"""
Chiastic pattern detector.

Detects A-B-C-C'-B'-A' mirror structures in scripture passages.

The approach:
1. For a given passage (list of verses), extract key words/phrases
2. Look for mirrored sequences at distance
3. Score the detected chiasms based on symmetry quality
"""

import re


def normalize_words(text):
    """Normalize text into lowercase words, removing punctuation."""
    return re.findall(r"[a-zA-Z\u0590-\u05FF']+", text.lower())


def extract_key_terms(text, stopwords=None):
    """Extract significant words from text, filtering common words."""
    stopwords = stopwords or {
        "and", "the", "a", "an", "in", "of", "to", "for", "with", "on",
        "at", "by", "from", "that", "this", "these", "those", "is", "was",
        "were", "be", "been", "are", "it", "its", "his", "her", "their",
        "our", "your", "my", "me", "we", "you", "they", "he", "she",
        "him", "them", "not", "no", "but", "or", "as", "all", "had",
        "has", "have", "do", "did", "does", "shall", "will", "would",
        "could", "should", "may", "might", "can", "every", "each",
        "there", "here", "then", "than", "also", "very", "unto",
        "upon", "into", "through", "after", "before",
        "ו", "ה", "ב", "ל", "כ", "מ", "א", "את", "על",
    }
    words = normalize_words(text)
    return [w for w in words if w not in stopwords and len(w) > 1]


def detect_internal_chiasm(verse_texts, min_matches=2, window_size=3):
    """Detect chiastic patterns within a sequence of verses.

    Looks for mirror patterns where words/phrases in an early verse
    are mirrored in a later verse.

    Returns list of detected chiasms with confidence scores.
    """
    if len(verse_texts) < 3:
        return []

    # Tokenize each verse into key terms
    tokenized = [extract_key_terms(v) for v in verse_texts]
    results = []

    n = len(tokenized)
    # Check each possible pair of positions (i, j) where i < j
    for i in range(n):
        for j in range(i + 2, n):
            # Check if outer pair (i, j) mirrors inner structure
            outer_i_terms = set(tokenized[i])
            outer_j_terms = set(tokenized[j])
            shared = outer_i_terms & outer_j_terms

            if len(shared) >= min_matches:
                # Content match at outer positions — check for mirroring
                # between (i+1, j-1), etc.
                inner_matches = 0
                for offset in range(1, min(j - i, window_size + 1)):
                    inner_i = i + offset
                    inner_j = j - offset
                    if inner_i >= inner_j:
                        break
                    if inner_i < n and inner_j < n and inner_i != inner_j:
                        inner_terms_i = set(tokenized[inner_i])
                        inner_terms_j = set(tokenized[inner_j])
                        inner_shared = inner_terms_i & inner_terms_j
                        if len(inner_shared) >= min_matches - 1:
                            inner_matches += 1

                # Score: more shared terms + more inner layers = stronger
                layers = min(j - i, window_size)
                score = (len(shared) / 5.0) * 0.6 + (inner_matches / layers) * 0.4
                score = min(score, 1.0)

                if score > 0.3:
                    results.append({
                        "type": "chiastic",
                        "start_index": i,
                        "end_index": j,
                        "shared_terms": list(shared),
                        "inner_matching_layers": inner_matches,
                        "confidence": round(score, 2),
                        "detected_by": "algorithm",
                    })

    return results


def detect_chiasm_in_book(verses, chapter=None):
    """Run chiastic detection on a set of verses.

    Args:
        verses: list of dicts with 'text_english' and optional 'chapter' keys
        chapter: specific chapter to analyze, or None for all
    """
    if chapter is not None:
        verses = [v for v in verses if v.get("chapter") == chapter]

    texts = [v.get("text_english", "") for v in verses if v.get("text_english")]
    if not texts:
        return []

    return detect_internal_chiasm(texts)
