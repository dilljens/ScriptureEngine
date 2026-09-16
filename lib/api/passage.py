"""Passage-level connection API — verse ranges, chapter summaries, book coherence."""

import json
import logging

from lib.db import get_db

logger = logging.getLogger(__name__)


def _parse_range(ref):
    """Parse a passage reference like 'gen.1.1-exod.12.51' into start/end."""
    parts = ref.split("-", 1)
    start = parts[0].strip()
    end = parts[1].strip() if len(parts) > 1 else start
    return start, end


def split_embedded_range(start, end):
    """Split a '--' embedded range out of a single endpoint ref.

    Data-quality fix for chiastic_promoter rows where a full range got written
    into one field, e.g. source_start='1adae.21.5--1adae.21.9'. Returns
    (start, end) with the range split across the two columns.
    """
    if start and "--" in start:
        left, _, right = start.partition("--")
        return left.strip(), (right.strip() or end or left.strip())
    return start, end


def derive_granularity(start, end):
    """Classify a passage range: 'verse' | 'chunk' | 'chapter' | 'book'.

    Derived from the endpoint refs rather than stored, so it works on the live
    DB without a migration. Ranges are verse-shaped (gen.1.1); chapter and book
    granularity is implied by the span.
    """
    start, end = split_embedded_range(start, end)
    s = (start or "").split(".")
    e = (end or start or "").split(".")
    if len(s) < 2 or len(e) < 2:
        return "book"
    if s[0] != e[0]:
        return "book"
    if len(s) >= 3 and len(e) >= 3 and s[1] == e[1]:
        try:
            width = abs(int(e[2]) - int(s[2]))
        except ValueError:
            return "chunk"
        if width == 0:
            return "verse"
        return "chunk" if width < 30 else "chapter"
    return "chapter"


def _format_row(r):
    """Normalize a passage_connections row: parse metadata JSON, split embedded
    '--' ranges, and derive a granularity label."""
    d = dict(r)
    if d.get("metadata") and isinstance(d["metadata"], str):
        try:
            d["metadata"] = json.loads(d["metadata"])
        except (json.JSONDecodeError, TypeError):
            d["metadata"] = {}
    d["source_start"], d["source_end"] = split_embedded_range(d.get("source_start"), d.get("source_end"))
    d["target_start"], d["target_end"] = split_embedded_range(d.get("target_start"), d.get("target_end"))
    d["granularity"] = derive_granularity(d["source_start"], d["source_end"])
    return d


def get_passage_connections(conn, start, end, min_density=0.0):
    """Get all passage-level connections involving a verse range."""
    rows = conn.execute("""
        SELECT * FROM passage_connections
        WHERE (source_start >= ? AND source_start <= ?)
           OR (target_start >= ? AND target_start <= ?)
           OR (source_end >= ? AND source_end <= ?)
           OR (target_end >= ? AND target_end <= ?)
        ORDER BY strength DESC
    """, (start, end, start, end, start, end, start, end)).fetchall()

    results = []
    for r in rows:
        d = _format_row(r)
        density = d.get("metadata", {}).get("density", 1.0) if isinstance(d.get("metadata"), dict) else 1.0
        if density >= min_density:
            results.append(d)

    return results


