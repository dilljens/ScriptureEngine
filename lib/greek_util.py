"""
Greek text utilities — transliteration, accent stripping, display formatting.

SBL-style scholarly transliteration for polytonic Greek via biblical-transliteration.
"""

import re
import unicodedata

from biblical_transliteration import GreekOptions, GreekScheme, GreekTransliterator

# ── Shared engine ──────────────────────────────────────────────
_GRK_TRANSLITERATOR = GreekTransliterator(
    GreekOptions(scheme=GreekScheme.SBL)
)

# ── Combining marks (for accent stripping) ────────────────────
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

    Uses biblical-transliteration (MIT) for correct handling of diphthongs,
    gamma nasal, rough breathings, iota subscript, and diaeresis.

    Args:
        text: Polytonic Greek string.

    Returns:
        SBL-style transliteration string (accents stripped).
    """
    if not text:
        return ""

    text = clean_greek(text)
    return _GRK_TRANSLITERATOR.transliterate(text)


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
