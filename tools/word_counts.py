#!/usr/bin/env python3
"""
MCP Tool: scripture_word_counts
Get Hebrew word count distribution across a book or passage.

Usage:
  python3 word_counts.py '{"book": "isa", "mode": "per_chapter"}'
  python3 word_counts.py '{"book": "gen", "mode": "by_formula", "formula": "toledot"}'
  python3 word_counts.py '{"book": "gen", "mode": "all_three"}'
  python3 word_counts.py '{"book": "gen", "mode": "custom", "sections": [
    {"label":"A","start":"gen.1.1","end":"gen.2.3"},
    {"label":"B","start":"gen.2.4","end":"gen.3.24"}
  ]}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, get_word_counts_by_chapter, get_word_counts_by_verse_range
from lib.db import get_section_verses, get_formula_sequence


def detect_formula_sections(schema_check):
    """Detect formula types available in the database."""
    # Will be populated once formulas are computed
    return {"toledot", "god_said", "came_to_pass", "thus_says_lord", "word_came"}


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    book = args.get("book", "")
    mode = args.get("mode", "per_chapter")

    if not book:
        print(json.dumps({"error": "Provide book"}))
        return

    conn = get_db()
    result = {"book": book, "mode": mode}

    if mode == "per_chapter":
        # Word counts per chapter
        counts = get_word_counts_by_chapter(conn, book)
        if not counts:
            # Try English word counts as fallback
            rows = conn.execute("""
                SELECT chapter, SUM(LENGTH(text_english) - LENGTH(REPLACE(text_english, ' ', '')) + 1) as word_count
                FROM verses WHERE book_id = ? GROUP BY chapter ORDER BY chapter
            """, (book,)).fetchall()
            counts = [dict(r) for r in rows]

        result["chapter_word_counts"] = counts
        total = sum(c.get("heb_word_count") or c.get("word_count", 0) for c in counts)
        result["total_word_count"] = total
        result["chapter_count"] = len(counts)
        result["avg_per_chapter"] = round(total / max(len(counts), 1), 1)

        # Check for interesting patterns
        if len(counts) >= 5:
            # Check if first and last chapters have similar word counts (possible chiasm signal)
            first_last_ratio = None
            if counts[0].get("heb_word_count", 0) > 0 and counts[-1].get("heb_word_count", 0) > 0:
                first = counts[0]["heb_word_count"]
                last = counts[-1]["heb_word_count"]
                ratio = max(first, last) / max(min(first, last), 1)
                first_last_ratio = {"first": first, "last": last, "ratio": round(ratio, 2)}

            result["signals"] = {}
            if first_last_ratio:
                result["signals"]["first_last_ratio"] = first_last_ratio
                if 0.8 <= first_last_ratio["ratio"] <= 1.2:
                    result["signals"]["first_last_note"] = "First and last chapters have similar word counts — potential chiastic outer layer"

    elif mode == "by_formula":
        # Word counts between formula markers
        formula = args.get("formula", "toledot")
        markers = get_formula_sequence(conn, book, formula_types=[formula])

        if not markers:
            result["error"] = f"No '{formula}' markers found for {book}"
        else:
            sections = []
            for i, marker in enumerate(markers):
                start_vid = marker["verse_id"]
                if i + 1 < len(markers):
                    end_vid = markers[i + 1]["verse_id"]
                else:
                    # Get last verse of book
                    last = conn.execute("""
                        SELECT id FROM verses WHERE book_id = ? ORDER BY chapter DESC, verse DESC LIMIT 1
                    """, (book,)).fetchone()
                    end_vid = last["id"] if last else start_vid

                wc = get_word_counts_by_verse_range(conn, start_vid, end_vid)
                sections.append({
                    "section": i + 1,
                    "marker": marker["formula_text"],
                    "start": start_vid,
                    "end": end_vid,
                    "hebrew_word_count": wc,
                })

            result["sections"] = sections
            result["section_count"] = len(sections)

            # Look for mirror patterns in section word counts
            wcs = [s["hebrew_word_count"] for s in sections]
            mirror_hints = []
            for i in range(len(wcs) // 2):
                j = -(i + 1)
                left, right = wcs[i], wcs[j]
                if left > 0 and right > 0:
                    ratio = max(left, right) / max(min(left, right), 1)
                    if ratio <= 1.25:
                        mirror_hints.append({
                            "section_a": i + 1,
                            "section_b": len(wcs) + j + 1,
                            "word_count_a": left,
                            "word_count_b": right,
                            "ratio": round(ratio, 2),
                        })
            result["mirror_hints"] = mirror_hints

    elif mode == "custom":
        sections = args.get("sections", [])
        result["sections"] = []
        for sec in sections:
            wc = get_word_counts_by_verse_range(conn, sec["start"], sec["end"])
            result["sections"].append({
                "label": sec.get("label", ""),
                "start": sec["start"],
                "end": sec["end"],
                "hebrew_word_count": wc,
            })

        # Mirror check for custom sections
        wcs = [s["hebrew_word_count"] for s in result["sections"]]
        mirror_hints = []
        for i in range(len(wcs) // 2):
            j = -(i + 1)
            left, right = wcs[i], wcs[j]
            if left > 0 and right > 0:
                ratio = max(left, right) / max(min(left, right), 1)
                if ratio <= 1.25:
                    mirror_hints.append({
                        "pair": f"{result['sections'][i]['label']}↔{result['sections'][j]['label']}",
                        "a_word_count": left,
                        "b_word_count": right,
                        "ratio": round(ratio, 2),
                    })
        result["mirror_hints"] = mirror_hints

    elif mode == "all_three":
        # Run all three methods and return combined results
        result["per_chapter"] = json.loads(main_inner(conn, book, "per_chapter"))
        result["by_formula_toledot"] = json.loads(main_inner(conn, book, "by_formula"))

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main_inner(conn, book, mode):
    """Helper to run one mode and return JSON string."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        # Can't call ourselves recursively, so duplicate logic inline
        pass
    return buf.getvalue()


if __name__ == "__main__":
    main()
