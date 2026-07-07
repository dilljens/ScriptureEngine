"""Phrase Match generator — connects verses sharing significant multi-word phrases.

Finds 2-4 word Hebrew phrases that repeat across the canon using the gematria
table's word_hebrew field. Phrase-level connections capture meaningful theological
links that word-level generators miss (e.g., "son of man", "day of the Lord",
"holy one of Israel").

Works in two modes:
  1. Hebrew phrase matching (OT) — uses sequential word_hebrew from gematria table
  2. English phrase matching (NT, BoM, D&C) — uses text_english LIKE queries
"""

import re
from collections import defaultdict, Counter
from lib.db import add_connection

# ─── Key Hebrew Phrases (manually curated, high significance) ───
# Format: (english_name, hebrew_phrase_compact)
# hebrew_phrase_compact: search text with spaces removed (for matching)
KEY_PHRASES = [
    ("Son of Man", "בן אדם"),
    ("Son of God", "בן אלהים"),
    ("Sons of God", "בני אלהים"),
    ("Sons of Israel", "בני ישראל"),
    ("Holy One of Israel", "קדוש ישראל"),
    ("Day of the Lord", "יום יהוה"),
    ("Day of YHWH", "יום יהוה"),
    ("Thus Says the Lord", "כה אמר יהוה"),
    ("Thus Says YHWH", "כה אמר יהוה"),
    ("Word of the Lord", "דבר יהוה"),
    ("Word of YHWH", "דבר יהוה"),
    ("House of Israel", "בית ישראל"),
    ("House of Judah", "בית יהודה"),
    ("House of the Lord", "בית יהוה"),
    ("House of YHWH", "בית יהוה"),
    ("House of God", "בית האלהים"),
    ("Covenant of the Lord", "ברית יהוה"),
    ("Ark of the Covenant", "ארון הברית"),
    ("Book of the Law", "ספר התורה"),
    ("Law of Moses", "תורת משה"),
    ("Law of the Lord", "תורת יהוה"),
    ("Servant of the Lord", "עבד יהוה"),
    ("Angel of the Lord", "מלאך יהוה"),
    ("Angel of YHWH", "מלאך יהוה"),
    ("Spirit of the Lord", "רוח יהוה"),
    ("Spirit of God", "רוח אלהים"),
    ("Glory of the Lord", "כבוד יהוה"),
    ("Glory of YHWH", "כבוד יהוה"),
    ("Hand of the Lord", "יד יהוה"),
    ("Fear of the Lord", "יראת יהוה"),
    ("Praise the Lord", "הללויה"),
    ("Hallelujah", "הללויה"),
    ("King of Israel", "מלך ישראל"),
    ("Land of Israel", "ארץ ישראל"),
    ("Land of Promise", "ארץ ההבטחה"),
    ("Promised Land", "ארץ ההבטחה"),
    ("Sons of Light", "בני אור"),
    ("Sons of Darkness", "בני חשך"),
    ("Prince of Light", "שר אור"),
    ("Angel of Darkness", "מלאך חשך"),
    ("Spirit of Truth", "רוח אמת"),
    ("Spirit of Holiness", "רוח קדש"),
    ("People of God", "עם אלהים"),
    ("City of David", "עיר דוד"),
    ("City of God", "עיר האלהים"),
    ("Mount Zion", "הר ציון"),
    ("Mount of God", "הר האלהים"),
    ("Mount Sinai", "הר סיני"),
    ("Mount of Olives", "הר הזיתים"),
    ("Tree of Life", "עץ החיים"),
    ("Tree of Knowledge", "עץ הדעת"),
    ("Garden of Eden", "גן עדן"),
    ("Living Water", "מים חיים"),
    ("Living Waters", "מים חיים"),
    ("Bread of Life", "לחם חיים"),
    ("People of the Book", "עם הספר"),
    ("New Covenant", "ברית חדשה"),
    ("Everlasting Covenant", "ברית עולם"),
    ("Book of Life", "ספר החיים"),
    ("Holy Place", "הקדש"),
    ("Holy of Holies", "קדש הקדשים"),
    ("Most Holy Place", "קדש הקדשים"),
    ("New Heavens and New Earth", "שמים חדשים וארץ חדשה"),
    ("New Jerusalem", "ירושלים חדשה"),
    ("Kingdom of God", "מלכות אלהים"),
    ("Kingdom of Heaven", "מלכות השמים"),
    ("End of Days", "אחרית הימים"),
    ("Last Days", "אחרית הימים"),
    ("Day of Wrath", "יום עברה"),
    ("Day of Vengeance", "יום נקם"),
    ("Year of the Lord", "שנת יהוה"),
    ("Fountain of Living Waters", "מקור מים חיים"),
    ("Everlasting Kindness", "חסד עולם"),
    ("Sure Mercies of David", "חסדי דוד"),
    ("Apple of His Eye", "אישון עין"),
    ("Chariot of Israel", "רכב ישראל"),
    ("Pillar of Cloud", "עמוד ענן"),
    ("Pillar of Fire", "עמוד אש"),
    ("Tables of the Covenant", "לוחות הברית"),
    ("Tent of Meeting", "אהל מועד"),
    ("Children of Israel", "בני ישראל"),
]

