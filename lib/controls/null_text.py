"""Null text generator — for statistical significance testing.

Generates two types of null text to compare against real biblical text:
1. Shuffled word order: same words, random arrangement
2. Random letter sequences: Hebrew-like text with same letter frequency

If a pattern detector finds the same number of connections in null text
as in real text, the pattern is not statistically significant.
"""

import random
import os
from collections import Counter

# Hebrew letter frequency in the Bible (approximate, from WLC)
HEBREW_LETTER_FREQ = {
    'א': 0.063, 'ב': 0.052, 'ג': 0.021, 'ד': 0.025, 'ה': 0.089,
    'ו': 0.114, 'ז': 0.013, 'ח': 0.023, 'ט': 0.007, 'י': 0.094,
    'כ': 0.036, 'ל': 0.071, 'מ': 0.049, 'נ': 0.042, 'ס': 0.013,
    'ע': 0.024, 'פ': 0.016, 'צ': 0.010, 'ק': 0.015, 'ר': 0.048,
    'ש': 0.044, 'ת': 0.031,
}

# Average Hebrew word length in the Bible
AVG_WORD_LENGTH = 4.5


def generate_shuffled_words(conn, book_ids=None, ratio=0.1):
    """Generate shuffled-word-order null text.
    
    Takes actual Hebrew words from the Bible (or a subset), shuffles
    their order while preserving total word count and book structure.
    
    Args:
        conn: database connection
        book_ids: list of book IDs to sample from (None = all)
        ratio: fraction of total words to include (0.1 = 10% ≈ 30K words)
    
    Returns:
        list of shuffled word strings
    """
    query = """
        SELECT word_hebrew FROM gematria
    """
    params = []
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" JOIN verses v ON v.id = gematria.verse_id WHERE v.book_id IN ({placeholders})"
        params.extend(book_ids)
    
    rows = conn.execute(query, params).fetchall()
    
    # Extract words
    words = []
    for r in rows:
        w = r["word_hebrew"].strip()
        if w:
            words.append(w)
    
    # Sample if needed
    if ratio < 1.0:
        sample_size = max(1000, int(len(words) * ratio))
        words = random.sample(words, sample_size)
    
    # Shuffle
    random.shuffle(words)
    return words


def generate_random_hebrew(num_words=30000, seed=42):
    """Generate random Hebrew-like text.
    
    Uses the same letter frequency distribution as the real Bible
    but with random sequences that form no meaningful words.
    
    Args:
        num_words: number of random words to generate
        seed: random seed for reproducibility
    
    Returns:
        list of randomly generated Hebrew word strings
    """
    random.seed(seed)
    
    # Build weighted letter list
    letters = list(HEBREW_LETTER_FREQ.keys())
    weights = list(HEBREW_LETTER_FREQ.values())
    
    words = []
    for _ in range(num_words):
        # Generate a word of random Hebrew-like length
        word_len = max(1, int(random.gauss(AVG_WORD_LENGTH, 1.5)))
        word = "".join(random.choices(letters, weights=weights, k=word_len))
        words.append(word)
    
    return words


def generate_and_store(conn):
    """Generate both null texts and store them for revalidation.
    
    Used by the validation script. Stores as reference.
    Returns (shuffled_words, random_words) for use in tests.
    """
    print("  Generating shuffled-word null text...", flush=True)
    shuffled = generate_shuffled_words(conn, ratio=0.1)
    
    print(f"  Generated {len(shuffled)} shuffled words", flush=True)
    
    print("  Generating random-letter null text...", flush=True)
    random_words = generate_random_hebrew(num_words=30000)
    
    print(f"  Generated {len(random_words)} random Hebrew words", flush=True)
    
    return shuffled, random_words


def count_matches_in_null(null_type, all_words, test_function, **kwargs):
    """Count how many 'connections' a function finds in null text.
    
    Args:
        null_type: 'shuffled' or 'random'
        all_words: list of null text word strings
        test_function: function(word_list, **kwargs) -> count
        **kwargs: additional args to pass to test_function
    
    Returns:
        count of patterns found in null text
    """
    return test_function(None, all_words, **kwargs)
