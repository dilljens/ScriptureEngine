"""Shared helpers for passage-level generators.

Keeps the INSERT-into-passage_connections, keyword scanning, and passage
clustering logic in one place so discovery generators stay thin. Mirrors the
private helpers in theme_tracer.py but generalized.
"""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def book_of(ref: str) -> str:
    """Extract the book id from a verse reference (gen.1.1 -> gen)."""
    return ref.split(".")[0]


def scan_keywords(conn, keywords, book_ids=None, limit=200):
    """Scan verse text for any of the given keywords (case-insensitive LIKE).

    Returns a list of {"verse", "book", "keyword"} dicts. Uses the top 5
    keywords per call for performance, matching theme_tracer's convention.
    """
    rows = []
    for kw in keywords[:5]:
        like = f"%{kw}%"
        try:
            if book_ids:
                placeholders = ",".join("?" for _ in book_ids)
                r = conn.execute(
                    f"""
                    SELECT id FROM verses
                    WHERE LOWER(text_english) LIKE ?
                      AND SUBSTR(id, 1, INSTR(id, '.') - 1) IN ({placeholders})
                    LIMIT {limit}
                    """,
                    (like, *book_ids),
                ).fetchall()
            else:
                r = conn.execute(
                    """
                    SELECT id FROM verses
                    WHERE LOWER(text_english) LIKE ?
                    LIMIT ?
                    """,
                    (like, limit),
                ).fetchall()
            for row in r:
                rows.append({"verse": row["id"], "book": book_of(row["id"]), "keyword": kw})
        except Exception as e:  # pragma: no cover - defensive
            logger.warning("scan_keywords error for %r: %s", kw, e)
    return rows


def _gap(a: str, b: str) -> int:
    """Verse-number gap between two refs; 999 across chapters/books."""
    pa, pb = a.split("."), b.split(".")
    if pa[0] != pb[0] or pa[1] != pb[1]:
        return 999
    try:
        return abs(int(pb[2]) - int(pa[2]))
    except (ValueError, IndexError):
        return 999


def cluster_passages(verse_ids, window=5):
    """Group sorted verse ids into passage ranges (gaps <= window).

    Returns a list of {"start", "end", "count", "book"} dicts. Passages with
    fewer than 2 distinct verses are dropped (matches theme_tracer).
    """
    by_book: dict[str, list[str]] = defaultdict(list)
    for v in sorted(set(verse_ids)):
        by_book[book_of(v)].append(v)

    passages = []
    for book, verses in by_book.items():
        verses.sort()
        i = 0
        while i < len(verses):
            j = i
            while j + 1 < len(verses) and _gap(verses[j], verses[j + 1]) <= window:
                j += 1
            start, end = verses[i], verses[j]
            if start != end:
                passages.append({"start": start, "end": end, "count": j - i + 1, "book": book})
            i = j + 1
    return passages


def to_passages(verse_ids, window=5, allow_singles=True):
    """Passage ranges for verse ids; falls back to single-verse passages.

    cluster_passages drops isolated verses (fewer than 2 distinct verses).
    Some generators (typology lift, reception network) want every curated
    verse represented, so allow_singles promotes unclustered verses to
    1-verse passages.
    """
    passages = cluster_passages(verse_ids, window)
    if passages or not allow_singles:
        return passages
    return [
        {"start": v, "end": v, "count": 1, "book": book_of(v)}
        for v in sorted(set(verse_ids))
    ]


def upsert(conn, a, b, layer, type_name, subtype="", strength=0.5, confidence=0.5,
           metadata=None, discovered_by="algorithm"):
    """Insert one passage_connections row (idempotent).

    a, b are {"start", "end", "book", ...} dicts. Returns True if inserted,
    False if it hit the UNIQUE conflict (duplicate).
    """
    try:
        cur = conn.execute(
            """
            INSERT INTO passage_connections
                (source_start, source_end, target_start, target_end, layer, type,
                 subtype, strength, confidence, discovered_by, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_start, source_end, target_start, target_end, layer, type, subtype)
            DO NOTHING
            """,
            (
                a["start"], a["end"], b["start"], b["end"], layer, type_name, subtype,
                round(strength, 2), round(confidence, 2), discovered_by,
                json.dumps(metadata or {}),
            ),
        )
        return cur.rowcount > 0
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("upsert error: %s", e)
        return False
