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
        if 0x05D0 <= cp <= 0x05EA or 0x05EF <= cp <= 0x05F2 or 0x05B0 <= cp <= 0x05C7:
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

# ─── Kabbalistic Gematria Systems ───

# Milui/Mispar Shemi — spell out each letter's full name and sum those values
# These are the traditional letter name spellings
LETTER_NAMES = {
    "א": "אלף",    # Aleph = 111
    "ב": "בית",    # Bet = 412
    "ג": "גימל",   # Gimel = 53 (or 83 with yod)
    "ד": "דלת",    # Dalet = 434
    "ה": "הא",     # He = 6
    "ו": "וו",     # Vav = 12
    "ז": "זין",    # Zayin = 67
    "ח": "חית",    # Chet = 418
    "ט": "טית",    # Tet = 419
    "י": "יוד",    # Yod = 20
    "כ": "כף",     # Kaf = 100
    "ך": "כף",     # Kaf final = 100
    "ל": "למד",    # Lamed = 74
    "מ": "מם",     # Mem = 80
    "ם": "מם",     # Mem final = 80
    "נ": "נון",    # Nun = 106
    "ן": "נון",    # Nun final = 106
    "ס": "סמך",    # Samekh = 120
    "ע": "עין",    # Ayin = 130
    "פ": "פא",     # Pe = 81
    "ף": "פא",     # Pe final = 81
    "צ": "צדי",    # Tzadi = 104
    "ץ": "צדי",    # Tzadi final = 104
    "ק": "קוף",    # Qof = 186
    "ר": "ריש",    # Resh = 510
    "ש": "שין",    # Shin = 360
    "ת": "תו",     # Tav = 406
}


def compute_milui(word):
    """Mispar Milui/Shemi — spell out each letter name and sum.

    For each letter, look up its full name spelling, compute the standard
    gematria of that spelling, and sum them.
    """
    cons = extract_consonants(word)
    total = 0
    for ch in cons:
        name = LETTER_NAMES.get(ch, "")
        if name:
            total += compute_standard(name)
    return total


def compute_kellali(word):
    """Mispar HaKellali — standard value + number of letters.

    This gives weight to the count of letters as well as their values.
    """
    cons = extract_consonants(word)
    std = compute_standard(cons)
    return std + len(cons)


def compute_kidmi(word):
    """Mispar Kidmi — triangular numbers.

    For each letter with value n, add the sum of 1+2+...+n instead of n.
    For example, if aleph=1, kidmi_aleph = 1. If bet=2, kidmi_bet = 1+2 = 3.
    """
    cons = extract_consonants(word)
    total = 0
    for ch in cons:
        val = STANDARD_MAP.get(ch, 0)
        # Triangular number: n(n+1)/2
        total += (val * (val + 1)) // 2
    return total


def compute_boneh(word):
    """Mispar Boneh — standard + ordinal.

    Building number — adds the two simplest systems together.
    """
    cons = extract_consonants(word)
    return compute_standard(cons) + compute_ordinal(cons)


def compute_all(word):
    """Compute all gematria values for a word, including kabbalistic systems."""
    cons = extract_consonants(word)
    if not cons:
        return {
            "standard": 0, "ordinal": 0, "reduced": 0, "mispar_gadol": 0,
            "milui": 0, "kellali": 0, "kidmi": 0, "boneh": 0,
        }
    std = compute_standard(cons)
    return {
        "standard": std,
        "ordinal": compute_ordinal(cons),
        "reduced": compute_reduced(cons),
        "mispar_gadol": compute_gadol(cons),
        "milui": compute_milui(cons),
        "kellali": compute_kellali(cons),
        "kidmi": compute_kidmi(cons),
        "boneh": compute_boneh(cons),
    }