# ─── English key phrases (NT, BoM, D&C — no Hebrew) ───
ENGLISH_PHRASES = [
    "Son of Man",
    "Son of God",
    "Sons of God",
    "kingdom of God",
    "kingdom of heaven",
    "eternal life",
    "everlasting life",
    "new covenant",
    "new testament",
    "born of God",
    "born again",
    "born of the Spirit",
    "baptism of fire",
    "baptism of the Holy Ghost",
    "gift of the Holy Ghost",
    "day of judgment",
    "day of the Lord",
    "last days",
    "eternal judgment",
    "judgment seat",
    "resurrection of the dead",
    "resurrection of the just",
    "first resurrection",
    "second death",
    "lake of fire",
    "tree of life",
    "bread of life",
    "living water",
    "water of life",
    "light of the world",
    "way of truth",
    "perfect love",
    "everlasting covenant",
    "new Jerusalem",
    "holy city",
    "heavenly host",
    "ministering spirits",
    "powers of heaven",
    "signs of the times",
    "fulness of times",
    "dispensations",
    "marriage of the Lamb",
    "supper of the Lamb",
    "great white throne",
    "book of life",
    "Lamb of God",
    "only begotten",
    "corner stone",
    "chief corner stone",
    "strong delusion",
    "falling away",
    "man of sin",
    "son of perdition",
    "mystery of God",
    "mystery of iniquity",
    "fulness of the Gentiles",
    "times of the Gentiles",
    "priesthood after the order of Melchizedek",
    "high priest forever",
    "holy priesthood",
    "holy order",
    "minister of the sanctuary",
    "shadow of good things",
    "image of the beast",
    "mark of the beast",
    "everlasting gospel",
    "faith of Abraham",
    "children of the covenant",
    "children of light",
    "children of disobedience",
    "armor of God",
    "whole armor of God",
    "shield of faith",
    "sword of the Spirit",
    "helmet of salvation",
    "breastplate of righteousness",
    "fellowship of the Saints",
    "body of Christ",
    "members in particular",
    "spiritual gifts",
    "diversities of gifts",
    "fruit of the Spirit",
    "works of the flesh",
    "wrath to come",
    "saving faith",
    "justification by faith",
    "justified by faith",
    "faith without works is dead",
    "obedience of faith",
    "endure to the end",
    "endure unto the end",
    "joy of the saints",
    "peace of God",
    "peace which passeth understanding",
    "hope of salvation",
    "anchor of the soul",
    "more sure word of prophecy",
    "sure word of prophecy",
    "restitution of all things",
    "dispensation of the fulness of times",
    "gathering of Israel",
    "scattering of Israel",
    "new song",
    "everlasting punishment",
    "endless torment",
    "worm dieth not",
    "fire is not quenched",
    "outer darkness",
    "weeping and gnashing of teeth",
]


def _search_hebrew_phrase(conn, phrase_compact):
    """Find verses containing a Hebrew phrase (with flexible spacing)."""
    # Create a LIKE pattern that allows any whitespace/maqqef between letters
    # "בן אדם" -> "%בן%אדם%"
    like_pattern = "%" + "%".join(phrase_compact.split()) + "%"
    
    rows = conn.execute(
        "SELECT id FROM verses WHERE text_hebrew LIKE ? AND has_hebrew = 1 LIMIT 500",
        (like_pattern,)
    ).fetchall()
    return [r["id"] for r in rows]


def _search_english_phrase(conn, phrase):
    """Find verses containing an English phrase."""
    rows = conn.execute(
        "SELECT id FROM verses WHERE LOWER(text_english) LIKE ? LIMIT 500",
        (f'%{phrase.lower()}%',)
    ).fetchall()
    return [r["id"] for r in rows]


def run(conn, book_ids=None):
    """Connect verses sharing significant phrases."""
    total = 0
    title_count = 0
    batch = []
    
    # ── Hebrew phrases (OT + DSS) ──
    print("  Scanning Hebrew phrases...", end=' ', flush=True)
    heb_count = 0
    for name, phrase in KEY_PHRASES:
        verses = _search_hebrew_phrase(conn, phrase)
        if len(verses) >= 2:
            title_count += 1
            # Hub-and-spoke
            for i in range(1, min(len(verses), 51)):
                batch.append((
                    verses[0], verses[i],
                    "linguistic", "keyword_linking", f"hebrew_phrase",
                    0.5, 0.4, "algorithm",
                    f'{{"phrase": "{name}", "hebrew": "{phrase}", "occurrences": {len(verses)}}}'
                ))
                heb_count += 1
            if len(batch) >= 200:
                total += len(batch)
                _flush(conn, batch)
                batch = []
    
    if batch:
        total += len(batch)
        _flush(conn, batch)
        batch = []
    print(f"{heb_count} connections from {title_count} phrases")
    
    # ── English phrases (NT, BoM, D&C, Apocrypha, Pseudepigrapha) ──
    print("  Scanning English phrases...", end=' ', flush=True)
    eng_count = 0
    eng_title_count = 0
    for phrase in ENGLISH_PHRASES:
        verses = _search_english_phrase(conn, phrase)
        if len(verses) >= 2:
            eng_title_count += 1
            for i in range(1, min(len(verses), 51)):
                batch.append((
                    verses[0], verses[i],
                    "linguistic", "keyword_linking", f"english_phrase",
                    0.45, 0.35, "algorithm",
                    f'{{"phrase": "{phrase}", "occurrences": {len(verses)}}}'
                ))
                eng_count += 1
            if len(batch) >= 200:
                total += len(batch)
                _flush(conn, batch)
                batch = []
    
    if batch:
        total += len(batch)
        _flush(conn, batch)
        batch = []
    print(f"{eng_count} connections from {eng_title_count} English phrases")
    
    print(f"  Total phrase matches: {total}")
    return total


def _flush(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
    batch.clear()
