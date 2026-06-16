#!/usr/bin/env python3
"""
MCP Tool: scripture_pattern_ingest
Store a discovered pattern in the database.

This is the tool that DeepSeek V4 Flash uses to save patterns
it discovers during analysis, so they persist across sessions.

Usage:
  python3 pattern_ingest.py '{
    "scholar": "deepseek_ai",
    "book": "isa",
    "type": "chiasm",
    "start": "isa.1.1",
    "end": "isa.12.6",
    "pivot": "isa.6.1",
    "confidence": 0.65,
    "notes": "Possible chiasm from judgment (1-5) through temple vision (6)...",
    "layers": [
      {"letter": "A", "label": "Judgment oracles", "start": "isa.1.1", "end": "isa.5.30"},
      {"letter": "B", "label": "Isaiah's commission", "start": "isa.6.1", "end": "isa.6.13"},
      {"letter": "C", "label": "Sign of Immanuel", "start": "isa.7.1", "end": "isa.9.7"},
      {"letter": "B'", "label": "Judgment on Assyria", "start": "isa.9.8", "end": "isa.11.16"},
      {"letter": "A'", "label": "Song of salvation", "start": "isa.12.1", "end": "isa.12.6"}
    ]
  }'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, add_known_chiasm


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    scholar = args.get("scholar", "deepseek_ai")
    book = args.get("book", "")
    pattern_type = args.get("type", "chiasm")
    start = args.get("start", "")
    end = args.get("end", "")
    pivot = args.get("pivot", "")
    confidence = args.get("confidence", 0.5)
    notes = args.get("notes", "")
    layers = args.get("layers", [])
    reference = args.get("reference", "")

    if not book or not start or not end:
        print(json.dumps({
            "error": "Required: book, start, end",
            "usage": 'pattern_ingest.py \'{"book":"isa","start":"isa.1.1","end":"isa.12.6","confidence":0.6}\'',
        }))
        return

    conn = get_db()

    # Check if this pattern already exists (same start/end/scholar)
    existing = conn.execute("""
        SELECT id FROM known_chiasms
        WHERE scholar = ? AND start_verse = ? AND end_verse = ?
    """, (scholar, start, end)).fetchone()

    if existing:
        # Update existing
        conn.execute("""
            UPDATE known_chiasms SET
                confidence = ?, notes = ?, layers_json = ?,
                pivot_verse = ?, chiasm_type = ?, reference = ?
            WHERE id = ?
        """, (confidence, notes, json.dumps(layers), pivot, pattern_type, reference, existing["id"]))
        conn.commit()
        result = {"status": "updated", "id": existing["id"]}
    else:
        add_known_chiasm(
            conn,
            scholar=scholar,
            book_id=book,
            start_verse=start,
            end_verse=end,
            pivot_verse=pivot,
            chiasm_type=pattern_type,
            layers_json=json.dumps(layers),
            confidence=confidence,
            notes=notes,
            reference=reference,
            source_url="",
        )
        # Get the ID
        row = conn.execute("""
            SELECT id FROM known_chiasms
            WHERE scholar = ? AND start_verse = ? AND end_verse = ?
        """, (scholar, start, end)).fetchone()
        result = {"status": "added", "id": row["id"] if row else None}

    # Summarize stats
    count = conn.execute("SELECT COUNT(*) as c FROM known_chiasms").fetchone()["c"]
    ai_count = conn.execute("""
        SELECT COUNT(*) as c FROM known_chiasms WHERE discovered_by = 'AI' OR scholar = 'deepseek_ai'
    """).fetchone()["c"]

    result["stats"] = {
        "total_patterns": count,
        "ai_discovered": ai_count,
        "human_sourced": count - ai_count,
    }

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
