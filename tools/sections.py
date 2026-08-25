#!/usr/bin/env python3
"""
MCP Tool: scripture_search_sections
Search for topical SECTIONS instead of single verses — clusters nearby
verse hits into contiguous passages (e.g. isa.52.13-53.12).

Usage: python3 sections.py '{"query": "servant", "book": "isa"}'
       python3 sections.py '{"query": "redemption", "min_hits": 3}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.api.search import search_sections
from lib.db import get_db


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    query = args.get("query", "")
    if not query:
        print(json.dumps({"error": "Provide a search query"}))
        return

    conn = get_db()
    result = search_sections(
        conn,
        query,
        book=args.get("book"),
        works=args.get("works"),
        limit=args.get("limit", 10),
        min_hits=args.get("min_hits", 2),
        gap=args.get("gap", 3),
    )
    conn.close()

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
