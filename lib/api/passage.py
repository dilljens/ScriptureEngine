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
        d = dict(r)
        if d.get("metadata") and isinstance(d["metadata"], str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
        density = d.get("metadata", {}).get("density", 1.0) if isinstance(d.get("metadata"), dict) else 1.0
        if density >= min_density:
            results.append(d)

    return results


def get_chapter_connections(conn, book, chapter):
    """Get all passage-level connections involving an entire chapter."""
    ch_start = f"{book}.{chapter}.1"
    # Use last verse of chapter
    row = conn.execute("""
        SELECT id FROM verses
        WHERE SUBSTR(id, 1, INSTR(id, '.') - 1) = ?
          AND CAST(SUBSTR(id, INSTR(id, '.') + 1, INSTR(SUBSTR(id, INSTR(id, '.') + 1), '.') - 1) AS INTEGER) = ?
        ORDER BY id DESC LIMIT 1
    """, (book, chapter)).fetchone()

    if not row:
        return {"error": f"No verses found for {book}.{chapter}"}

    ch_end = row["id"]
    ch_start_full = f"{book}.{chapter}.1"
    connections = get_passage_connections(conn, ch_start_full, ch_end)

    # Count verse-level connections involving this chapter
    verse_count = conn.execute("""
        SELECT COUNT(*) FROM connections
        WHERE SUBSTR(source_verse, 1, INSTR(SUBSTR(source_verse, INSTR(source_verse, '.') + 1), '.') + INSTR(source_verse, '.')) = ?
           OR SUBSTR(target_verse, 1, INSTR(SUBSTR(target_verse, INSTR(target_verse, '.') + 1), '.') + INSTR(target_verse, '.')) = ?
    """, (f"{book}.{chapter}.", f"{book}.{chapter}.")).fetchone()[0]

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
        d = dict(r)
        if d.get("metadata") and isinstance(d["metadata"], str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
        passages.append(d)

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
        d = dict(r)
        if d.get("metadata") and isinstance(d["metadata"], str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = {}
        results.append(d)
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
