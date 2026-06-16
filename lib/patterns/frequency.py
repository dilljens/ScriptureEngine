"""
Frequency and distribution analysis for scripture.

Tracks word/phrase occurrences across canon, books, and chapters.
Identifies significant patterns (seven-fold, forty-days, etc.).
"""

import re
from collections import Counter, defaultdict


SACRED_COUNTS = {
    1: "Unique occurrence",
    3: "Divine emphasis / completeness",
    7: "Divine perfection / rest",
    10: "Divine order / completeness",
    12: "Divine government",
    24: "Heavenly worship (24 elders)",
    30: "Preparation / dedication",
    40: "Testing / trial / preparation",
    50: "Jubilee / redemption",
    70: "Nations / council of elders",
    120: "Divine waiting period",
    1000: "Divine fullness / day as a thousand years",
}


def count_occurrences(text_corpus, target_word):
    """Count occurrences of a word/phrase across a corpus.

    Args:
        text_corpus: list of (verse_id, text) tuples
        target_word: word or phrase to count

    Returns:
        dict with counts by scope
    """
    word_lower = target_word.lower()
    total = 0
    by_book = Counter()
    by_chapter = Counter()

    for verse_id, text in text_corpus:
        count = text.lower().count(word_lower)
        if count > 0:
            total += count
            # Parse verse_id: "gen.1.1"
            parts = verse_id.split(".")
            if len(parts) >= 2:
                book = parts[0]
                by_book[book] += count
                if len(parts) >= 2:
                    chapter = f"{book}.{parts[1]}"
                    by_chapter[chapter] += count

    return {
        "word": target_word,
        "total": total,
        "by_book": dict(by_book.most_common()),
        "by_chapter": dict(by_chapter.most_common(30)),
    }


def find_formula_count(text_corpus, formula):
    """Count how many times a structural formula appears.

    Common formulas:
    - "And it came to pass"
    - "Thus says the Lord"
    - "The word of the Lord came"
    - "And God said"
    """
    return count_occurrences(text_corpus, formula)


def sacred_count_significance(count):
    """Check if a count has significance as a sacred number."""
    if count in SACRED_COUNTS:
        return SACRED_COUNTS[count]
    # Check for multiples of 7
    if count > 0 and count % 7 == 0 and count <= 777:
        return f"Multiple of 7 ({count} = {count//7} × 7)"
    # Check for factors of 40
    if count > 0 and count % 40 == 0 and count <= 400:
        return f"Multiple of 40 ({count} = {count//40} × 40)"
    return None


def find_phrases_by_pattern(corpus, pattern_type):
    """Find phrases that follow specific frequency patterns.

    pattern_type: 'seven_fold', 'forty_day', 'twelve_fold'
    """
    results = []
    # Build a word frequency index from the corpus
    word_freq = Counter()
    for verse_id, text in corpus:
        words = re.findall(r"[a-zA-Z']+", text.lower())
        word_freq.update(w for w in words if len(w) > 2)

    target_counts = {
        "seven_fold": 7,
        "forty_day": 40,
        "twelve_fold": 12,
    }

    target = target_counts.get(pattern_type)
    if not target:
        return results

    # Find words that appear exactly target times
    for word, count in word_freq.most_common(200):
        if count == target and len(word) > 2:
            significance = sacred_count_significance(count)
            results.append({
                "word": word,
                "count": count,
                "significance": significance,
                "pattern_type": pattern_type,
            })

    return results
