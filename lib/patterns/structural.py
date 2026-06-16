"""
Structural formula sequence analysis.

Tracks sequences of structural formulas across a book to identify:
- Chiastic formula sequences (mirrored formula types at distance)
- Structural skeletons (the "spine" of a book)
- Formula density patterns (where formulas cluster)
"""

import re
from collections import defaultdict, Counter
from ..db import get_db, get_formula_sequence


# Formula type categories
FORMULA_CATEGORIES = {
    "toledot": "structural_divider",
    "god_said": "divine_speech",
    "came_to_pass": "narrative_marker",
    "thus_says_lord": "prophetic_formula",
    "word_came": "prophetic_formula",
    "hineni": "response",
    "woe": "judgment",
    "behold": "attention",
    "blessed": "praise",
}


def get_structural_skeleton(conn, book_id):
    """Get the structural skeleton of a book — the sequence of formula markers.

    Returns a simplified sequence of formula types as a string pattern.
    """
    markers = get_formula_sequence(conn, book_id)
    if not markers:
        return {"book": book_id, "markers": [], "pattern": "", "note": "No formulas computed yet"}

    pattern = [m["formula_type"] for m in markers]
    categories = [FORMULA_CATEGORIES.get(m["formula_type"], "other") for m in markers]

    return {
        "book": book_id,
        "total_markers": len(markers),
        "type_sequence": pattern,
        "category_sequence": categories,
        "pattern_string": " → ".join(pattern[:30]),
        "marker_density": round(len(markers) / max(1, _get_book_chapters(conn, book_id)), 2),
    }


def _get_book_chapters(conn, book_id):
    """Get the number of chapters in a book."""
    row = conn.execute("""
        SELECT MAX(chapter) as max_ch FROM verses WHERE book_id = ?
    """, (book_id,)).fetchone()
    return row["max_ch"] if row else 1


def detect_chiastic_formula_sequence(conn, book_id):
    """Check if the structural formula sequence has chiastic mirroring.

    A chiastic formula sequence would have a pattern like:
    A → B → C → ... → C → B → A
    where A, B, C are formula types.
    """
    markers = get_formula_sequence(conn, book_id)
    types = [m["formula_type"] for m in markers]

    if len(types) < 5:
        return []

    chiasm_candidates = []

    # Check for palindrome/mirror in the sequence
    for center in range(1, len(types) - 1):
        for span in range(1, min(center, len(types) - center - 1, 5) + 1):
            left = types[center - span]
            right = types[center + span]

            if left == right:
                # Found a mirror pair — check inner pairs too
                inner_pairs = 0
                for i in range(1, span):
                    if types[center - i] == types[center + i]:
                        inner_pairs += 1

                total_layers = span
                score = (1 + inner_pairs) / max(total_layers, 1)

                if score >= 0.5:
                    chiasm_candidates.append({
                        "center_marker": markers[center],
                        "center_position": center,
                        "outer_span": span,
                        "matching_inner_pairs": inner_pairs,
                        "total_inner_layers": total_layers,
                        "score": round(score, 2),
                        "type": "formula_sequence_chiasm",
                    })

    return chiasm_candidates


def get_formula_density_analysis(conn, book_id):
    """Analyze where formula markers cluster in a book.

    High-density regions are likely structural pivots or transitions.
    """
    markers = get_formula_sequence(conn, book_id)
    if not markers:
        return {"book": book_id, "note": "No formulas computed"}

    # Group by chapter
    by_chapter = defaultdict(list)
    for m in markers:
        verse_parts = m["verse_id"].split(".")
        if len(verse_parts) >= 2:
            try:
                ch = int(verse_parts[1])
                by_chapter[ch].append(m)
            except ValueError:
                pass

    chapter_density = [
        {"chapter": ch, "marker_count": len(items), "types": [m["formula_type"] for m in items]}
        for ch, items in sorted(by_chapter.items())
    ]

    peak_chapters = sorted(chapter_density, key=lambda c: c["marker_count"], reverse=True)[:5]

    return {
        "book": book_id,
        "total_markers": len(markers),
        "chapter_density": chapter_density,
        "peak_chapters": peak_chapters,
        "avg_per_chapter": round(len(markers) / max(len(chapter_density), 1), 1),
    }


def get_formula_type_breakdown(conn, book_id):
    """Get a breakdown of formula types for a book."""
    markers = get_formula_sequence(conn, book_id)
    if not markers:
        return {}

    counts = Counter(m["formula_type"] for m in markers)
    by_category = defaultdict(int)
    for m in markers:
        cat = FORMULA_CATEGORIES.get(m["formula_type"], "other")
        by_category[cat] += 1

    return {
        "book": book_id,
        "by_type": dict(counts.most_common()),
        "by_category": dict(by_category),
    }