def get_chapter_connections(conn, book, chapter):
    """Get all passage-level connections involving an entire chapter."""
    # Verse ids via the (book_id, chapter) index — no string surgery.
    verse_rows = conn.execute(
        "SELECT id FROM verses WHERE book_id = ? AND chapter = ? ORDER BY verse",
        (book, chapter)).fetchall()
    if not verse_rows:
        return {"error": f"No verses found for {book}.{chapter}"}
    verse_ids = [r["id"] for r in verse_rows]
    ch_start_full, ch_end = verse_ids[0], verse_ids[-1]
    connections = get_passage_connections(conn, ch_start_full, ch_end)

    # Count verse-level connections with indexed prefix ranges, not a
    # SUBSTR-over-every-row scan (that was 8+s on 1.3M rows). No book_id
    # contains '.', so `{book}.{chapter}.` is an unambiguous prefix, and
    # '/' is '.'+1, so [prefix, prefix-next) matches exactly that prefix.
    # UNION over id preserves OR semantics (a row matching both sides
    # counts once) while each branch uses its own source/target index.
    lo, hi = f"{book}.{chapter}.", f"{book}.{chapter}/"
    verse_count = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT id FROM connections WHERE source_verse >= ? AND source_verse < ?
            UNION
            SELECT id FROM connections WHERE target_verse >= ? AND target_verse < ?
        )
    """, (lo, hi, lo, hi)).fetchone()[0]

    return {
        "chapter": f"{book}.{chapter}",
        "passage_connections": connections,
        "verse_connection_count": verse_count,
        "density": round(len(connections) / max(verse_count, 1), 3),
    }


def get_book_summary(conn, book):
    """Get book-level connection summary."""
    # Get book range
    first = conn.execute(
        "SELECT id FROM verses WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) = ? ORDER BY id LIMIT 1",
        (book,),
    ).fetchone()
    last = conn.execute(
        "SELECT id FROM verses WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) = ? ORDER BY id DESC LIMIT 1",
        (book,),
    ).fetchone()

    if not first or not last:
        return {"error": f"Book not found: {book}"}

    # Passage connections involving this book
    passage_rows = conn.execute("""
        SELECT * FROM passage_connections
        WHERE SUBSTR(source_start, 1, INSTR(source_start, '.') - 1) = ?
           OR SUBSTR(target_start, 1, INSTR(target_start, '.') - 1) = ?
        ORDER BY strength DESC LIMIT 50
    """, (book, book)).fetchall()

    passages = []
    for r in passage_rows:
        passages.append(_format_row(r))

    # Top connected books
    top_books = conn.execute("""
        SELECT
            CASE WHEN SUBSTR(source_start, 1, INSTR(source_start, '.') - 1) = ?
                 THEN SUBSTR(target_start, 1, INSTR(target_start, '.') - 1)
                 ELSE SUBSTR(source_start, 1, INSTR(source_start, '.') - 1)
            END AS other_book,
            COUNT(*) AS connection_count,
            AVG(strength) AS avg_strength
        FROM passage_connections
        WHERE SUBSTR(source_start, 1, INSTR(source_start, '.') - 1) = ?
           OR SUBSTR(target_start, 1, INSTR(target_start, '.') - 1) = ?
        GROUP BY other_book
        ORDER BY connection_count DESC
        LIMIT 10
    """, (book, book, book)).fetchall()

    # Verse-level connection counts per layer
    layer_counts = conn.execute("""
        SELECT layer, COUNT(*) AS cnt
        FROM connections
        WHERE SUBSTR(source_verse, 1, INSTR(source_verse, '.') - 1) = ?
           OR SUBSTR(target_verse, 1, INSTR(target_verse, '.') - 1) = ?
        GROUP BY layer
        ORDER BY cnt DESC
    """, (book, book)).fetchall()

    return {
        "book": book,
        "passage_connections": passages,
        "top_connected_books": [dict(r) for r in top_books],
        "layer_distribution": [dict(r) for r in layer_counts],
    }


def get_density_clusters(conn, book=None, min_density=0.3):
    """Find all passage clusters above a density threshold."""
    if book:
        rows = conn.execute("""
            SELECT * FROM passage_connections
            WHERE type = 'pericope_parallel'
              AND SUBSTR(source_start, 1, INSTR(source_start, '.') - 1) = ?
              AND CAST(JSON_EXTRACT(metadata, '$.density') AS REAL) >= ?
            ORDER BY CAST(JSON_EXTRACT(metadata, '$.density') AS REAL) DESC
            LIMIT 100
        """, (book, min_density)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM passage_connections
            WHERE type = 'pericope_parallel'
              AND CAST(JSON_EXTRACT(metadata, '$.density') AS REAL) >= ?
            ORDER BY CAST(JSON_EXTRACT(metadata, '$.density') AS REAL) DESC
            LIMIT 100
        """, (min_density,)).fetchall()

    results = []
    for r in rows:
        results.append(_format_row(r))
    return results


# ── MCP tool definitions ─────────────────────────────────────────────

TOOL_DEFS = [
    {
        "name": "passage_connections",
        "description": "Get passage-level connections for a verse range (e.g. 'gen.1.1-exod.12.51' or 'gen.40.1-gen.40.23')",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ref": {"type": "string", "description": "Passage reference: 'start-end' or single verse"},
                "min_density": {"type": "number", "description": "Minimum density filter (0-1, default 0)"},
            },
            "required": ["ref"],
        },
    },
    {
        "name": "chapter_connections",
        "description": "Get passage-level and verse-level connection summary for a chapter",
        "inputSchema": {
            "type": "object",
            "properties": {
                "book": {"type": "string", "description": "Book ID (e.g. 'gen', 'isa')"},
                "chapter": {"type": "integer", "description": "Chapter number"},
            },
            "required": ["book", "chapter"],
        },
    },
    {
        "name": "book_connection_summary",
        "description": "Get book-level connection summary with top connected books and layer distribution",
        "inputSchema": {
            "type": "object",
            "properties": {
                "book": {"type": "string", "description": "Book ID (e.g. 'gen', 'isa')"},
            },
            "required": ["book"],
        },
    },
]
