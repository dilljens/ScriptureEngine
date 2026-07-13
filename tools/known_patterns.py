#!/usr/bin/env python3
"""
MCP Tool: scripture_known_patterns
Query and manage the known chiasms database.

Usage:
  python3 known_patterns.py '{"book": "gen"}'
  python3 known_patterns.py '{"scholar": "welch"}'
  python3 known_patterns.py '{"scholar": "giliadi"}'
  python3 known_patterns.py '{"add": {"scholar": "welch", ...}}'
  python3 known_patterns.py '{"detect": {"start": "gen.6.9", "end": "gen.9.29"}}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import add_known_chiasm, find_matching_known_chiasm, get_db, get_known_chiasms


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    conn = get_db()
    result = {}

    if "add" in args:
        # Add a known pattern to the database
        data = args["add"]
        add_known_chiasm(
            conn,
            scholar=data.get("scholar", ""),
            book_id=data.get("book", ""),
            start_verse=data.get("start", ""),
            end_verse=data.get("end", ""),
            pivot_verse=data.get("pivot", ""),
            chiasm_type=data.get("type", ""),
            layers_json=json.dumps(data.get("layers", [])),
            confidence=data.get("confidence", 0.7),
            notes=data.get("notes", ""),
            source_url=data.get("url", ""),
            reference=data.get("reference", ""),
        )
        result = {"status": "added", "pattern": data.get("type", "chiasm")}

    elif "detect" in args:
        # Check if a passage matches any known pattern
        start = args["detect"].get("start", "")
        end = args["detect"].get("end", "")
        matches = find_matching_known_chiasm(conn, start, end)
        result = {
            "query": {"start": start, "end": end},
            "matches_found": len(matches),
            "matches": [
                {
                    "scholar": m["scholar"],
                    "reference": m.get("reference", ""),
                    "book": m["book_id"],
                    "start": m["start_verse"],
                    "end": m["end_verse"],
                    "chiasm_type": m["chiasm_type"],
                    "confidence": m["confidence"],
                    "notes": m.get("notes", ""),
                }
                for m in matches
            ],
        }

    else:
        # Query known patterns
        book = args.get("book")
        scholar = args.get("scholar")

        if scholar == "giliadi":
            scholar_name = "Giliadi"
        elif scholar == "welch":
            scholar_name = "Welch"
        else:
            scholar_name = scholar

        patterns = get_known_chiasms(conn, book_id=book, scholar=scholar_name)

        # Group by book
        by_book = {}
        for p in patterns:
            b = p["book_id"]
            if b not in by_book:
                by_book[b] = []
            by_book[b].append({
                "id": p["id"],
                "scholar": p["scholar"],
                "reference": p.get("reference", ""),
                "start": p["start_verse"],
                "end": p["end_verse"],
                "pivot": p["pivot_verse"],
                "type": p["chiasm_type"],
                "confidence": p["confidence"],
                "notes": p.get("notes", ""),
            })

        result = {
            "query": {"book": book, "scholar": scholar_name},
            "total_patterns": len(patterns),
            "by_book": by_book,
        }

        # Add summary
        if patterns:
            result["summary"] = {
                "unique_books": len(by_book),
                "by_type": {},
            }
            type_counts = {}
            for p in patterns:
                t = p["chiasm_type"] or "unspecified"
                type_counts[t] = type_counts.get(t, 0) + 1
            result["summary"]["by_type"] = type_counts

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
