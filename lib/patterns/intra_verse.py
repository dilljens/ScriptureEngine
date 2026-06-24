"""Intra-verse parallelism detection — detects parallelism between
poetic lines within a single verse.

Uses the existing classify_parallelism() from lib.patterns.parallelism
but with adjusted thresholds for shorter poetic lines.
"""

import re
from lib.patterns.parallelism import (
    classify_parallelism,
    tokenize,
    word_overlap,
    ANTITHETIC_MARKERS,
    SYNTHETIC_MARKERS,
)
from lib.poetry.line_split import split_verse

STOP_WORDS = {
    "and", "the", "a", "an", "in", "of", "to", "for", "with", "on",
    "at", "by", "from", "that", "this", "these", "those", "is", "was",
    "were", "be", "been", "are", "it", "its", "his", "her", "their",
    "our", "your", "my", "me", "we", "you", "they", "he", "she",
    "him", "them", "not", "no", "but", "or", "as", "all", "had",
    "has", "have", "do", "did", "does", "shall", "will", "would",
    "could", "should", "may", "might", "can", "every", "each",
    "there", "here", "then", "than", "also", "very", "unto",
}

PARALLEL_IMPERATIVES = {
    "seek", "call", "hear", "hearken", "go", "come", "make", "let",
    "take", "give", "bring", "cast", "put", "set", "turn", "lift",
    "raise", "praise", "sing", "shout", "tell", "declare", "prepare",
    "remember", "forget", "fear", "trust", "wait", "look", "see",
    "behold", "arise", "awake", "stand", "know", "consider", "think",
    "keep", "observe", "love", "hate", "choose", "follow",
}


def _content_words(text):
    """Extract meaningful content words (non-stop-words, length > 2)."""
    tokens = tokenize(text)
    return {w for w in tokens if w not in STOP_WORDS and len(w) > 2}


def _detect_imperative_parallelism(text_a, text_b):
    """Check if both lines start with imperatives — strong structural parallel."""
    a_first = tokenize(text_a)[0] if tokenize(text_a) else ""
    b_first = tokenize(text_b)[0] if tokenize(text_b) else ""
    if a_first in PARALLEL_IMPERATIVES and b_first in PARALLEL_IMPERATIVES:
        return True
    return False


def _detect_contrast_parallelism(text_a, text_b):
    """Check if lines have contrast markers — antithetic structure."""
    words_a = set(tokenize(text_a))
    words_b = set(tokenize(text_b))
    return bool(
        (words_a & ANTITHETIC_MARKERS) or (words_b & ANTITHETIC_MARKERS)
    )


def detect_intra_verse(verse_text_english, verse_text_hebrew):
    """Detect parallelism between lines within a verse.

    Args:
        verse_text_english: Full English text of the verse
        verse_text_hebrew: Full Hebrew text of the verse (can be empty)

    Returns:
        dict: {
            "lines": [...],
            "parallelisms": [{"type": str, "line_a": int, "line_b": int,
                              "confidence": float, "evidence": str}, ...]
        }
    """
    lines = split_verse(verse_text_english, verse_text_hebrew)

    result = {
        "lines": [{"english": l["english"], "hebrew": l["hebrew"], "index": i}
                  for i, l in enumerate(lines)],
        "parallelisms": [],
    }

    if len(lines) < 2:
        return result

    for i in range(len(lines) - 1):
        text_a = lines[i]["english"]
        text_b = lines[i + 1]["english"]

        # Try the standard classifier first
        ptype, confidence, evidence = classify_parallelism(text_a, text_b)

        # If the standard classifier didn't catch it, try intra-verse heuristics
        if not ptype or confidence < 0.3:
            content_a = _content_words(text_a)
            content_b = _content_words(text_b)

            # Check for synonymous parallelism via imperative pairs
            if _detect_imperative_parallelism(text_a, text_b):
                shared_content = content_a & content_b
                overlap_score = len(shared_content) / max(len(content_a | content_b), 1)
                conf = 0.4 + overlap_score * 0.3
                result["parallelisms"].append({
                    "type": "parallel_synonymous",
                    "line_a": i,
                    "line_b": i + 1,
                    "confidence": round(min(conf, 0.9), 2),
                    "evidence": "imperative_parallel",
                })
                continue

            # Check for antithetic via contrast markers
            if _detect_contrast_parallelism(text_a, text_b):
                shared_content = content_a & content_b
                overlap_score = len(shared_content) / max(len(content_a | content_b), 1)
                if overlap_score < 0.3:
                    result["parallelisms"].append({
                        "type": "parallel_antithetic",
                        "line_a": i,
                        "line_b": i + 1,
                        "confidence": round(0.5 + overlap_score * 0.2, 2),
                        "evidence": "contrast_markers",
                    })
                    continue

        # Use standard classifier result if valid
        if ptype and confidence > 0.25:
            result["parallelisms"].append({
                "type": ptype,
                "line_a": i,
                "line_b": i + 1,
                "confidence": round(confidence, 2),
                "evidence": evidence,
            })

    return result


def detect_intra_verse_batch(verses):
    """Run intra-verse detection on a batch of verse dicts.

    Args:
        verses: list of dicts with 'text_english' and optional 'text_hebrew' keys

    Returns:
        dict mapping verse index -> detect_intra_verse() result
    """
    return {
        i: detect_intra_verse(
            v.get("text_english", ""),
            v.get("text_hebrew", ""),
        )
        for i, v in enumerate(verses)
    }
