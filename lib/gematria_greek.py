"""
Greek isopsephy calculation engine.

Computes numerical values for Greek text:
  - Standard: α=1, β=2, γ=3, ... ω=800 (standard isopsephy)
  - Ordinal:  α=1, β=2, γ=3, ... ω=24 (position in alphabet)
  - Reduced: digit sum of standard value
"""

import re
from functools import lru_cache

# Standard Greek isopsephy (α=1, β=2, ... ω=800)
STANDARD_MAP = {
    'α': 1, 'Α': 1,
    'β': 2, 'Β': 2,
    'γ': 3, 'Γ': 3,
    'δ': 4, 'Δ': 4,
    'ε': 5, 'Ε': 5,
    'ϛ': 6, 'Ϛ': 6,  # stigma (archaic)
    'ζ': 7, 'Ζ': 7,
    'η': 8, 'Η': 8,
    'θ': 9, 'Θ': 9,
    'ι': 10, 'Ι': 10,
    'κ': 20, 'Κ': 20,
    'λ': 30, 'Λ': 30,
    'μ': 40, 'Μ': 40,
    'ν': 50, 'Ν': 50,
    'ξ': 60, 'Ξ': 60,
    'ο': 70, 'Ο': 70,
    'π': 80, 'Π': 80,
    'ϟ': 90, 'Ϟ': 90,  # koppa (archaic)
    'ρ': 100, 'Ρ': 100,
    'σ': 200, 'Σ': 200,
    'τ': 300, 'Τ': 300,
    'υ': 400, 'Υ': 400,
    'φ': 500, 'Φ': 500,
    'χ': 600, 'Χ': 600,
    'ψ': 700, 'Ψ': 700,
    'ω': 800, 'Ω': 800,
    'ς': 200,  # final sigma
}

# Ordinal Greek (letter position: α=1, β=2, ... ω=24)
ORDINAL_MAP = {
    'α': 1, 'β': 2, 'γ': 3, 'δ': 4, 'ε': 5, 'ϛ': 6, 'ζ': 7, 'η': 8, 'θ': 9,
    'ι': 10, 'κ': 11, 'λ': 12, 'μ': 13, 'ν': 14, 'ξ': 15, 'ο': 16, 'π': 17,
    'ϟ': 18, 'ρ': 19, 'σ': 20, 'τ': 21, 'υ': 22, 'φ': 23, 'χ': 24, 'ψ': 25, 'ω': 26,
}

GREEK_LETTER_RE = re.compile(r'[\u0370-\u03FF\u1F00-\u1FFF]+')


def extract_greek_letters(word):
    """Extract only Greek base letters from a word.

    Uses Unicode NFD normalization to decompose accented characters
    into base letter + combining marks, then keeps only the base letters.
    This correctly handles all Greek accent and breathing mark combinations.
    """
    import unicodedata
    result = []
    # First decompose: e.g., Ἰ (U+1F38) → Ι (U+0399) +  ̓ (U+0313)
    nfd = unicodedata.normalize('NFD', word)
    for ch in nfd:
        cp = ord(ch)
        # Keep only characters in the Greek alphabet ranges
        # and the final sigma
        if 0x0370 <= cp <= 0x03FF:
            # But filter out combining diacritics (which also fall in this range)
            # Greek diacritics specific ranges that should be excluded
            if cp not in (0x0374, 0x0375, 0x037A, 0x037E):
                result.append(ch)
        # Also check for &sigmaf; (final sigma) which is already a base letter
        elif cp == 0x03C2:  # final sigma
            result.append(ch)
    return ''.join(result)


def compute_standard(word):
    """Compute standard Greek isopsephy."""
    letters = extract_greek_letters(word)
    total = 0
    for ch in letters:
        total += STANDARD_MAP.get(ch, 0)
    return total


def compute_ordinal(word):
    """Compute ordinal Greek isopsephy."""
    letters = extract_greek_letters(word)
    total = 0
    for ch in letters:
        total += ORDINAL_MAP.get(ch.lower(), 0)
    return total


def compute_reduced(value):
    """Reduce to single digit."""
    while value > 9:
        value = sum(int(d) for d in str(value))
    return value


def compute_all(word):
    """Compute all Greek isopsephy values for a word."""
    std = compute_standard(word)
    ord_val = compute_ordinal(word)
    red = compute_reduced(std)
    return {
        "standard": std,
        "ordinal": ord_val,
        "reduced": red,
    }


# Notable Greek isopsephy values
NOTABLE_GREEK_VALUES = {
    99: "Ἀμήν (Amen) — so be it",
    666: "χξϛ (the number of the beast, Rev 13:18)",
    888: "Ἰησοῦς (Jesus) — 888 is the number of Jesus",
    1485: "Χριστός (Christ) — 3× 495",
    2368: "Ἰησοῦς Χριστός (Jesus Christ) — 888+1480 (with variant)",
}

# Common NT words with their isopsephy (for quick reference)
COMMON_GREEK_ISOPSEPHY = {
    "Ἰησοῦς": 888,   # Jesus
    "Χριστός": 1480,  # Christ (or 1485 depending on spelling)
    "Κύριος": 800,    # Lord
    "Θεός": 284,      # God
    "Πνεῦμα": 576,    # Spirit
    "Ἀμήν": 99,       # Amen
    "Σωτήρ": 1408,    # Savior
    "Πίστις": 800,    # Faith
    "Ἀγάπη": 93,      # Love
    "Χάρις": 809,     # Grace
    "Ἀλήθεια": 64,    # Truth
    "Ζωή": 815,       # Life
    "Φῶς": 1500,      # Light
    "Λόγος": 373,     # Word
}
