"""
Gematria calculation engine.

Computes multiple gematria systems for Hebrew text:
  - Standard (Mispar Hechrachi):  א=1, ב=2, ... כ=20, ... ת=400
  - Ordinal (Mispar Siduri):      א=1, ב=2, ... ת=22
  - Reduced (Mispar Katan):       digit sum, then reduce to single digit
  - Gadol (Mispar Gadol):         includes final forms (ך=500, ם=600, ן=700, ף=800, ץ=900)
"""

import re
from functools import lru_cache

# === Hebrew letter → numerical value maps ===

# Standard gematria (Mispar Hechrachi)
STANDARD_MAP = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ך": 20, "ל": 30, "מ": 40, "ם": 40, "נ": 50, "ן": 50,
    "ס": 60, "ע": 70, "פ": 80, "ף": 80, "צ": 90, "ץ": 90, "ק": 100,
    "ר": 200, "ש": 300, "ת": 400,
}

# Ordinal gematria (Mispar Siduri) — letter position in alphabet
ORDINAL_MAP = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 11, "ך": 11, "ל": 12, "מ": 13, "ם": 13, "נ": 14, "ן": 14,
    "ס": 15, "ע": 16, "פ": 17, "ף": 17, "צ": 18, "ץ": 18, "ק": 19,
    "ר": 20, "ש": 21, "ת": 22,
}

# Mispar Gadol — includes final forms with extended values
GADOL_MAP = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ך": 500, "ל": 30, "מ": 40, "ם": 600, "נ": 50,
    "ן": 700, "ס": 60, "ע": 70, "פ": 80, "ף": 800, "צ": 90, "ץ": 900,
    "ק": 100, "ר": 200, "ש": 300, "ת": 400,
}

# Divine names and their standard gematria values
DIVINE_NAMES = [
    {"name": "YHWH", "hebrew": "יהוה", "value_standard": 26, "value_ordinal": 10, "value_reduced": 8, "category": "name"},
    {"name": "Elohim", "hebrew": "אלהים", "value_standard": 86, "value_ordinal": 14, "value_reduced": 5, "category": "name"},
    {"name": "Adonai", "hebrew": "אדני", "value_standard": 65, "value_ordinal": 14, "value_reduced": 2, "category": "name"},
    {"name": "El Shaddai", "hebrew": "אל שדי", "value_standard": 345, "value_ordinal": 21, "value_reduced": 3, "category": "title"},
    {"name": "El", "hebrew": "אל", "value_standard": 31, "value_ordinal": 4, "value_reduced": 4, "category": "name"},
    {"name": "Eloah", "hebrew": "אלוה", "value_standard": 42, "value_ordinal": 12, "value_reduced": 6, "category": "name"},
    {"name": "Eheyeh", "hebrew": "אהיה", "value_standard": 21, "value_ordinal": 9, "value_reduced": 3, "category": "name"},
    {"name": "YHWH Tsevaot", "hebrew": "יהוה צבאות", "value_standard": 98, "value_ordinal": 26, "value_reduced": 8, "category": "title"},
    {"name": "Shaddai", "hebrew": "שדי", "value_standard": 314, "value_ordinal": 17, "value_reduced": 8, "category": "name"},
    {"name": "El Elyon", "hebrew": "אל עליון", "value_standard": 166, "value_ordinal": 25, "value_reduced": 4, "category": "title"},
    {"name": "El Olam", "hebrew": "אל עולם", "value_standard": 187, "value_ordinal": 25, "value_reduced": 7, "category": "title"},
    {"name": "YHWH Yireh", "hebrew": "יהוה יראה", "value_standard": 316, "value_ordinal": 32, "value_reduced": 10, "category": "title"},
    {"name": "YHWH Shalom", "hebrew": "יהוה שלום", "value_standard": 376, "value_ordinal": 31, "value_reduced": 7, "category": "title"},
    {"name": "YHWH Tsidkenu", "hebrew": "יהוה צדקנו", "value_standard": 201, "value_ordinal": 36, "value_reduced": 3, "category": "title"},
    {"name": "Kadosh Israel", "hebrew": "קדוש ישראל", "value_standard": 557, "value_ordinal": 38, "value_reduced": 8, "category": "title"},
    {"name": "Mashiach", "hebrew": "משיח", "value_standard": 358, "value_ordinal": 25, "value_reduced": 7, "category": "title"},
    {"name": "Yeshua", "hebrew": "ישוע", "value_standard": 386, "value_ordinal": 17, "value_reduced": 8, "category": "name"},
    {"name": "Shekinah", "hebrew": "שכינה", "value_standard": 385, "value_ordinal": 22, "value_reduced": 7, "category": "title"},
]


# Compile Hebrew character detection
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


def is_hebrew_char(ch):
    """Check if a character is a Hebrew letter."""
    return HEBREW_RE.match(ch) is not None


