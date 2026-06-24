"""Experimental: runs Isaiah-derived techniques on ALL canonical books.
Tests whether Isaiah's patterns appear elsewhere. Can be pruned later."""

from collections import defaultdict, Counter
from lib.db import add_connection

ALL_HEBREW = ['gen','exo','lev','num','deu','josh','judg','ruth','1sam','2sam','1kgs','2kgs','1chr','2chr','ezra','neh','esth','job','psa','prov','eccl','song','isa','jer','lam','ezek','dan','hos','joel','amos','obad','jonah','mic','nah','hab','zeph','hag','zech','mal']
ALL_BOM = ['1ne','2ne','jacob','enos','jarom','omni','wom','mosiah','alma','hel','3ne','4ne','morm','ether','moro']
ALL_NT = ['matt','mark','luke','john','acts','rom','1cor','2cor','gal','eph','phil','col','1thes','2thes','1tim','2tim','titus','philem','heb','james','1pet','2pet','1john','2john','3john','jude','rev']

GILIADI_CATCHWORDS = {
    "Zion": ["6726", "ציון"],
    "Remnant": ["7611", "שארית", "8300", "שריד"],
    "Covenant": ["1285", "ברית"],
    "Righteousness": ["6664", "6666", "צדק"],
    "Judgment": ["4941", "משפט"],
    "Salvation": ["3444", "3467", "ישע"],
    "Holy One": ["6918", "קדוש"],
    "Servant": ["5650", "עבד"],
    "Nations": ["1471", "גוי"],
    "Everlasting": ["5769", "עולם"],
    "Light": ["216", "215", "אור"],
    "Darkness": ["2822", "חשך"],
    "Redeemer": ["1350", "גאל"],
    "Peace": ["7965", "שלום"],
    "King": ["4428", "מלך"],
    "Deliverance/Yesha": ["3467", "3444", "ישע"],
}

# Spiritual level keywords: mapping Hebrew and English terms
SPIRITUAL_LEVEL_KEYWORDS = {
    "perdition": {
        "heb": ["6586", "4784", "205", "7845"],
        "eng": ["son of perdition", "sons of perdition", "perdition", "satan", "devil", "damnation"],
    },
    "babylon": {
        "heb": ["6091", "6456", "2181", "465"],
        "eng": ["babylon", "harlot", "whore of babylon", "idol", "idolatry", "abomination", "mystery babylon"],
    },
    "israel": {
        "heb": ["3290", "3478", "669"],
        "eng": ["house of israel", "house of jacob", "remnant of israel", "tribes of israel"],
    },
    "zion": {
        "heb": ["6726", "3389"],
        "eng": ["house of zion", "city of zion", "daughter of zion", "zions", "remnant of the lord"],
    },
    "sons_daughters": {
        "heb": ["1121", "1323", "5650", "4899"],
        "eng": ["sons of god", "sons of the lord", "daughters of god", "child of god", "children of christ", "sons and daughters", "servant of the lord", "anointed"],
    },
    "seraphim": {
        "heb": ["8314", "3742", "4397", "6918"],
        "eng": ["seraphim", "cherubim", "holy angels", "ministering spirits", "heavenly host"],
    },
    "jehovah": {
        "heb": ["3068", "6918", "6635", "1350"],
        "eng": ["holy one of israel", "lord of hosts", "god of israel", "king of zion", "redeemer of israel", "jehovah"],
    },
}


def run(conn, book_ids=None):
    """Run all Isaiah-derived techniques on every canonical book."""
    total = 0
    batch = []

    # Clean slate
    for subtype in ['x_seraphim','x_zion','x_babylon','x_israel','x_sons_daughters','x_perdition','x_jehovah',
                    'x_catchword', 'x_keyword_hub']:
        conn.execute("DELETE FROM connections WHERE subtype=?", (subtype,))
    conn.commit()

    # ── 1. SPIRITUAL LEVEL KEYWORD SEARCH ──
    # Run across ALL books: OT prophets via Hebrew, BoM+NT+D&C via English
    for level_name, keywords in SPIRITUAL_LEVEL_KEYWORDS.items():
        # Hebrew books
        for book in ALL_HEBREW:
            for kw in keywords["heb"]:
                rows = conn.execute("""
                    SELECT DISTINCT g.verse_id FROM gematria g
                    JOIN verses v ON v.id = g.verse_id
                    WHERE v.book_id = ? AND g.lemma LIKE ?
                    LIMIT 30
                """, (book, f"%{kw}%")).fetchall()
                for r in rows:
                    vid = r["verse_id"]
                    batch.append((
                        f"isa.1.2", vid, "interpretive",
                        "giliadi_pattern", f"x_{level_name}",
                        0.3, 0.25, "algorithm",
                        f'{{"experiment": "spiritual_level", "level": "{level_name}", "book": "{book}", "match": "hebrew"}}'
                    ))
                    total += 1
                    if len(batch) >= 200: _batch_insert(conn, batch); batch = []

        # English books
        for book in ALL_BOM + ALL_NT + ['dc']:
            for kw in keywords["eng"]:
                tbl = "verses" if book != 'dc' else "verses"
                prefix = "dc%" if book == 'dc' else book
                if prefix == 'dc%':
                    rows = conn.execute("""
                        SELECT id FROM verses WHERE book_id LIKE 'dc%' AND text_english LIKE ? LIMIT 30
                    """, (f"%{kw}%",)).fetchall()
                else:
                    rows = conn.execute("""
                        SELECT id FROM verses WHERE book_id = ? AND text_english LIKE ? LIMIT 30
                    """, (book, f"%{kw}%")).fetchall()
                for r in rows:
                    vid = r[0]
                    batch.append((
                        f"isa.1.2", vid, "interpretive",
                        "giliadi_pattern", f"x_{level_name}",
                        0.25, 0.2, "algorithm",
                        f'{{"experiment": "spiritual_level", "level": "{level_name}", "book": "{book}", "match": "english"}}'
                    ))
                    total += 1
                    if len(batch) >= 200: _batch_insert(conn, batch); batch = []

    # ── 2. GILIADI CATCHWORD LIKING ──
    # Connect verses that share a Giliadi catchword within each book
    for word_name, strongs_and_heb in GILIADI_CATCHWORDS.items():
        heb_kw = strongs_and_heb[0]  # first Strong's number
        for book in ALL_HEBREW:
            rows = conn.execute("""
                SELECT g.verse_id FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = ? AND g.lemma LIKE ?
                LIMIT 50
            """, (book, f"%{heb_kw}%")).fetchall()
            verse_ids = list(set(r["verse_id"] for r in rows if not r["verse_id"].startswith("isa.")))
            if len(verse_ids) >= 2:
                hub = verse_ids[0]
                for vid in verse_ids[1:]:
                    batch.append((
                        hub, vid, "linguistic",
                        "keyword_linking", "x_catchword",
                        0.3, 0.25, "algorithm",
                        f'{{"experiment": "catchword", "word": "{word_name}", "book": "{book}"}}'
                    ))
                    total += 1
                    if len(batch) >= 200: _batch_insert(conn, batch); batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Experimental cross-canon: {total} connections")
    print(f"  (9 spiritual level types + {len(GILIADI_CATCHWORDS)} catchwords)")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
