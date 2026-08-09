"""Inner-Biblical Interpretation Network (dim 4).

Walks chains of explicit intertextual edges and emits PASSAGE-level
connections between chain endpoints. A chain is A -> B -> C where A quotes B
and B quotes C (edges are stored as source_verse quotes target_verse). When A
and C are in different books and not directly connected, their passages belong
to the same interpretation network and get a passage_connections row
(type='interpretation_chain').

Selectivity (quality over density): only EXPLICIT direct_quotation edges count,
and only cross-testament chains (OT <-> NT/BoM etc.) are emitted — same-testament
chains add little and would swamp the table. Chain verses are aggregated into
passages per book, and only DISTINCT passage pairs are emitted (deduped by the
UNIQUE key). No running caps -> deterministic and idempotent (a second run
emits nothing new). Canon-wide quote hubs are skipped via MAX_DEGREE.
"""

import logging
from bisect import bisect_right
from collections import defaultdict

from ._common import to_passages, upsert

logger = logging.getLogger(__name__)

# Only explicit direct quotations count — the strongest intertextual signal.
EDGE_TYPES = ("direct_quotation",)
MAX_DEGREE = 150          # skip canon-wide quote hubs
MAX_PAIRS_PER_HUB = 100   # cap pairs per intermediate (dedup keeps it exact)

OT_BOOKS = {
    "gen", "exo", "lev", "num", "deu", "josh", "judg", "ruth",
    "1sam", "2sam", "1kgs", "2kgs", "1chr", "2chr", "ezra", "neh",
    "esth", "job", "psa", "prov", "eccl", "song", "isa", "jer",
    "lam", "ezek", "dan", "hos", "joel", "amos", "obad", "jonah",
    "mic", "nah", "hab", "zeph", "hag", "zech", "mal",
}


def _ref_key(ref):
    """Sortable tuple from a verse ref: (book, chapter, verse)."""
    book, ch, v = ref.split(".")
    return (book, int(ch), int(v))


def _collect_edges(conn):
    """Directed adjacency: out[s] = {t : s quotes t}, in[t] = {s : s quotes t}."""
    out = defaultdict(set)
    inn = defaultdict(set)
    rows = conn.execute(
        """
        SELECT source_verse, target_verse FROM connections
        WHERE layer = 'intertextual' AND type = 'direct_quotation'
        """
    ).fetchall()
    for r in rows:
        out[r["source_verse"]].add(r["target_verse"])
        inn[r["target_verse"]].add(r["source_verse"])
    return out, inn


def _assign(verses, passages):
    """{verse_id: passage key} using bisect over each book's passage starts."""
    by_book = defaultdict(list)
    for p in passages:
        by_book[p["book"]].append(p)
    for _book, ps in by_book.items():
        ps.sort(key=lambda p: _ref_key(p["start"]))

    index = {}
    for v in verses:
        book = v.split(".")[0]
        ps = by_book.get(book)
        if not ps:
            continue
        starts = [_ref_key(p["start"]) for p in ps]
        k = _ref_key(v)
        i = bisect_right(starts, k) - 1
        if i >= 0 and _ref_key(ps[i]["end"]) >= k:
            index[v] = (ps[i]["start"], ps[i]["end"])
    return index


def run(conn, book_ids=None) -> int:
    """Connect interpretation-chain endpoints at the passage level.

    Returns the number of passage_connections created.
    """
    out, inn = _collect_edges(conn)

    # Chain participants: nodes with both incoming and outgoing intertextual
    # edges, plus their neighbors (any verse that could sit in an A->B->C chain).
    participants = set()
    for b in set(out) & set(inn):
        participants.add(b)
        participants |= out[b]
        participants |= inn[b]
    if book_ids:
        participants = {v for v in participants if v.split(".")[0] in book_ids}
    if not participants:
        return 0

    passages = to_passages(participants)
    p_of = _assign(participants, passages)

    # Passages already directly connected at the verse level are not "chain
    # endpoints" — skip them.
    direct = set()
    for a, cs in out.items():
        ka = p_of.get(a)
        if ka is None:
            continue
        for c in cs:
            kc = p_of.get(c)
            if kc is not None and kc != ka:
                direct.add((ka, kc) if ka < kc else (kc, ka))

    total = 0
    for b in set(out) & set(inn):
        degree = len(out[b]) + len(inn[b])
        if not (2 <= degree <= MAX_DEGREE):
            continue
        pa_set = {p_of[a] for a in inn[b] if a in p_of}
        pc_set = {p_of[c] for c in out[b] if c in p_of}
        if not pa_set or not pc_set:
            continue
        # Sorted iteration: deterministic across runs (set order is not).
        pa_list = sorted(pa_set)
        pc_list = sorted(pc_set)
        pairs = 0
        for ka in pa_list:
            for kc in pc_list:
                if ka == kc or (ka, kc) in direct or (kc, ka) in direct:
                    continue
                ka_book = ka[0].split(".")[0]
                kc_book = kc[0].split(".")[0]
                if ka_book == kc_book:
                    continue  # same-book pairs are not a network
                # Cross-testament only: OT endpoints must pair with a
                # non-OT endpoint (NT/BoM/D&C etc.).
                if (ka_book in OT_BOOKS) == (kc_book in OT_BOOKS):
                    continue
                a = {"start": ka[0], "end": ka[1], "count": 1, "book": ka_book}
                c = {"start": kc[0], "end": kc[1], "count": 1, "book": kc_book}
                if upsert(
                    conn, a, c, "intertextual", "interpretation_chain",
                    strength=0.4, confidence=0.5,
                    metadata={"via": b, "hops": 2, "source": "interpretation_network"},
                ):
                    total += 1
                pairs += 1
                if pairs >= MAX_PAIRS_PER_HUB:
                    break
            if pairs >= MAX_PAIRS_PER_HUB:
                break
        conn.commit()

    logger.info("interpretation_network: %d connections created", total)
    return total
