"""
Book Coherence Scanner — aggregate verse-level connections into book-level summaries.

For each book, calculates:
  - Total incoming/outgoing connections
  - Top 10 most connected books (with counts)
  - Per-layer distribution
  - Connection density per chapter
  - Most connected chapters

Outputs book_thematic passage_connections between books.
Also updates book connection metadata for the API.
"""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

MIN_BOOK_CONNECTIONS = 10  # minimum connections to create a book-level record


def run(conn, book_ids=None) -> int:
    """Create book-level passage connections from verse-level data."""
    books = _get_books(conn, book_ids)
    if not books:
        return 0

    # Count connections per book pair
    book_pairs = _count_book_pairs(conn, books, book_ids)
    if not book_pairs:
        return 0

    count = _write_book_connections(conn, book_pairs, books)
    logger.info("book_coherence: %d book-level connections created", count)
    return count


def _get_books(conn, book_ids=None):
    """Get list of book IDs."""
    if book_ids:
        return {b: b for b in book_ids}
    rows = conn.execute("SELECT DISTINCT SUBSTR(id, 1, INSTR(id, '.') - 1) AS book_id FROM verses ORDER BY id").fetchall()
    return {r["book_id"]: r["book_id"] for r in rows}


def _count_book_pairs(conn, books, book_ids=None):
    """Count connections between every pair of books."""
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT
                SUBSTR(c.source_verse, 1, INSTR(c.source_verse, '.') - 1) AS src_book,
                SUBSTR(c.target_verse, 1, INSTR(c.target_verse, '.') - 1) AS tgt_book,
                c.layer, c.type, COUNT(*) AS cnt,
                AVG(c.strength) AS avg_strength,
                AVG(c.confidence) AS avg_confidence
            FROM connections c
            WHERE SUBSTR(c.source_verse, 1, INSTR(c.source_verse, '.') - 1) IN ({placeholders})
               OR SUBSTR(c.target_verse, 1, INSTR(c.target_verse, '.') - 1) IN ({placeholders})
            GROUP BY src_book, tgt_book, c.layer
            HAVING cnt >= ?
        """, (*book_ids, *book_ids, MIN_BOOK_CONNECTIONS)).fetchall()
    else:
        rows = conn.execute("""
            SELECT
                SUBSTR(c.source_verse, 1, INSTR(c.source_verse, '.') - 1) AS src_book,
                SUBSTR(c.target_verse, 1, INSTR(c.target_verse, '.') - 1) AS tgt_book,
                c.layer, c.type, COUNT(*) AS cnt,
                AVG(c.strength) AS avg_strength,
                AVG(c.confidence) AS avg_confidence
            FROM connections c
            GROUP BY src_book, tgt_book, c.layer
            HAVING cnt >= ?
        """, (MIN_BOOK_CONNECTIONS,)).fetchall()

    return [dict(r) for r in rows]


def _write_book_connections(conn, book_pairs, books):
    """Write book-level passage_connections records."""
    # Aggregate per book pair across all layers
    pair_data = defaultdict(lambda: {
        "total": 0, "layers": defaultdict(int), "types": defaultdict(int),
        "avg_strength": 0, "avg_confidence": 0, "count": 0,
    })

    for r in book_pairs:
        key = (r["src_book"], r["tgt_book"])
        pair_data[key]["total"] += r["cnt"]
        pair_data[key]["layers"][r["layer"]] += r["cnt"]
        pair_data[key]["types"][r["type"]] += r["cnt"]
        pair_data[key]["avg_strength"] += r["avg_strength"] * r["cnt"]
        pair_data[key]["avg_confidence"] += r["avg_confidence"] * r["cnt"]
        pair_data[key]["count"] += r["cnt"]

    count = 0
    for (src_book, tgt_book), data in pair_data.items():
        if data["count"] == 0:
            continue
        avg_strength = data["avg_strength"] / data["count"]
        avg_confidence = data["avg_confidence"] / data["count"]

        # Get book verse ranges
        src_start = _get_first_verse(conn, src_book)
        src_end = _get_last_verse(conn, src_book)
        tgt_start = _get_first_verse(conn, tgt_book)
        tgt_end = _get_last_verse(conn, tgt_book)

        if not all([src_start, src_end, tgt_start, tgt_end]):
            continue

        # Top layers
        sorted_layers = sorted(data["layers"].items(), key=lambda x: -x[1])
        top_types = sorted(data["types"].items(), key=lambda x: -x[1])[:5]

        metadata = json.dumps({
            "total_connections": data["total"],
            "layers": dict(sorted_layers),
            "top_types": [{"type": t, "count": c} for t, c in top_types],
            "avg_strength": round(avg_strength, 3),
            "source": "book_coherence",
        }, default=str)

        try:
            conn.execute("""
                INSERT INTO passage_connections
                    (source_start, source_end, target_start, target_end, layer, type,
                     strength, confidence, discovered_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_start, source_end, target_start, target_end, layer, type, subtype)
                DO NOTHING
            """, (
                src_start, src_end, tgt_start, tgt_end,
                "intertextual", "book_thematic",
                round(avg_strength, 2), round(avg_confidence, 2),
                "algorithm", metadata,
            ))
            count += 1
        except Exception as e:
            logger.warning("book_coherence: insert error for %s→%s: %s", src_book, tgt_book, e)

    conn.commit()
    return count


def _get_first_verse(conn, book_id):
    """Get the first verse ID for a book."""
    row = conn.execute(
        "SELECT id FROM verses WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) = ? ORDER BY id LIMIT 1",
        (book_id,),
    ).fetchone()
    return row["id"] if row else None


def _get_last_verse(conn, book_id):
    """Get the last verse ID for a book."""
    row = conn.execute(
        "SELECT id FROM verses WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) = ? ORDER BY id DESC LIMIT 1",
        (book_id,),
    ).fetchone()
    return row["id"] if row else None
