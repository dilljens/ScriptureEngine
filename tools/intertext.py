#!/usr/bin/env python3
"""
MCP Tool: scripture_intertext
Trace intertextual connections — quotations, allusions, and echoes.

Usage: python3 intertext.py '{"verse": "isa.6.1"}'
       python3 intertext.py '{"verse": "isa.6.1", "direction": "both"}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.retrieval import get_intertextual_chain


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    verse_id = args.get("verse", "")
    direction = args.get("direction", "both")

    if not verse_id:
        print(json.dumps({"error": "Provide a verse ID (e.g., isa.6.1)"}))
        return

    conn = get_db()

    # Get the verse text first
    verse = conn.execute("""
        SELECT v.*, b.title as book_title
        FROM verses v
        JOIN books b ON b.id = v.book_id
        WHERE v.id = ?
    """, (verse_id,)).fetchone()

    chain = get_intertextual_chain(conn, verse_id, direction=direction)

    result = {
        "verse_id": verse_id,
        "verse_text": dict(verse)["text_english"] if verse else "",
        "book": dict(verse)["book_title"] if verse else "",
        "direction": direction,
        "connection_count": len(chain),
        "connections": [
            {
                "type": c["type"],
                "subtype": c.get("subtype", ""),
                "target_verse": c.get("target_verse", c.get("source_verse")),
                "target_text": c.get("target_text", "")[:200],
                "target_book": c.get("target_book_title", ""),
                "strength": c.get("strength", 0),
            }
            for c in chain
        ],
    }

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
