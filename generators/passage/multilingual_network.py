"""Multilingual Textual Network (dim 7).

Connects passages by translation behavior across the multi-version
`text_resources` table (KJV, WEB, LSV are canon-wide). For each verse that has
all three translations, computes a divergence score (1 minus word-overlap).
Contiguous high-divergence verses cluster into "textual crux" passages; the top
few crux passages per book are connected across books (type=
'translation_divergence').

KNOWN GAP (documented): the engine has no LXX/Vulgate/Peshitta text, so true
MT <-> LXX alignment is out of reach. KJV/WEB/LSV are all MT-based English
translations — what this generator surfaces is translation-family divergence
(lexical cruxes where translators disagree most), not versional divergence.
Real versional alignment needs a future LXX/Vulgate/Peshitta ingest.
"""

import logging
from collections import defaultdict

from ._common import cluster_passages, upsert

logger = logging.getLogger(__name__)

VERSIONS = ("KJV", "WEB", "LSV")

TOP_FRACTION = 0.15          # verses kept per book (top-divergence slice)
MAX_PASSAGES_PER_BOOK = 3    # crux passages kept per book
MIN_DIVERGENCE = 0.45        # both passages must exceed this to connect
MAX_TOTAL = 20000            # overall cap


def _wordset(text):
    return set(text.lower().split())


def _load_divergence(conn, book_id=None):
    """{verse_id: divergence} for verses present in all three versions."""
    div = {}
    clause = "WHERE verse_id IN (SELECT verse_id FROM text_resources WHERE version = 'KJV')" \
             " AND verse_id IN (SELECT verse_id FROM text_resources WHERE version = 'WEB')" \
             " AND verse_id IN (SELECT verse_id FROM text_resources WHERE version = 'LSV')"
    if book_id:
        clause += f" AND verse_id LIKE '{book_id}.%'"
    rows = conn.execute(
        f"""
        SELECT verse_id, version, text FROM text_resources
        {clause}
        """
    ).fetchall()

    per_verse = defaultdict(dict)
    for r in rows:
        per_verse[r["verse_id"]][r["version"]] = r["text"]

    for vid, texts in per_verse.items():
        if len(texts) < len(VERSIONS):
            continue
        ws = [_wordset(texts[v]) for v in VERSIONS if v in texts]
        if not ws:
            continue
        union = set().union(*ws)
        if not union:
            continue
        inter = set(ws[0]).intersection(*ws[1:])
        div[vid] = 1.0 - (len(inter) / len(union))
    return div


def _crux_passages(conn, div, book_ids=None):
    """Top few crux passages per book, with mean divergence."""
    by_book = defaultdict(list)
    for vid, score in div.items():
        by_book[vid.split(".")[0]].append((vid, score))

    passages = []
    for book, items in by_book.items():
        if book_ids and book not in book_ids:
            continue
        items.sort(key=lambda x: x[1], reverse=True)
        cutoff_n = max(3, int(len(items) * TOP_FRACTION))
        crux = {vid for vid, _ in items[:cutoff_n]}
        crux_passes = cluster_passages(crux)
        for p in crux_passes[:MAX_PASSAGES_PER_BOOK]:
            mean = sum(score for vid, score in items if vid in crux) / max(len(crux), 1)
            p["divergence"] = mean
            passages.append(p)
    return passages


def run(conn, book_ids=None) -> int:
    """Connect textual-crux passages across the canon.

    Returns the number of passage_connections created.
    """
    try:
        div = _load_divergence(conn)
    except Exception as e:  # pragma: no cover - no text_resources
        logger.warning("multilingual_network: text_resources unavailable: %s", e)
        return 0
    if not div:
        return 0

    passages = _crux_passages(conn, div, book_ids)
    # Highest divergence first, so the cap keeps the strongest pairs.
    passages.sort(key=lambda p: p.get("divergence", 0), reverse=True)

    total = 0
    for i in range(len(passages)):
        if total >= MAX_TOTAL:
            break
        for j in range(i + 1, len(passages)):
            if total >= MAX_TOTAL:
                break
            a, b = passages[i], passages[j]
            if a["book"] == b["book"]:
                continue
            da, db = a.get("divergence", 0), b.get("divergence", 0)
            if da < MIN_DIVERGENCE or db < MIN_DIVERGENCE:
                continue
            if upsert(
                conn, a, b, "textual", "translation_divergence",
                strength=round((da + db) / 2, 2), confidence=0.4,
                metadata={"versions": list(VERSIONS), "mean_divergence": round((da + db) / 2, 3),
                          "source": "multilingual_network"},
            ):
                total += 1
        conn.commit()

    logger.info("multilingual_network: %d connections created", total)
    return total
