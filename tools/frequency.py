#!/usr/bin/env python3
"""
MCP Tool: scripture_frequency
Analyze word/phrase frequency and distribution.

Usage: python3 frequency.py '{"word": "covenant"}'
       python3 frequency.py '{"formula": "And it came to pass"}'
       python3 frequency.py '{"pattern": "seven_fold", "book": "gen"}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.patterns.frequency import (
    count_occurrences,
    find_phrases_by_pattern,
    sacred_count_significance,
)


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    conn = get_db()

    # Build text corpus from the database
    book_filter = args.get("book")
    if book_filter:
        rows = conn.execute("""
            SELECT v.id, v.text_english
            FROM verses v
            WHERE v.book_id = ?
        """, (book_filter,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT v.id, v.text_english FROM verses v
        """).fetchall()

    corpus = [(r["id"], r["text_english"]) for r in rows if r["text_english"]]

    result = {}

    if "word" in args:
        result = count_occurrences(corpus, args["word"])
        # Add significance check
        sig = sacred_count_significance(result["total"])
        if sig:
            result["significance"] = sig

    elif "formula" in args:
        result = count_occurrences(corpus, args["formula"])
        result["formula"] = args["formula"]

    elif "pattern" in args:
        pattern_type = args["pattern"]
        pattern_results = find_phrases_by_pattern(corpus, pattern_type)
        result = {
            "pattern_type": pattern_type,
            "count": len(pattern_results),
            "matches": pattern_results[:20],
        }

    else:
        result = {"error": "Provide word, formula, or pattern"}

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
