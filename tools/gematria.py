#!/usr/bin/env python3
"""
MCP Tool: scripture_gematria
Get gematria values for a word or verse.

Usage: python3 gematria.py '{"word": "יהוה"}'
       python3 gematria.py '{"verse": "gen.1.1"}'
       python3 gematria.py '{"value": 26, "system": "standard"}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, get_gematria_for_verse, find_matching_gematria
from lib.gematria import (compute_all, find_divine_name_matches,
                          is_sacred_number, DIVINE_NAMES,
                          get_divine_names_table, SACRED_NUMBERS)
from lib.hebrew_util import rtl_mark, transliterate


def word_lookup(word):
    """Look up gematria for a specific word."""
    values = compute_all(word)
    divine_matches = find_divine_name_matches(values["standard"])

    result = {
        "word": word,
        "hebrew_display": {
            "text": rtl_mark(word),
            "transliteration": transliterate(word, strip_accents=False),
        },
        "gematria": values,
        "divine_name_matches": divine_matches,
        "is_sacred_number": {
            "standard": is_sacred_number(values["standard"]),
        },
    }

    # Check if this value is a sacred number
    if values["standard"] in SACRED_NUMBERS:
        result["sacred_number_meaning"] = SACRED_NUMBERS[values["standard"]]

    return result


def verse_lookup(verse_id, conn=None):
    """Get all gematria data for a verse."""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True

    try:
        words = get_gematria_for_verse(conn, verse_id)
        if not words:
            return {"error": f"No gematria data for {verse_id}"}

        total_std = sum(w["value_standard"] for w in words)
        total_ord = sum(w["value_ordinal"] for w in words)
        total_red = sum(w["value_reduced"] for w in words)

        # Find divine name matches in individual words
        matched_names = []
        for w in words:
            matches = find_divine_name_matches(w["value_standard"])
            for m in matches:
                matched_names.append({
                    "word": w["word_hebrew"],
                    "word_index": w["word_index"],
                    "divine_name": m["name"],
                    "value": w["value_standard"],
                })

        # Check if total has significance
        total_significance = None
        if total_std in SACRED_NUMBERS:
            total_significance = SACRED_NUMBERS[total_std]

        result = {
            "verse_id": verse_id,
            "word_count": len(words),
            "totals": {
                "standard": total_std,
                "ordinal": total_ord,
                "reduced": total_red,
            },
            "total_significance": total_significance,
            "divine_name_matches_in_words": matched_names,
            "words": [
                {
                    "index": w["word_index"],
                    "hebrew": w["word_hebrew"],
                    "standard": w["value_standard"],
                    "ordinal": w["value_ordinal"],
                    "reduced": w["value_reduced"],
                }
                for w in words
            ],
        }

        return result
    finally:
        if close_conn:
            conn.close()


def value_search(value, system="standard", limit=30):
    """Find matches for a specific gematria value."""
    conn = get_db()

    divine_matches = find_divine_name_matches(value, system)
    sacred = is_sacred_number(value)
    sacred_meaning = SACRED_NUMBERS.get(value)

    results = find_matching_gematria(conn, value, system=system, limit=limit)

    conn.close()

    return {
        "value": value,
        "system": system,
        "total_matches": len(results),
        "divine_name_matches": divine_matches,
        "is_sacred_number": sacred,
        "sacred_number_meaning": sacred_meaning,
        "matches": [
            {
                "verse_id": r.get("vid") or r.get("verse_id"),
                "word_hebrew": r["word_hebrew"],
                "word_english": r.get("word_english", ""),
                "book": r.get("book_title", ""),
                "context": r.get("text_english", "")[:100],
            }
            for r in results
        ],
    }


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    if "word" in args:
        result = word_lookup(args["word"])
    elif "verse" in args:
        result = verse_lookup(args["verse"])
    elif "value" in args:
        system = args.get("system", "standard")
        result = value_search(args["value"], system, args.get("limit", 30))
    elif "divine_names" in args:
        result = {"divine_names": get_divine_names_table()}
    else:
        result = {"error": "Provide word, verse, value, or divine_names"}

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
