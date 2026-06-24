"""
Greek text utilities — transliteration, accent stripping, display formatting.

SBL-style scholarly transliteration for polytonic Greek.
"""

import re
import unicodedata

# ── Combining marks ──────────────────────────────────────────────
SMOOTH = "\u0313"         # combining comma above
ROUGH = "\u0314"          # combining reversed comma above
ACUTE = "\u0301"          # combining acute accent
GRAVE = "\u0300"          # combining grave accent
CIRCUMFLEX = "\u0342"     # combining circumflex accent
IOTA_SUB = "\u0345"       # combining ypogegrammeni (iota subscript)
DIAERESIS = "\u0308"      # combining diaeresis

ACCENTS = frozenset({ACUTE, GRAVE, CIRCUMFLEX})
BREATHINGS = frozenset({SMOOTH, ROUGH})
STRIP_DIACRITICS = BREATHINGS | ACCENTS | {IOTA_SUB, DIAERESIS}
STRIP_ACCENTS = ACCENTS

HEL_TEXT = "Greek"

# ── Letter map ──────────────────────────────────────────────────
LETTER_MAP = {
    "α": "a",
    "β": "b",
    "γ": "g",
    "δ": "d",
    "ε": "e",
    "ζ": "z",
    "η": "ē",
    "θ": "th",
    "ι": "i",
    "κ": "k",
    "λ": "l",
    "μ": "m",
    "ν": "n",
    "ξ": "x",
    "ο": "o",
    "π": "p",
    "ρ": "r",
    "ς": "s",
    "σ": "s",
    "τ": "t",
    "υ": "y",
    "φ": "ph",
    "χ": "ch",
    "ψ": "ps",
    "ω": "ō",
}

# Uppercase equivalents
for k, v in list(LETTER_MAP.items()):
    LETTER_MAP[k.upper()] = v.upper()

# ── Diphthong table ─────────────────────────────────────────────
DIPHTHONGS = {
    ("α", "ι"): "ai",
    ("ε", "ι"): "ei",
    ("ο", "ι"): "oi",
    ("α", "υ"): "au",
    ("ε", "υ"): "eu",
    ("ο", "υ"): "ou",
    ("υ", "ι"): "ui",
    ("η", "υ"): "ēu",
    ("ω", "υ"): "ōu",
}

VOWELS = frozenset({"α", "ε", "η", "ι", "ο", "υ", "ω",
                     "Α", "Ε", "Η", "Ι", "Ο", "Υ", "Ω"})

# Gamma nasal: γ before γ/κ/ξ/χ → n
GAMMA_NASAL_FOLLOWING = frozenset({"γ", "κ", "ξ", "χ", "Γ", "Κ", "Ξ", "Χ"})

# Iota subscript → macron-vowel + i
IOTA_SUB_MAP = {
    "α": "āi",
    "η": "ēi",
    "ω": "ōi",
}


# ── Helper ──────────────────────────────────────────────────────

def _tokenize(text):
    """Break NFD-normalized text into (base_char, set_of_combining_marks) tokens."""
    chars = list(text)
    n = len(chars)
    tokens = []
    i = 0
    while i < n:
        cat = unicodedata.category(chars[i])
        if cat.startswith("M"):
            i += 1
            continue
        base = chars[i]
        i += 1
        combining = set()
        while i < n and unicodedata.category(chars[i]).startswith("M"):
            combining.add(chars[i])
            i += 1
        tokens.append((base, combining))
    return tokens


# ── Cleaning ────────────────────────────────────────────────────

def clean_greek(text):
    """Normalize whitespace — collapse runs, strip ends."""
    return re.sub(r"\s+", " ", text).strip()


def strip_diacritics(text):
    """Remove ALL diacritics: breathings, accents, iota subscript, diaeresis."""
    text = unicodedata.normalize("NFD", text)
    result = [
        c for c in text
        if not (unicodedata.category(c).startswith("M") and c in STRIP_DIACRITICS)
    ]
    return unicodedata.normalize("NFC", "".join(result))


def strip_accents(text):
    """Remove only accent marks — keep breathings, iota subscript, diaeresis."""
    text = unicodedata.normalize("NFD", text)
    result = [c for c in text if c not in ACCENTS]
    return unicodedata.normalize("NFC", "".join(result))


# ── Transliteration ─────────────────────────────────────────────

def transliterate(text):
    """Convert polytonic Greek text to SBL-style scholarly transliteration.

    Handles breathings, accents (stripped), iota subscript, diphthongs,
    gamma nasal, diaeresis, and rho with rough breathing.

    Args:
        text: Polytonic Greek string.

    Returns:
        SBL-style transliteration string (accents stripped).
    """
    if not text:
        return ""

    text = clean_greek(text)
    text = unicodedata.normalize("NFD", text)
    tokens = _tokenize(text)

    result = []
    i = 0
    m = len(tokens)

    while i < m:
        base, combining = tokens[i]
        has_rough = ROUGH in combining
        has_iota_sub = IOTA_SUB in combining
        has_diaeresis = DIAERESIS in combining
        is_upper = base.isupper()
        base_lower = base.lower()

        if base_lower not in LETTER_MAP:
            result.append(base)
            i += 1
            continue

        # ── Diphthong check (vowel + vowel, no diaeresis on either) ──
        if (
            base in VOWELS
            and not has_diaeresis
            and i + 1 < m
        ):
            nb, nc = tokens[i + 1]
            if nb in VOWELS and DIAERESIS not in nc:
                key = (base_lower, nb.lower())
                if key in DIPHTHONGS:
                    trans = DIPHTHONGS[key]
                    # Rough breathing on EITHER vowel → h prefix
                    if has_rough or ROUGH in nc:
                        trans = "h" + trans
                    if is_upper:
                        trans = trans[:1].upper() + trans[1:]
                    result.append(trans)
                    i += 2
                    continue

        # ── Iota subscript ──
        if has_iota_sub and base_lower in IOTA_SUB_MAP:
            trans = IOTA_SUB_MAP[base_lower]
        else:
            trans = LETTER_MAP[base_lower]

        # ── Rho with rough breathing → rh ──
        if base_lower == "ρ" and has_rough:
            trans = "rh"
        elif has_rough:
            trans = "h" + trans

        # ── Gamma nasal ──
        if base_lower == "γ" and i + 1 < m:
            if tokens[i + 1][0] in GAMMA_NASAL_FOLLOWING:
                trans = "n"

        # ── Diaeresis ──
        if has_diaeresis:
            if trans == "i":
                trans = "ï"
            elif trans == "y":
                trans = "ü"

        if is_upper and trans:
            trans = trans[:1].upper() + trans[1:]

        result.append(trans)
        i += 1

    return "".join(result)


# ── Display ─────────────────────────────────────────────────────

def display_verse(text_greek, translit=None):
    """Format Greek text for display, with optional transliteration.

    Args:
        text_greek: Greek text (possibly raw from DB with diacritics).
        translit: Pre-computed transliteration (or None to compute).

    Returns:
        Formatted "clean_text [translit]" string.
    """
    if not text_greek:
        return ""

    clean = clean_greek(text_greek)
    bare = strip_diacritics(clean)
    if translit is None:
        translit = transliterate(clean)

    return f"{bare} [{translit}]"
