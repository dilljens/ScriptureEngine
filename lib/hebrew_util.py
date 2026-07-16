"""
Hebrew text utilities — transliteration, accent stripping, RTL-safe output.

Uses `biblical-transliteration` (MIT, zero deps) as the transliteration engine
for correct SBL-style output with qamats qatan detection, vocal/silent shewa
distinction, full begadkefat, and Tetragrammaton avoidance.

Three improvements for terminal/plaintext display:

1. **strip_cantillation(text)** — remove trope marks (accents) for cleaner reading
2. **transliterate(text)** — scholarly SBL transliteration via biblical-transliteration
3. **rtl_mark(text)** — wraps text with Unicode RTL markers for correct rendering
"""

import re
import unicodedata

from biblical_transliteration import HebrewOptions, HebrewScheme, HebrewTransliterator

# ── Shared engines ─────────────────────────────────────────────
# Three schemes for different contexts:
#   SBL    — academic (bǝrēʾšîṯ) — diacritics, reversible
#   SIMPLE — readable ASCII (bereshit) — no diacritics, typable
#   PHONETIC — pronunciation (be-re-SHEET) — syllable stress
_HEB_SBL = HebrewTransliterator(
    HebrewOptions(scheme=HebrewScheme.SBL)
)
_HEB_SIMPLE = HebrewTransliterator(
    HebrewOptions(scheme=HebrewScheme.SIMPLE)
)
_HEB_PHONETIC = HebrewTransliterator(
    HebrewOptions(scheme=HebrewScheme.PHONETIC)
)

# Default transliteration scheme for vocabulary display
TR_SCHEME_DEFAULT = "simple"

# Map scheme names to engines
_SCHEMES = {
    "sbl": _HEB_SBL,
    "simple": _HEB_SIMPLE,
    "phonetic": _HEB_PHONETIC,
}

# ── Unicode ranges (for accent stripping) ────────────────────
CANTILLATION = set(range(0x0591, 0x05A2)) | {0x05A3, 0x05A4, 0x05A5, 0x05A6, 0x05A7, 0x05A8, 0x05A9, 0x05AA, 0x05AB, 0x05AC, 0x05AD, 0x05AE, 0x05AF}
# Everything between 0x0591-0x05AF is accents/cantillation
CANTILLATION_RANGE = range(0x0591, 0x05B0)
PUNCTUATION_HEB = {0x05C0, 0x05C3, 0x05C6, 0x05F3, 0x05F4}

# RTL marker
RLM = "\u200F"  # RIGHT-TO-LEFT MARK
LRM = "\u200E"  # LEFT-TO-RIGHT MARK

# ── Functions ──────────────────────────────────────────────────

def strip_cantillation(text):
    """Remove cantillation/trope marks for cleaner reading.

    Keeps vowel points, dagesh, shin/sin dots — removes only accents.
    """
    return "".join(c for c in text if unicodedata.category(c) != "Mn"
                   or ord(c) not in CANTILLATION_RANGE)


def strip_vowels(text):
    """Remove all vowel pointing and accents — leaves bare consonants."""
    # Remove combining marks in Hebrew ranges (vowels + accents + dagesh)
    return "".join(
        c for c in text
        if unicodedata.category(c) != "Mn"
        and ord(c) not in {0x05C1, 0x05C2}  # keep shin/sin dots
    )


def clean_hebrew(text):
    """Clean up the database format: remove slashes, collapse whitespace."""
    text = text.replace("/", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def transliterate(text, scheme="sbl"):
    """Convert pointed Hebrew text to transliteration in the chosen scheme.

    Uses `biblical-transliteration` (MIT) for correct handling of:
    - Qamats qatan vs gadol
    - Vocal vs silent shewa
    - Full begadkefat spirantization (SBL only)
    - Tetragrammaton avoidance (yhwh, not yəhwāh)
    - Mater lectionis, dagesh forte, shin/sin dots

    Args:
        text: Hebrew text (possibly with / separators from DB, cantillation, vowels)
        scheme: 'sbl' (academic, default), 'simple' (ASCII), or 'phonetic'

    Returns:
        Transliteration string (left-to-right)
    """
    if not text:
        return ""

    text = clean_hebrew(text)
    engine = _SCHEMES.get(scheme, _HEB_SBL)
    return engine.transliterate(text)


def rtl_mark(text):
    """Wrap text with Unicode RTL markers for correct terminal display.

    Use for any Hebrew text embedded in LTR output.
    """
    return f"{RLM}{text}{RLM}"


def ltr_mark(text):
    """Wrap plain text with LTR markers to reset direction."""
    return f"{LRM}{text}{LRM}"


def display_verse(text_hebrew, translit=None, fmt="text"):
    """Format Hebrew text for display, with optional transliteration.

    Args:
        text_hebrew: Hebrew text (possibly raw from DB with slashes)
        translit: Pre-computed transliteration (or None to compute)

    Returns:
        Formatted string safe for terminal/plaintext display
    """
    if not text_hebrew:
        return ""

    clean = clean_hebrew(text_hebrew)
    bare = strip_cantillation(clean)
    if translit is None:
        translit = transliterate(clean)

    return f"{rtl_mark(bare)} [{translit}]"
