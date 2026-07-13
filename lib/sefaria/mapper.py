"""Sefaria reference mapper — converts Sefaria references to engine verse IDs.

Sefaria uses formats like:
  - "Genesis 1:1" → gen.1.1
  - "Exodus 12:1-13" → exo.12.1 (range, take first)
  - "Rashi on Genesis 1:1:2" → gen.1.1 (strip commentator)
  - "Talmud Shabbat 1a" → (stored as metadata, not a verse ID)
  - "Zohar 1:1a" → (stored as metadata, book.zohar section)
  - "Bereshit Rabbah 1:1" → (stored as metadata, midrash reference)

Usage:
    from lib.sefaria.mapper import to_verse_id, link_type_to_engine
    verse_id = to_verse_id("Genesis 1:1")  # Returns "gen.1.1"
"""

import re

# ── Book name mapping: Sefaria → engine ──
SEFARIA_TO_ENGINE = {
    # Torah
    "Genesis": "gen", "Exodus": "exo", "Leviticus": "lev", "Numbers": "num", "Deuteronomy": "deu",
    # Historical books
    "Joshua": "josh", "Judges": "judg", "Ruth": "ruth",
    "I Samuel": "1sam", "II Samuel": "2sam", "1 Samuel": "1sam", "2 Samuel": "2sam",
    "I Kings": "1kgs", "II Kings": "2kgs", "1 Kings": "1kgs", "2 Kings": "2kgs",
    "I Chronicles": "1chr", "II Chronicles": "2chr", "1 Chronicles": "1chr", "2 Chronicles": "2chr",
    "Ezra": "ezra", "Nehemiah": "neh", "Esther": "esth",
    # Poetry/Wisdom
    "Job": "job", "Psalms": "psa", "Psalm": "psa", "Proverbs": "prov", "Ecclesiastes": "eccl",
    "Song of Songs": "song", "Canticles": "song",
    # Major Prophets
    "Isaiah": "isa", "Jeremiah": "jer", "Lamentations": "lam", "Ezekiel": "ezek", "Daniel": "dan",
    # Minor Prophets
    "Hosea": "hos", "Joel": "joel", "Amos": "amos", "Obadiah": "obad", "Jonah": "jonah",
    "Micah": "mic", "Nahum": "nah", "Habakkuk": "hab", "Zephaniah": "zeph",
    "Haggai": "hag", "Zechariah": "zech", "Malachi": "mal",
    # New Testament
    "Matthew": "matt", "Mark": "mark", "Luke": "luke", "John": "john",
    "Acts": "acts", "Romans": "rom",
    "I Corinthians": "1cor", "II Corinthians": "2cor", "1 Corinthians": "1cor", "2 Corinthians": "2cor",
    "Galatians": "gal", "Ephesians": "eph", "Philippians": "phil", "Colossians": "col",
    "I Thessalonians": "1thes", "II Thessalonians": "2thes", "1 Thessalonians": "1thes", "2 Thessalonians": "2thes",
    "I Timothy": "1tim", "II Timothy": "2tim", "1 Timothy": "1tim", "2 Timothy": "2tim",
    "Titus": "titus", "Philemon": "philem",
    "Hebrews": "heb", "James": "james",
    "I Peter": "1pet", "II Peter": "2pet", "1 Peter": "1pet", "2 Peter": "2pet",
    "I John": "1john", "II John": "2john", "III John": "3john", "1 John": "1john", "2 John": "2john", "3 John": "3john",
    "Jude": "jude", "Revelation": "rev",
    # Book of Mormon
    "1 Nephi": "1ne", "2 Nephi": "2ne", "Jacob": "jacob", "Enos": "enos",
    "Jarom": "jarom", "Omni": "omni", "Words of Mormon": "wom",
    "Mosiah": "mosiah", "Alma": "alma", "Helaman": "hel",
    "3 Nephi": "3ne", "4 Nephi": "4ne", "Mormon": "morm", "Ether": "ether", "Moroni": "moro",
    # PGP
    "Moses": "moses", "Abraham": "abraham",
}

# Sefaria link types → engine connection types
LINK_TYPE_MAP = {
    "commentary": "rabbinic_midrash",
    "midrash": "midrash_rabbah",
    "quotation": "talmud_quotation",
    "reference": "scriptural_reference",
    "ein_mishpat": "rabbinic_law_ref",
    "mesorat_hasas": "talmud_cross_ref",
    "related": "thematic_reference",
}

