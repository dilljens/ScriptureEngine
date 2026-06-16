#!/usr/bin/env python3
"""
MCP Tool: scripture_search
Search scripture text by keyword or phrase.

Usage: python3 search.py '{"query": "light", "book": "gen"}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, search_verses


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    query = args.get("query", "")
    book = args.get("book")
    limit = args.get("limit", 20)

    if not query:
        print(json.dumps({"error": "Provide a search query"}))
        return

    conn = get_db()
    results = search_verses(conn, query, book_id=book, limit=limit)
    conn.close()

    output = {
        "query": query,
        "count": len(results),
        "results": [
            {
                "verse_id": r["id"],
                "reference": f"{r.get('book_title', '')} {r['chapter']}:{r['verse']}",
                "text": r["text_english"][:200] + ("..." if len(r["text_english"]) > 200 else ""),
                "book": r.get("book_title"),
            }
            for r in results
        ],
    }

    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
