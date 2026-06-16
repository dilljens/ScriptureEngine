"""
Giliadi-style word-count chiastic detection.

Avraham Giliadi's methodology:
1. Biblical books have "integral structures" — unified chiastic designs
2. Word counts in mirrored sections correspond (exactly or proportionally)
3. The center section is the theological pivot
4. Structures can be multi-level (chiasm within chiasm)

This module implements the word-count mirroring detection algorithm.
"""

from collections import defaultdict
from ..db import get_db, get_word_counts_by_chapter, get_word_counts_by_verse_range


def detect_word_count_chiasms(conn, book_id, methods=("chapter", "even_divide", "sliding")):
    """Run Giliadi-style word-count chiastic detection.

    Args:
        conn: database connection
        book_id: book to analyze
        methods: tuple of methods to try
            'chapter': use chapter boundaries
            'even_divide': divide chapters evenly into N sections
            'sliding': sliding window across different section counts

    Returns:
        list of candidate chiastic structures with scores
    """
    # Get chapter-by-chapter Hebrew word counts
    chap_data = get_word_counts_by_chapter(conn, book_id)
    if not chap_data:
        return []

    chapters = [c["chapter"] for c in chap_data]
    word_counts = [c.get("heb_word_count", 0) for c in chap_data]
    num_chapters = len(chapters)

    candidates = []

    # Method 1: Chapter boundaries (most natural division)
    if "chapter" in methods and num_chapters >= 5:
        candidates.extend(_scan_word_count_mirror(
            word_counts, chapters, method_name="chapter_boundaries"
        ))

    # Method 2: Even division into N sections
    if "even_divide" in methods:
        for num_sections in range(5, min(num_chapters, 13) + 1, 2):
            # Try different offsets for grouping chapters
            for offset in range(num_sections):
                section_word_counts = []
                section_labels = []
                section_size = num_chapters / num_sections

                for s in range(num_sections):
                    start_idx = max(0, int(s * section_size) + offset)
                    end_idx = min(num_chapters, int((s + 1) * section_size) + offset)
                    if start_idx < end_idx:
                        total = sum(word_counts[start_idx:end_idx])
                        section_word_counts.append(total)
                        section_labels.append(f"ch.{chapters[start_idx]}-{chapters[end_idx-1]}")

                if len(section_word_counts) >= 5 and len(section_word_counts) % 2 == 1:
                    candidates.extend(_scan_word_count_mirror(
                        section_word_counts, section_labels,
                        method_name=f"even_divide_{num_sections}sections_offset{offset}"
                    ))

    # Method 3: Sliding window — try different center points
    if "sliding" in methods and num_chapters >= 7:
        for center_idx in range(2, num_chapters - 2):
            max_span = min(center_idx, num_chapters - center_idx - 1, 5)
            for span in range(2, max_span + 1):
                left_indices = list(range(center_idx - span, center_idx))
                right_indices = list(range(center_idx + 1, center_idx + span + 1))

                section_wcs = []
                section_labels = []

                # Build sections from outside-in
                for i in range(span):
                    left_ch = chapters[left_indices[i]]
                    right_ch = chapters[right_indices[-(i + 1)]]
                    left_wc = word_counts[left_indices[i]]
                    right_wc = word_counts[right_indices[-(i + 1)]]
                    section_wcs.append(left_wc)
                    section_wcs.append(right_wc)
                    section_labels.append(f"L{i+1}:ch{left_ch}")
                    section_labels.append(f"R{i+1}:ch{right_ch}")

                # Add center
                section_wcs.append(word_counts[center_idx])
                section_labels.append(f"CENTER:ch{chapters[center_idx]}")

                candidates.extend(_scan_word_count_mirror(
                    section_wcs, section_labels,
                    method_name=f"sliding_center_ch{chapters[center_idx]}_span{span}"
                ))

    # Sort by score
    candidates.sort(key=lambda c: c["score"], reverse=True)

    return candidates


def _scan_word_count_mirror(word_counts, labels, method_name=""):
    """Scan a list of word counts for chiastic mirror patterns.

    Args:
        word_counts: list of Hebrew word counts per section
        labels: labels for each section (chapter numbers, etc.)
        method_name: name of the detection method used

    Returns:
        list of candidate dicts
    """
    n = len(word_counts)
    if n < 5 or n % 2 == 0:
        return []

    candidates = []
    num_pairs = n // 2
    pair_scores = []
    total_score = 0

    for i in range(num_pairs):
        j = -(i + 1)
        a = word_counts[i]
        b = word_counts[j]

        if a > 0 and b > 0:
            ratio = max(a, b) / max(min(a, b), 1)
            # Score: 1.0 at perfect match, 0.0 at 1.25 ratio
            if ratio <= 1.25:
                pair_score = max(0, 1.0 - (ratio - 1.0) * 4)
            else:
                pair_score = 0
        else:
            pair_score = 0
            ratio = 0

        pair_scores.append({
            "pair": f"{labels[i]} ↔ {labels[j]}",
            "word_count_a": a,
            "word_count_b": b,
            "ratio": round(ratio, 3),
            "pair_score": round(pair_score, 3),
        })
        total_score += pair_score

    avg_score = total_score / max(num_pairs, 1)

    if avg_score > 0.3:
        center_idx = n // 2
        center_count = word_counts[center_idx] if center_idx < len(word_counts) else 0

        candidates.append({
            "method": method_name,
            "num_sections": n,
            "num_pairs": num_pairs,
            "score": round(avg_score, 3),
            "word_counts": word_counts,
            "labels": labels,
            "pairs": pair_scores,
            "center_word_count": center_count,
            "center_label": labels[center_idx] if center_idx < len(labels) else "",
        })

    return candidates


def find_giliadi_patterns(conn, book_id):
    """High-level: run Giliadi detection and return structured results."""
    candidates = detect_word_count_chiasms(conn, book_id)

    result = {
        "book": book_id,
        "method": "Giliadi word-count mirroring",
        "total_candidates": len(candidates),
    }

    if candidates:
        result["top_candidate"] = candidates[0]
        result["all_candidates"] = candidates[:5]
        result["summary"] = {
            "best_score": candidates[0]["score"],
            "best_method": candidates[0]["method"],
            "num_good_candidates": sum(1 for c in candidates if c["score"] > 0.5),
        }

    return result


def compare_giliadi_methods(conn, book_id):
    """Run all three methods and compare results."""
    chapter_results = detect_word_count_chiasms(conn, book_id, methods=("chapter",))
    even_results = detect_word_count_chiasms(conn, book_id, methods=("even_divide",))
    sliding_results = detect_word_count_chiasms(conn, book_id, methods=("sliding",))

    return {
        "book": book_id,
        "chapter_method": {
            "count": len(chapter_results),
            "best_score": chapter_results[0]["score"] if chapter_results else 0,
        },
        "even_divide_method": {
            "count": len(even_results),
            "best_score": even_results[0]["score"] if even_results else 0,
        },
        "sliding_method": {
            "count": len(sliding_results),
            "best_score": sliding_results[0]["score"] if sliding_results else 0,
        },
        "combined_candidates": sorted(
            chapter_results + even_results + sliding_results,
            key=lambda c: c["score"], reverse=True
        )[:10],
    }