# Commentator prefixes to strip (Sefaria refs like "Rashi on Genesis 1:1:2")
COMMENTATOR_PREFIXES = [
    "Rashi on ", "Ramban on ", "Ibn Ezra on ", "Rashbam on ",
    "Sforno on ", "Radak on ", "Ralbag on ", "Metzudat David on ",
    "Metzudat Tzion on ", "Malbim on ", "Targum Onkelos on ",
    "Targum Jonathan on ", "Targum Pseudo-Jonathan on ",
    "Rambam on ", "Baal HaTurim on ", "Kli Yakar on ",
    "Ohr HaChayim on ", "Kitzur Baal HaTurim on ",
]

# Sefaria section identifiers that are NOT verse refs
NON_VERSE_REF_PREFIXES = [
    "Talmud ", "Mishnah ", "Tosefta ", "Zohar ", "Midrash ",
    "Bereshit Rabbah", "Shemot Rabbah", "Vayikra Rabbah",
    "Bamidbar Rabbah", "Devarim Rabbah", "Shir HaShirim Rabbah",
    "Rut Rabbah", "Eichah Rabbah", "Kohelet Rabbah",
    "Pesikta", "Mekhilta", "Sifra", "Sifrei",
    "Targum ", "Rashi ", "Rambam ", "Maimonides ",
    "Shulchan Aruch", "Tur ", "Mishneh Torah",
    "Sefer Yetzirah", "Bahir",
]


def is_tanakh_ref(ref):
    """Check if a Sefaria reference is a Tanakh (OT) verse."""
    for prefix in NON_VERSE_REF_PREFIXES:
        if ref.startswith(prefix):
            return False
    # If it matches book.chapter:verse pattern, it's likely Tanakh/NT
    return any(ref.startswith(book) or ref.startswith(f"{book} ") for book in SEFARIA_TO_ENGINE)


def strip_commentator(ref):
    """Strip commentator prefix from a reference like 'Rashi on Genesis 1:1:2'."""
    for prefix in COMMENTATOR_PREFIXES:
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
            break
    return ref


def parse_ref(ref):
    """Parse a Sefaria reference into components.

    Returns dict with:
      - type: "tanakh" | "talmud" | "midrash" | "zohar" | "commentary" | "other"
      - book: book name
      - chapter: chapter number
      - verse: verse number
      - raw: original reference
      - is_range: True if the ref covers multiple verses
    """
    result = {"raw": ref, "type": "other", "book": "", "chapter": 0, "verse": 0, "is_range": False}

    stripped = strip_commentator(ref)

    # Check for non-Tanakh refs
    for prefix in NON_VERSE_REF_PREFIXES:
        if stripped.startswith(prefix):
            result["type"] = "other"
            result["book"] = stripped
            return result

    # Try to parse as "Book Chapter:Verse" or "Book Chapter:Verse-Verse"
    # Also handle "Book Chapter:Verse:Word" (commentary granularity)
    for book in sorted(SEFARIA_TO_ENGINE, key=len, reverse=True):
        pattern = re.compile(
            rf'^{re.escape(book)}\s+(\d+):(\d+)', re.IGNORECASE
        )
        m = pattern.match(stripped)
        if m:
            result["type"] = "tanakh"
            result["book"] = book
            result["chapter"] = int(m.group(1))
            result["verse"] = int(m.group(2))
            # Check for range
            if "-" in stripped:
                result["is_range"] = True
            return result

    return result


def to_verse_id(ref):
    """Convert a Sefaria reference to an engine verse ID.

    Returns:
        str: engine verse ID (e.g., "gen.1.1") or None if not mappable
    """
    parsed = parse_ref(ref)
    if parsed["type"] != "tanakh":
        return None

    book_id = SEFARIA_TO_ENGINE.get(parsed["book"])
    if not book_id:
        return None

    return f"{book_id}.{parsed['chapter']}.{parsed['verse']}"


def link_type_to_engine(sefaria_type, auto=True):
    """Map a Sefaria link type to an engine connection type.

    Args:
        sefaria_type: string from Sefaria link data
        auto: whether the link was auto-generated by Sefaria

    Returns:
        engine connection type string
    """
    engine_type = LINK_TYPE_MAP.get(sefaria_type, "rabbinic_midrash")

    # Auto-generated links are lower confidence
    if auto and engine_type == "rabbinic_midrash":
        return "scriptural_reference"  # auto = less specific

    return engine_type


def link_type_confidence(sefaria_type, auto=True):
    """Return confidence score for a link based on type."""
    base = {
        "commentary": 0.85,
        "midrash": 0.75,
        "quotation": 0.95,
        "reference": 0.6,
        "ein_mishpat": 0.9,
        "mesorat_hasas": 0.9,
        "related": 0.4,
    }.get(sefaria_type, 0.5)

    if auto:
        base *= 0.8  # Auto-generated links get 20% confidence reduction

    return base
