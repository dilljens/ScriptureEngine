#!/usr/bin/env python3
"""
MCP Tool: scripture_keyword_distribution
Get distribution of key Hebrew terms across a book.

Usage:
  python3 keyword_distribution.py '{"book": "gen", "terms": ["יהוה", "אלהים", "ברית"]}'
  python3 keyword_distribution.py '{"book": "isa", "terms": ["קדוש", "ישע", "גוי"]}'
  python3 keyword_distribution.py '{"book": "psa", "terms": ["חסד", "אמת", "צדק"]}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, get_keyword_distribution


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    book = args.get("book", "")
    terms = args.get("terms", [])

    if not book or not terms:
        print(json.dumps({"error": "Provide book and terms list"}))
        return

    conn = get_db()
    dist = get_keyword_distribution(conn, book, terms)

    # Build a chapter-by-chapter matrix
    all_chapters = set()
    for term_data in dist.values():
        all_chapters.update(term_data.keys())

    chapter_matrix = []
    for ch in sorted(all_chapters):
        row = {"chapter": ch}
        for term in terms:
            row[term] = dist.get(term, {}).get(ch, 0)
        chapter_matrix.append(row)

    # Find key insights
    insights = []
    for term in terms:
        data = dist.get(term, {})
        if data:
            chapters_used = [c for c, cnt in data.items() if cnt > 0]
            total = sum(data.values())
            avg = round(total / max(len(data), 1), 1)
            peak_ch = max(data, key=data.get)
            insights.append({
                "term": term,
                "total_occurrences": total,
                "chapters_used": len(chapters_used),
                "avg_per_chapter": avg,
                "peak_chapter": int(peak_ch) if peak_ch else None,
                "peak_count": data.get(peak_ch, 0),
            })

    result = {
        "book": book,
        "terms": terms,
        "chapter_matrix": chapter_matrix,
        "insights": insights,
        "correlation_hints": [],
    }

    # Check for distribution signals useful for chiasm detection
    # If two terms have inverse patterns (one peaks early, the other late),
    # that could indicate a chiastic structure
    if len(terms) >= 2:
        for i, t1 in enumerate(terms):
            for t2 in terms[i + 1:]:
                d1 = dist.get(t1, {})
                d2 = dist.get(t2, {})
                chs = sorted(set(list(d1.keys()) + list(d2.keys())))
                if len(chs) >= 3:
                    # Check if they peak in opposite halves
                    mid = max(chs) / 2
                    t1_early = sum(d1.get(c, 0) for c in chs if c <= mid)
                    t1_late = sum(d1.get(c, 0) for c in chs if c > mid)
                    t2_early = sum(d2.get(c, 0) for c in chs if c <= mid)
                    t2_late = sum(d2.get(c, 0) for c in chs if c > mid)
                    t1_total = t1_early + t1_late
                    t2_total = t2_early + t2_late
                    if t1_total > 0 and t2_total > 0:
                        t1_ratio = t1_early / t1_total if t1_total > 0 else 0
                        t2_ratio = t2_early / t2_total if t2_total > 0 else 0
                        if (t1_ratio > 0.6 and t2_ratio < 0.4) or (t1_ratio < 0.4 and t2_ratio > 0.6):
                            result["correlation_hints"].append({
                                "terms": [t1, t2],
                                "description": f"'{t1}' and '{t2}' have inverse distributions — '{t1}' peaks in early chapters, '{t2}' in late chapters (or vice versa). Possible chiastic keyword mirroring.",
                            })

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
