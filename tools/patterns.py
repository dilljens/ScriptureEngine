#!/usr/bin/env python3
"""
MCP Tool: scripture_patterns
Detect literary patterns in a passage.

Usage: python3 patterns.py '{"book": "isa", "chapter": 6}'
       python3 patterns.py '{"book": "gen", "chapter": 1, "chapter_end": 2}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_chapter, get_db
from lib.patterns.chiastic import detect_chiasm_in_book
from lib.patterns.parallelism import detect_parallelisms


def analyze_passage(book, chapter_start, chapter_end=None):
    """Analyze a passage for literary patterns."""
    conn = get_db()

    if chapter_end is None:
        chapter_end = chapter_start

    all_verses = []
    for ch in range(chapter_start, chapter_end + 1):
        verses = get_chapter(conn, book, ch)
        all_verses.extend(verses)

    if not all_verses:
        conn.close()
        return {"error": f"No verses found for {book} chapters {chapter_start}-{chapter_end}"}

    result = {
        "book": book,
        "chapters": list(range(chapter_start, chapter_end + 1)),
        "verse_count": len(all_verses),
    }

    # Chiastic patterns
    chiasms = detect_chiasm_in_book(all_verses)
    if chiasms:
        result["chiasms"] = []
        for c in chiasms:
            idx_a = c["start_index"]
            idx_b = c["end_index"]
            if idx_a < len(all_verses) and idx_b < len(all_verses):
                v_a = all_verses[idx_a]
                v_b = all_verses[idx_b]
                result["chiasms"].append({
                    "verse_a": f"{v_a.get('book_title', book)} {v_a['chapter']}:{v_a['verse']}",
                    "verse_b": f"{v_b.get('book_title', book)} {v_b['chapter']}:{v_b['verse']}",
                    "shared_terms": c["shared_terms"],
                    "inner_layers": c["inner_matching_layers"],
                    "confidence": c["confidence"],
                })
    else:
        result["chiasms"] = []

    # Parallelism patterns
    parallelisms = detect_parallelisms(all_verses)
    if parallelisms:
        result["parallelisms"] = []
        for p in parallelisms:
            idx_a = p["verse_a_index"]
            idx_b = p["verse_b_index"]
            if idx_a < len(all_verses) and idx_b < len(all_verses):
                v_a = all_verses[idx_a]
                v_b = all_verses[idx_b]
                result["parallelisms"].append({
                    "type": p["type"],
                    "verse_a": f"{v_a.get('book_title', book)} {v_a['chapter']}:{v_a['verse']}",
                    "verse_b": f"{v_b.get('book_title', book)} {v_b['chapter']}:{v_b['verse']}",
                    "text_a": v_a.get("text_english", "")[:150],
                    "text_b": v_b.get("text_english", "")[:150],
                    "confidence": p["confidence"],
                })
    else:
        result["parallelisms"] = []

    conn.close()
    return result


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    book = args.get("book", "")
    chapter = args.get("chapter", 1)
    chapter_end = args.get("chapter_end", chapter)

    if not book:
        result = {"error": "Provide book and chapter"}
    else:
        result = analyze_passage(book, chapter, chapter_end)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
