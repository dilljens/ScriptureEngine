"""Advanced gematria — hidden numerical patterns beyond word-level.

Detects patterns in:
  - Substring gematria: gematria of letter-substrings within words
  - Skip-letter gematria: every other letter, every 3rd letter, etc.
  - First/last letter gematria per verse
  - Letter-count gematria: total letters in a verse
"""

from ..gematria import extract_consonants, compute_standard


def substring_gematria(word, start=0, length=None):
    """Compute gematria of a substring of a Hebrew word."""
    cons = extract_consonants(word)
    if start >= len(cons):
        return {"value": 0, "substring": ""}
    sub = cons[start:length]
    return {"value": compute_standard(sub), "substring": sub}


def skip_letter_gematria(word, skip=2):
    """Compute gematria of every Nth letter.
    
    skip=2: take letters 0, 2, 4, 6...
    skip=3: take letters 0, 3, 6, 9...
    """
    cons = extract_consonants(word)
    selected = cons[::skip]
    return {"value": compute_standard(selected), "selected": selected, "skip": skip}


def first_letter_gematria(words):
    """Compute gematria of the first letter of each word.
    
    This is a common pattern — the first letters of a verse
    sometimes form a word with meaningful gematria.
    """
    total = 0
    first_letters = []
    for w in words:
        cons = extract_consonants(w)
        if cons:
            first_letters.append(cons[0])
            total += compute_standard(cons[0])
    return {
        "total": total,
        "first_letters": "".join(first_letters),
        "standard": compute_standard("".join(first_letters)),
    }


def last_letter_gematria(words):
    """Compute gematria of the last letter of each word."""
    total = 0
    last_letters = []
    for w in words:
        cons = extract_consonants(w)
        if cons:
            last_letters.append(cons[-1])
            total += compute_standard(cons[-1])
    return {
        "total": total,
        "last_letters": "".join(last_letters),
        "standard": compute_standard("".join(last_letters)),
    }


def analyze_verse_gematria(hebrew_text):
    """Comprehensive gematria analysis of a verse.
    
    Returns all hidden numerical patterns found.
    """
    words = hebrew_text.split()
    cons_words = [extract_consonants(w) for w in words if extract_consonants(w)]
    
    patterns = []
    
    # Total letters in verse
    total_letters = sum(len(w) for w in cons_words)
    patterns.append({
        "type": "total_letters",
        "value": total_letters,
        "note": f"Total consonants in verse: {total_letters}",
    })
    
    # Word count
    word_count = len(cons_words)
    patterns.append({
        "type": "word_count",
        "value": word_count,
        "note": f"Words in verse: {word_count}",
    })
    
    # First letter gematria
    fl = first_letter_gematria(words)
    patterns.append({
        "type": "first_letter_gematria",
        "value": fl["total"],
        "note": f"First letter gematria: {fl['total']} ({fl['first_letters']})",
    })
    
    # Last letter gematria
    ll = last_letter_gematria(words)
    patterns.append({
        "type": "last_letter_gematria",
        "value": ll["total"],
        "note": f"Last letter gematria: {ll['total']} ({ll['last_letters']})",
    })
    
    # Check if word count is a sacred number
    from ..gematria import is_sacred_number
    if is_sacred_number(word_count):
        patterns.append({
            "type": "sacred_word_count",
            "value": word_count,
            "note": f"{word_count} is a sacred number",
        })
    
    # Check if letter count is a sacred number
    if is_sacred_number(total_letters):
        patterns.append({
            "type": "sacred_letter_count",
            "value": total_letters,
            "note": f"{total_letters} is a sacred number",
        })
    
    return patterns
