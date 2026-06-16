#!/usr/bin/env python3
"""
MCP Tool: scripture_section_compare
Compare two sections of scripture for similarity and mirroring.

Usage:
  python3 section_compare.py '{
    "section_a": {"start": "gen.6.9", "end": "gen.8.14"},
    "section_b": {"start": "gen.8.15", "end": "gen.9.29"}
  }'
  python3 section_compare.py '{
    "book": "gen",
    "pair_a": [1, 3],    # chapters 1-3
    "pair_b": [48, 50]   # chapters 48-50
  }'
"""

import sys
import json
import os
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, compare_sections, get_section_verses


def compare_by_chapters(conn, book_id, chap_start_a, chap_end_a, chap_start_b, chap_end_b):
    """Compare two chapter ranges."""
    first_a = conn.execute("""
        SELECT id FROM verses WHERE book_id = ? AND chapter = ? AND verse = 1
    """, (book_id, chap_start_a)).fetchone()
    last_a = conn.execute("""
        SELECT id FROM verses WHERE book_id = ? AND chapter = ? ORDER BY verse DESC LIMIT 1
    """, (book_id, chap_end_a)).fetchone()
    first_b = conn.execute("""
        SELECT id FROM verses WHERE book_id = ? AND chapter = ? AND verse = 1
    """, (book_id, chap_start_b)).fetchone()
    last_b = conn.execute("""
        SELECT id FROM verses WHERE book_id = ? AND chapter = ? ORDER BY verse DESC LIMIT 1
    """, (book_id, chap_end_b)).fetchone()

    if not all([first_a, last_a, first_b, last_b]):
        return {"error": "Chapter range not found"}

    return compare_sections(conn, first_a["id"], last_a["id"], first_b["id"], last_b["id"])


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    conn = get_db()
    result = {}

    if "section_a" in args and "section_b" in args:
        start_a = args["section_a"]["start"]
        end_a = args["section_a"]["end"]
        start_b = args["section_b"]["start"]
        end_b = args["section_b"]["end"]
        result = compare_sections(conn, start_a, end_a, start_b, end_b)

    elif "book" in args and "pair_a" in args and "pair_b" in args:
        book = args["book"]
        chap_a_s, chap_a_e = args["pair_a"][0], args["pair_a"][-1]
        chap_b_s, chap_b_e = args["pair_b"][0], args["pair_b"][-1]
        result = compare_by_chapters(conn, book, chap_a_s, chap_a_e, chap_b_s, chap_b_e)

    else:
        result = {"error": "Provide section_a+section_b or book+pair_a+pair_b"}

    # Add interpretation hints
    if "overlap_score" in result:
        hints = []
        score = result["overlap_score"]
        ratio = result.get("word_count_ratio", 0)

        if score > 0.3:
            hints.append("High keyword overlap — these sections share significant vocabulary")

        if 0.8 <= ratio <= 1.2:
            hints.append(f"Word counts are close ({ratio}) — possible chiastic pairing")

        wc_a = result.get("section_a", {}).get("word_count", 0)
        wc_b = result.get("section_b", {}).get("word_count", 0)
        if wc_a > 0 and wc_b > 0 and abs(wc_a - wc_b) < 10:
            hints.append(f"Near-identical word counts ({wc_a} vs {wc_b}) — strong structural mirror signal")

        shared_count = len(result.get("shared_keywords", []))
        if shared_count > 10:
            hints.append(f"{shared_count} shared keywords — these sections are lexically related")

        result["interpretation_hints"] = hints

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
