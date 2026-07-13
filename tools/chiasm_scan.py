#!/usr/bin/env python3
"""
MCP Tool: scripture_chiasm_scan
Algorithmic pre-scan for chiastic candidates in a book.

Uses three methods to find candidate structures:
  - word_count: Giliadi-style word count mirroring
  - keyword: keyword distribution mirroring
  - formula: structural formula sequence mirroring

Usage:
  python3 chiasm_scan.py '{"book": "gen"}'
  python3 chiasm_scan.py '{"book": "gen", "methods": ["word_count", "keyword"]}'
  python3 chiasm_scan.py '{"book": "gen", "min_sections": 5, "max_sections": 11}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import (
    find_matching_known_chiasm,
    get_db,
    get_formula_sequence,
    get_keyword_distribution,
    get_word_counts_by_chapter,
)

# Key Hebrew theological terms for keyword analysis
KEY_TERMS = {
    "gen": ["יהוה", "אלהים", "ברית", "ברך", "זרע", "ארץ", "שמים"],
    "exo": ["יהוה", "אלהים", "מצרים", "משה", "ברית", "עבד", "אות"],
    "lev": ["יהוה", "קדש", "חטא", "קרבן", "כהן", "אהרן", "דם"],
    "num": ["יהוה", "משה", "אהרן", "עדה", "מחנה", "חטא", "נשיא"],
    "deu": ["יהוה", "משה", "ברית", "מצוה", "חוק", "ארץ", "עם"],
    "isa": ["יהוה", "ישע", "ציון", "גוי", "קדוש", "עבד", "משפט"],
    "psa": ["יהוה", "אלהים", "חסד", "צדק", "אמת", "נפש", "מלך"],
}


def try_all_divisions(conn, book_id):
    """Try all possible book divisions and score each for chiastic structure."""
    # Get chapter word counts
    chap_counts = get_word_counts_by_chapter(conn, book_id)
    num_chapters = len(chap_counts)
    word_counts = [c.get("heb_word_count", 0) for c in chap_counts]

    candidates = []

    # Try odd-numbered section divisions from 5 to min(num_chapters, 11)
    max_sections = min(num_chapters, 11)
    min_sections = min(5, num_chapters)

    for num_sections in range(min_sections, max_sections + 1, 2):
        # Try different groupings of chapters into sections
        # Simple approach: divide equally
        section_size = num_chapters / num_sections

        for offset in range(num_sections):
            sections = []
            for s in range(num_sections):
                start_ch = max(1, int(s * section_size) + offset + 1)
                end_ch = min(num_chapters, int((s + 1) * section_size) + offset)
                if start_ch <= end_ch:
                    total = sum(word_counts[start_ch - 1:end_ch])
                    sections.append({"label": chr(65 + s), "start_ch": start_ch, "end_ch": end_ch, "word_count": total})

            if len(sections) < 5:
                continue

            # Score for chiastic mirroring
            score = 0
            pairs = []
            for i in range(len(sections) // 2):
                j = -(i + 1)
                a = sections[i]
                b = sections[j]
                if a["word_count"] > 0 and b["word_count"] > 0:
                    ratio = max(a["word_count"], b["word_count"]) / max(min(a["word_count"], b["word_count"]), 1)
                    if ratio <= 1.15:
                        pair_score = 1.0 - (ratio - 1.0) * 5  # 1.0 at ratio=1.0, 0.0 at ratio=1.2
                        score += max(0, pair_score)
                        pairs.append({
                            "a": a["label"], "b": b["label"],
                            "a_chapters": f"{a['start_ch']}-{a['end_ch']}",
                            "b_chapters": f"{b['start_ch']}-{b['end_ch']}",
                            "a_word_count": a["word_count"],
                            "b_word_count": b["word_count"],
                            "ratio": round(ratio, 3),
                            "pair_score": round(max(0, pair_score), 2),
                        })

            if pairs:
                max_possible = len(sections) // 2
                total_score = score / max_possible if max_possible > 0 else 0

                if total_score > 0.3:
                    center = sections[len(sections) // 2]
                    candidates.append({
                        "num_sections": num_sections,
                        "score": round(total_score, 3),
                        "pairs": pairs,
                        "center": f"Chapters {center['start_ch']}-{center['end_ch']} (word count: {center['word_count']})",
                        "method": "word_count_mirroring",
                    })

    # Sort by score
    candidates.sort(key=lambda c: c["score"], reverse=True)

    return candidates[:10]


def check_keyword_mirror(conn, book_id):
    """Check if key terms have mirror distributions."""
    terms = KEY_TERMS.get(book_id, ["יהוה", "אלהים"])
    dist = get_keyword_distribution(conn, book_id, terms)

    # Check for inversion patterns (term A peaks early, term B peaks late)
    hints = []
    term_list = list(dist.keys())
    for i, t1 in enumerate(term_list):
        for t2 in term_list[i + 1:]:
            d1 = dist.get(t1, {})
            d2 = dist.get(t2, {})
            if not d1 or not d2:
                continue
            chs = sorted(set(list(d1.keys()) + list(d2.keys())))
            if len(chs) < 4:
                continue
            mid = max(chs) / 2
            t1_early = sum(d1.get(c, 0) for c in chs if c <= mid)
            t1_late = sum(d1.get(c, 0) for c in chs if c > mid)
            t2_early = sum(d2.get(c, 0) for c in chs if c <= mid)
            t2_late = sum(d2.get(c, 0) for c in chs if c > mid)
            if t1_early + t1_late > 0 and t2_early + t2_late > 0:
                t1_ratio = t1_early / (t1_early + t1_late)
                t2_ratio = t2_early / (t2_early + t2_late)
                if (t1_ratio > 0.6 and t2_ratio < 0.4) or (t1_ratio < 0.4 and t2_ratio > 0.6):
                    hints.append({
                        "term_a": t1, "term_b": t2,
                        f"{t1}_early_ratio": round(t1_ratio, 2),
                        f"{t2}_early_ratio": round(t2_ratio, 2),
                        "note": f"'{t1}' and '{t2}' have inverted distributions — possible chiastic keyword pairing",
                    })

    return hints


def check_formula_mirror(conn, book_id):
    """Check if structural formula sequence has mirror patterns."""
    markers = get_formula_sequence(conn, book_id)
    types = [m["formula_type"] for m in markers]

    hints = []
    if len(types) >= 5:
        for i in range(min(len(types) // 2, 6)):
            if types[i] == types[-(i + 1)]:
                hints.append({
                    "position_a": i + 1,
                    "position_b": len(types) - i,
                    "formula": types[i],
                    "note": f"Formula '{types[i]}' at positions {i+1} and {len(types)-i} — possible structural mirror",
                })

    return hints


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    book = args.get("book", "")
    methods = args.get("methods", ["word_count", "keyword", "formula"])
    args.get("min_sections", 5)
    args.get("max_sections", 11)

    if not book:
        print(json.dumps({"error": "Provide book"}))
        return

    conn = get_db()
    result = {"book": book}

    candidates = []
    keyword_hints = []
    formula_hints = []

    if "word_count" in methods:
        candidates = try_all_divisions(conn, book)
        result["word_count_candidates"] = candidates

    if "keyword" in methods:
        keyword_hints = check_keyword_mirror(conn, book)
        result["keyword_mirror_hints"] = keyword_hints

    if "formula" in methods:
        formula_hints = check_formula_mirror(conn, book)
        result["formula_mirror_hints"] = formula_hints

    # Check against known patterns
    if candidates:
        best = candidates[0]
        if best["pairs"]:
            best["pairs"][0]
            # Try to find a matching known chiasm
            find_matching_known_chiasm(conn, "", "")
            # This would need verse IDs from the chapter mapping
            # For now, just note the comparison
            result["known_patterns_check"] = "Run known_patterns.py with specific verse ranges to cross-reference"

    # Summary
    result["summary"] = {
        "total_candidates": len(candidates),
        "keyword_inversions": len(keyword_hints),
        "formula_mirrors": len(formula_hints),
        "top_candidate_score": candidates[0]["score"] if candidates else 0,
    }

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
