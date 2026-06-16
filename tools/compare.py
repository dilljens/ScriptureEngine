#!/usr/bin/env python3
"""
MCP Tool: scripture_compare
Compare two scripture passages side by side.

Usage: python3 compare.py '{"verse_a": "gen.1.1", "verse_b": "john.1.1"}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, get_gematria_for_verse, get_verse_gematria_total
from lib.gematria import find_divine_name_matches, SACRED_NUMBERS


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    verse_a = args.get("verse_a", "")
    verse_b = args.get("verse_b", "")

    if not verse_a or not verse_b:
        print(json.dumps({"error": "Provide verse_a and verse_b"}))
        return

    conn = get_db()

    def get_verse_data(vid):
        row = conn.execute("""
            SELECT v.*, b.title as book_title
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (vid,)).fetchone()

        if not row:
            return None

        row = dict(row)
        gem_words = get_gematria_for_verse(conn, vid)
        gem_total = get_verse_gematria_total(conn, vid)

        # Find divine name matches
        name_matches = []
        for w in gem_words:
            matches = find_divine_name_matches(w["value_standard"])
            for m in matches:
                name_matches.append({
                    "word": w["word_hebrew"],
                    "divine_name": m["name"],
                    "value": w["value_standard"],
                })

        return {
            "verse_id": vid,
            "reference": f"{row['book_title']} {row['chapter']}:{row['verse']}",
            "text_english": row["text_english"],
            "text_hebrew": row.get("text_hebrew") or None,
            "has_hebrew": bool(row.get("has_hebrew")),
            "total_gematria_standard": gem_total.get("total_std", 0),
            "total_gematria_ordinal": gem_total.get("total_ord", 0),
            "word_count_in_hebrew": len(gem_words),
            "divine_name_matches": name_matches,
        }

    data_a = get_verse_data(verse_a)
    data_b = get_verse_data(verse_b)

    if not data_a:
        print(json.dumps({"error": f"Verse not found: {verse_a}"}))
        return
    if not data_b:
        print(json.dumps({"error": f"Verse not found: {verse_b}"}))
        return

    # Find similarities
    similarities = []
    if data_a["text_english"].lower() == data_b["text_english"].lower():
        similarities.append("Identical English text")
    if data_a["total_gematria_standard"] == data_b["total_gematria_standard"] and data_a["total_gematria_standard"] > 0:
        similarities.append(f"Same total gematria: {data_a['total_gematria_standard']}")
    if data_a["word_count_in_hebrew"] == data_b["word_count_in_hebrew"] and data_a["word_count_in_hebrew"] > 0:
        similarities.append(f"Same Hebrew word count: {data_a['word_count_in_hebrew']}")
    if data_a.get("text_hebrew") and data_b.get("text_hebrew"):
        a_hebrew_clean = data_a["text_hebrew"].replace("/", "").replace(" ", "")
        b_hebrew_clean = data_b["text_hebrew"].replace("/", "").replace(" ", "")
        if a_hebrew_clean == b_hebrew_clean:
            similarities.append("Identical Hebrew text")

    # Check gematria relationship
    ga = data_a["total_gematria_standard"] or 0
    gb = data_b["total_gematria_standard"] or 0
    if ga > 0 and gb > 0:
        if ga > gb and ga % gb == 0:
            similarities.append(f"Gematria ratio: {ga}/{gb} = {ga // gb}")
        elif gb > ga and gb % ga == 0:
            similarities.append(f"Gematria ratio: {gb}/{ga} = {gb // ga}")
        diff = abs(ga - gb)
        if diff in SACRED_NUMBERS:
            similarities.append(f"Gematria difference = {diff} ({SACRED_NUMBERS[diff]})")

    conn.close()

    result = {
        "verse_a": data_a,
        "verse_b": data_b,
        "similarities": similarities,
        "differences": {
            "gematria_delta": abs((data_b["total_gematria_standard"] or 0) - (data_a["total_gematria_standard"] or 0)),
            "hebrew_word_count_delta": abs(data_b["word_count_in_hebrew"] - data_a["word_count_in_hebrew"]),
        },
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