def strip_cantillation(text):
    """Remove cantillation marks and other non-letter diacritics from Hebrew text.

    Preserves consonants and vowel points but removes:
    - Cantillation marks (ta'amei ha'mikra): ֑ ֒ ֓ ֔ ֕ ֖ ֗ ֘ ֙ ֚ ֛ ֜ ֝ ֞ ֟ ֠ ֡ ֢ ֣ ֤ ֥ ֦ ֧ ֨ ֩
    - Meteg: ֽ
    - Maqaf: ׀ (word hyphen)
    """
    # Remove everything that's not a Hebrew letter, vowel point, or dagesh
    # Keep consonants, vowels (niqqud), dagesh, shin/sin dot, rafe
    result = []
    for ch in text:
        cp = ord(ch)
        # Keep Hebrew letters (consonants + final forms)
        if 0x05D0 <= cp <= 0x05EA or 0x05EF <= cp <= 0x05F2:
            result.append(ch)
        # Keep vowel points, dagesh, shin/sin dot, rafe
        elif 0x05B0 <= cp <= 0x05C7:
            result.append(ch)
        # Skip everything else (cantillation marks, meteg, maqaf, etc.)
        else:
            continue
    return "".join(result)


def extract_consonants(text):
    """Extract only consonants from Hebrew text (remove vowels, cantillation)."""
    result = []
    for ch in text:
        cp = ord(ch)
        if 0x05D0 <= cp <= 0x05EA or 0x05EF <= cp <= 0x05F2:
            result.append(ch)
    return "".join(result)


def compute_standard(word):
    """Compute standard gematria (Mispar Hechrachi) for a Hebrew word."""
    total = 0
    for ch in extract_consonants(word):
        total += STANDARD_MAP.get(ch, 0)
    return total


def compute_ordinal(word):
    """Compute ordinal gematria (Mispar Siduri) for a Hebrew word."""
    total = 0
    for ch in extract_consonants(word):
        total += ORDINAL_MAP.get(ch, 0)
    return total


def compute_reduced(word):
    """Compute reduced gematria (Mispar Katan) — reduce to single digit."""
    val = compute_standard(word)
    while val > 9:
        val = sum(int(d) for d in str(val))
    return val


def compute_gadol(word):
    """Compute Mispar Gadol (includes final forms with extended values)."""
    total = 0
    for ch in extract_consonants(word):
        total += GADOL_MAP.get(ch, 0)
    return total


def compute_all(word):
    """Compute all gematria values for a word."""
    cons = extract_consonants(word)
    if not cons:
        return {"standard": 0, "ordinal": 0, "reduced": 0, "mispar_gadol": 0}
    return {
        "standard": compute_standard(cons),
        "ordinal": compute_ordinal(cons),
        "reduced": compute_reduced(cons),
        "mispar_gadol": compute_gadol(cons),
    }


@lru_cache(maxsize=10000)
def compute_all_cached(word):
    """Cached version of compute_all."""
    return compute_all(word)


def find_divine_name_matches(value, system="standard"):
    """Find which divine names match a given value."""
    key = f"value_{system}"
    if system == "standard":
        key = "value_standard"
    elif system == "ordinal":
        key = "value_ordinal"
    elif system == "reduced":
        key = "value_reduced"
    matches = []
    for d in DIVINE_NAMES:
        if d.get(key, 0) == value:
            matches.append(d)
    return matches


def is_sacred_number(value):
    """Check if a number is a known sacred/pattern number."""
    sacred = {1, 3, 4, 7, 10, 12, 24, 30, 40, 50, 70, 100, 120, 400, 1000}
    return value in sacred


def compute_verse_gematria(verse_words):
    """Compute total gematria for a verse (list of Hebrew words)."""
    total_std = 0
    total_ord = 0
    total_red = 0
    for word in verse_words:
        v = compute_all(word)
        total_std += v["standard"]
        total_ord += v["ordinal"]
        total_red += v["reduced"]
    return {"standard": total_std, "ordinal": total_ord, "reduced": total_red}


def get_divine_names_table():
    """Get the full divine names reference table."""
    return DIVINE_NAMES


# Special sacred connections data
SACRED_NUMBERS = {
    26: "Value of the divine name YHWH (יהוה)",
    86: "Value of Elohim (אלהים) — God",
    65: "Value of Adonai (אדני) — Lord",
    345: "Value of El Shaddai (אל שדי) — God Almighty",
    358: "Value of Mashiach (משיח) — Messiah",
    386: "Value of Yeshua (ישוע) — Jesus/Salvation",
    7: "Number of divine perfection/rest (7 days of creation)",
    12: "Number of divine government (12 tribes, 12 apostles)",
    40: "Number of testing/preparation (40 days/years)",
    70: "Number of the nations/elders",
    10: "Number of divine order (10 commandments)",
    613: "Number of mitzvot (commandments) in Torah",
    777: "Perfection of perfection (divine fullness)",
}

# Mispar Katan approaches
def mispar_katan_method(value):
    """Sum digits repeatedly until single digit."""
    while value > 9:
        value = sum(int(d) for d in str(value))
    return value


def mispar_katan_mispar(value):
    """Mispar Katan — remove hundreds digits (just take the tens and ones)."""
    if value >= 100:
        # Remove hundreds digit(s), keep tens and ones
        return value % 100 if value % 100 != 0 else (value % 1000) // 10
    return value
