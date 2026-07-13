#!/usr/bin/env python3
"""
MCP Tool: scripture_structural_formulas
Get structural formula markers for a book.

Usage:
  python3 structural_formulas.py '{"book": "gen"}'
  python3 structural_formulas.py '{"book": "gen", "formulas": ["toledot", "god_said"]}'
  python3 structural_formulas.py '{"book": "gen", "compute": true}'
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import add_formula_marker, get_db, get_formula_sequence

# Formula detection patterns
FORMULA_PATTERNS = {
    "toledot": [
        r"(?:these\s+(?:are\s+)?the\s+(?:book\s+of\s+)?(?:generations|genealogy|family\s+record))",
        r"תּוֹלְדוֹת",
        r"this\s+is\s+the\s+account",
    ],
    "god_said": [
        r"(?:and\s+)?god\s+said",
        r"וַיֹּאמֶר\s+אֱלֹהִים",
        r"the\s+lord\s+said",
        r"וַיֹּאמֶר\s+יְהוָה",
    ],
    "came_to_pass": [
        r"and\s+it\s+came\s+to\s+pass",
        r"וַיְהִי",
        r"and\s+it\s+shall\s+come\s+to\s+pass",
    ],
    "thus_says_lord": [
        r"thus\s+saith\s+(?:the\s+)?(?:lord|lord\s+god)",
        r"כֹּה\s+אָמַר\s+יְהוָה",
        r"thus\s+says\s+the\s+lord",
    ],
    "word_came": [
        r"the\s+word\s+of\s+(?:the\s+)?(?:lord|lord\s+god)\s+came",
        r"וַיְהִי\s+דְּבַר\s+יְהוָה",
    ],
    "hineni": [
        r"\bhineni\b",
        r"הִנְנִי",
    ],
    "woe": [
        r"\bwoe\s+(?:unto|to|is)\b",
        r"הוֹי",
    ],
    "behold": [
        r"\bbehold\b",
        r"הִנֵּה",
    ],
    "blessed": [
        r"\bblessed\s+(?:be\s+)?(?:the\s+)?(?:lord|god)\b",
        r"בָּרוּךְ",
    ],
}


def compute_formulas(conn, book_id):
    """Scan all verses in a book and detect formula markers."""
    rows = conn.execute("""
        SELECT v.id, v.chapter, v.verse, v.text_english
        FROM verses v WHERE v.book_id = ?
        ORDER BY v.chapter, v.verse
    """, (book_id,)).fetchall()

    # Delete existing formulas for this book
    conn.execute("DELETE FROM structural_formulas WHERE book_id = ?", (book_id,))

    count = 0
    for row in rows:
        text = row["text_english"].lower()
        for ftype, patterns in FORMULA_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    # Find the actual matched text
                    m = re.search(pat, row["text_english"], re.IGNORECASE)
                    matched_text = m.group(0) if m else text[:50]
                    count += 1
                    add_formula_marker(conn, book_id, row["id"], ftype,
                                      matched_text[:100], count)
                    break  # one formula type per verse max

    conn.commit()
    return count


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    book = args.get("book", "")
    formula_types = args.get("formulas")
    compute = args.get("compute", False)

    if not book:
        print(json.dumps({"error": "Provide book"}))
        return

    conn = get_db()

    # Compute formulas if requested
    if compute:
        count = compute_formulas(conn, book)
        # Don't return yet — also return the results below

    # Get formula sequence
    markers = get_formula_sequence(conn, book, formula_types=formula_types)

    # Group by type
    by_type = {}
    for m in markers:
        ft = m["formula_type"]
        if ft not in by_type:
            by_type[ft] = []
        by_type[ft].append({
            "position": m["position"],
            "verse": m["verse_id"],
            "formula_text": m["formula_text"],
            "context": (m.get("text_english", "") or "")[:100],
        })

    # Detect sequences for chiasm hints
    type_sequence = [m["formula_type"] for m in markers]
    mirror_hints = []
    seq_str = " → ".join(type_sequence[:20])
    if len(type_sequence) >= 5:
        # Check for palindrome/chiastic patterns in formula sequence
        mid = len(type_sequence) // 2
        for i in range(min(mid, 5)):
            if type_sequence[i] == type_sequence[-(i + 1)]:
                mirror_hints.append({
                    "position_a": i + 1,
                    "position_b": len(type_sequence) - i,
                    "formula": type_sequence[i],
                })

    result = {
        "book": book,
        "total_markers": len(markers),
        "by_type": {ft: len(items) for ft, items in by_type.items()},
        "details": by_type,
        "sequence_preview": seq_str,
        "mirror_hints": mirror_hints,
        "available_formula_types": list(FORMULA_PATTERNS.keys()),
    }

    if compute:
        result["computed"] = count

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
