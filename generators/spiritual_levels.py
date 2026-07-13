"""Seven Spiritual Levels — Giliadi's Ladder to Heaven (Isaiah Decoded).

The correct framework from Giliadi's book:

1. Perdition          — King of Assyria/Babylon, archtyrant, unredeemable
2. Babylon/Chaldea    — Idolaters, evildoers, wicked of the world
3. Jacob/Israel       — Believers in God but wayward, idolatrous
4. Zion/Jerusalem     — God's covenant people, redeemed
5. Sons/Daughters     — Servants of God, proxy saviors
6. Seraphim           — Angelic emissaries (Abraham, Moses as types)
7. Jehovah            — God of Israel, the Son
"""


# Each level: hub verse, keywords (Strong's numbers and Hebrew), strength
LEVELS = [
    {
        "name": "perdition",
        "label": "Perdition — King of Assyria/Babylon, Unredeemable",
        "hub": "isa.10.5",
        "strength": 0.7,
        "keywords": [
            "804", "אשור",         # Assyria (the archtyrant power)
            "894", "בבל",          # Babylon
            "4714", "מצרים",       # Egypt (conquered by Assyria)
            "7585", "שאול",        # Sheol/Pit (destination of archtyrant)
            "7845", "שחת",         # Pit/Corruption
            "639", "אף",           # Anger (pseudonym of archtyrant)
            "5678", "עברה",        # Wrath (archtyrant pseudonym)
            "2534", "חמה",         # Heat/Wrath
            "4057", "מדבר",        # Wilderness (desolation)
        ],
    },
    {
        "name": "babylon",
        "label": "Babylon/Chaldea — Idolaters & Evildoers",
        "hub": "isa.47.1",
        "strength": 0.65,
        "keywords": [
            "894", "בבל",          # Babylon
            "3778", "כשדי",        # Chaldea
            "2181", "זנה",         # Harlot
            "6091", "עצב",         # Idols
            "6456", "פסיל",        # Graven image
            "6049", "ענן",         # Divination/sorcery
            "3784", "כשף",         # Witchcraft
            "5956", "עלם",         # Conceal/deceive
            "8267", "שקר",         # Falsehood
        ],
    },
    {
        "name": "israel",
        "label": "Jacob/Israel — Wayward Believers",
        "hub": "isa.1.2",
        "strength": 0.6,
        "keywords": [
            "3290", "יעקב",        # Jacob
            "3478", "ישראל",        # Israel
            "669", "אפרים",         # Ephraim
            "5787", "עור",          # Blind
            "2795", "חרש",         # Deaf
            "8451", "תורה",         # Torah/law (they abandon)
        ],
    },
    {
        "name": "zion",
        "label": "Zion/Jerusalem — Covenant People",
        "hub": "isa.52.1",
        "strength": 0.65,
        "keywords": [
            "6726", "ציון",        # Zion
            "3389", "ירושלם",       # Jerusalem
            "6664", "צדק",          # Righteousness
            "4941", "משפט",         # Justice
            "1285", "ברית",         # Covenant
            "2617", "חסד",          # Lovingkindness/mercy
            "571", "אמת",           # Truth
            "7611", "שארית",        # Remnant
        ],
    },
    {
        "name": "sons_daughters",
        "label": "Sons/Daughters — Servants of God",
        "hub": "isa.38.5",
        "strength": 0.65,
        "keywords": [
            "5650", "עבד",          # Servant
            "1121", "בן",           # Son
            "1323", "בת",           # Daughter
            "4428", "מלך",          # King
            "4899", "משיח",        # Anointed one/Messiah
            "2220", "זרוע",         # Arm (servant pseudonym)
            "3027", "יד",           # Hand (servant pseudonym)
            "5251", "נס",           # Ensign/banner
        ],
    },
    {
        "name": "seraphim",
        "label": "Seraphim — Angelic Emissaries",
        "hub": "isa.6.2",
        "strength": 0.7,
        "keywords": [
            "8314", "שרף",          # Seraph/seraphim
            "3742", "כרוב",         # Cherub/cherubim
            "4397", "מלאך",         # Angel/messenger
            "6918", "קדוש",         # Holy one
            "4720", "מקדש",         # Sanctuary/temple
            "3519", "כבוד",         # Glory
        ],
    },
    {
        "name": "jehovah",
        "label": "Jehovah — God of Israel, the Son",
        "hub": "isa.6.1",
        "strength": 0.8,
        "keywords": [
            "3068", "יהוה",         # YHWH
            "430", "אלהים",          # Elohim
            "410", "אל",            # El (God)
            "6918", "קדוש",         # Kadosh/Holy One
            "6635", "צבאות",        # YHWH of Hosts
            "135", "אדני",          # Adonai/Lord
            "136", "אדני",          # My Lord
            "3467", "ישע",          # Salvation
            "1350", "גאל",          # Redeemer
        ],
    },
]


def run(conn, book_ids=None):
    """Classify Isaiah verses by Giliadi's 7 spiritual levels.

    For each level, find Isaiah verses matching its keyword signatures
    and connect them to the level's hub verse.
    """
    # Clear previous incorrect levels
    conn.execute("DELETE FROM connections WHERE type='giliadi_pattern' AND subtype LIKE 'spiritual_level_%'")
    conn.commit()

    total = 0
    batch = []

    for level in LEVELS:
        name = level["name"]
        label = level["label"]
        hub = level["hub"]
        strength = level["strength"]

        for kw in level["keywords"]:
            # Search by Strong's number or Hebrew text
            pattern = f"%{kw}%"
            rows = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = 'isa'
                  AND (g.lemma LIKE ? OR g.word_hebrew LIKE ?)
                LIMIT 150
            """, (pattern, pattern)).fetchall()

            for r in rows:
                verse_id = r["verse_id"]
                if verse_id == hub:
                    continue
                batch.append((
                    hub, verse_id, "interpretive",
                    "giliadi_pattern", f"spiritual_level_{name}",
                    strength, 0.5, "algorithm",
                    f'{{"level": "{name}", "label": "{label}", "ladder": "Gileadi_7_levels"}}'
                ))
                total += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Spiritual levels (corrected): {total} connections across {len(LEVELS)} levels")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
