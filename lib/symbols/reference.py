"""Symbol reference table — seed data and database operations."""

import contextlib

from ..db import add_connection

# === SEED DATA: ~80 known scriptural symbols ===

SEED_SYMBOLS = [
    # Animals
    {"name": "lamb", "category": "animal", "meaning": "Sacrifice / Christ's atonement / innocence"},
    {"name": "lion", "category": "animal", "meaning": "Judah / Christ's kingship / strength / devourer"},
    {"name": "serpent", "category": "animal", "meaning": "Satan / adversary / wisdom"},
    {"name": "dragon", "category": "animal", "meaning": "Satan / chaos / end-time opposition"},
    {"name": "eagle", "category": "animal", "meaning": "Divine protection / swift judgment / renewal"},
    {"name": "horse", "category": "animal", "meaning": "Warfare / judgment / victory"},
    {"name": "dove", "category": "animal", "meaning": "Holy Spirit / peace / purity"},
    {"name": "fox", "category": "animal", "meaning": "Herod / deception / destruction"},
    {"name": "wolf", "category": "animal", "meaning": "False prophets / enemies of the flock"},
    {"name": "serpent_bronze", "category": "animal", "meaning": "Christ lifted up / healing through looking"},
    {"name": "fish", "category": "animal", "meaning": "Believers / evangelism / multiplication"},

    # Plants
    {"name": "tree_of_life", "category": "plant", "meaning": "Eternal life / Christ / wisdom"},
    {"name": "vine", "category": "plant", "meaning": "Israel / Christ / covenant people"},
    {"name": "fig_tree", "category": "plant", "meaning": "Israel / judgment / fruitfulness"},
    {"name": "olive_tree", "category": "plant", "meaning": "Israel / covenant / Holy Spirit / peace"},
    {"name": "mustard_seed", "category": "plant", "meaning": "Kingdom of heaven / faith growing large"},
    {"name": "lily", "category": "plant", "meaning": "God's provision / beauty / purity"},
    {"name": "cedar", "category": "plant", "meaning": "Strength / pride / Lebanon / temple"},
    {"name": "thorns", "category": "plant", "meaning": "Curse / sin / suffering / crown of Christ"},

    # Food
    {"name": "bread", "category": "food", "meaning": "Christ / word of God / provision / body of Christ"},
    {"name": "wine", "category": "food", "meaning": "Blood of covenant / joy / Spirit"},
    {"name": "milk", "category": "food", "meaning": "Pure word / spiritual infancy"},
    {"name": "honey", "category": "food", "meaning": "God's word / abundance / promised land"},
    {"name": "water_living", "category": "food", "meaning": "Holy Spirit / eternal life / Christ"},
    {"name": "manna", "category": "food", "meaning": "God's provision / Christ as bread from heaven"},

    # Elements
    {"name": "fire", "category": "element", "meaning": "God's presence / purification / judgment / Holy Spirit"},
    {"name": "water", "category": "element", "meaning": "Life / cleansing / Spirit / word"},
    {"name": "wind", "category": "element", "meaning": "Spirit / God's power / change"},
    {"name": "earthquake", "category": "element", "meaning": "God's presence / judgment / kingdom shaking"},
    {"name": "cloud", "category": "element", "meaning": "God's presence / glory / covering"},
    {"name": "light", "category": "element", "meaning": "Christ / truth / righteousness / God's presence"},
    {"name": "darkness", "category": "element", "meaning": "Sin / ignorance / judgment / separation from God"},

    # Objects
    {"name": "throne", "category": "object", "meaning": "God's sovereignty / kingship / judgment seat"},
    {"name": "crown", "category": "object", "meaning": "Victory / authority / eternal reward"},
    {"name": "scepter", "category": "object", "meaning": "Authority / rule / Messiah's reign"},
    {"name": "sword", "category": "object", "meaning": "God's word / judgment / warfare"},
    {"name": "key", "category": "object", "meaning": "Authority / access / kingdom"},
    {"name": "seal", "category": "object", "meaning": "Ownership / security / authenticity / judgment"},
    {"name": "trumpet", "category": "object", "meaning": "Warning / assembly / God's voice / judgment"},
    {"name": "scroll", "category": "object", "meaning": "God's word / prophecy / judgment / revelation"},
    {"name": "altar", "category": "object", "meaning": "Sacrifice / worship / covenant"},
    {"name": "lampstand", "category": "object", "meaning": "Church / Spirit / God's light"},
    {"name": "incense", "category": "object", "meaning": "Prayers of the saints / worship"},
    {"name": "robe", "category": "object", "meaning": "Righteousness / identity / authority"},
    {"name": "shield", "category": "object", "meaning": "Faith / God's protection"},
    {"name": "rock", "category": "object", "meaning": "Christ / foundation / refuge"},
    {"name": "cornerstone", "category": "object", "meaning": "Christ / foundation of the church"},
    {"name": "ark_noah", "category": "object", "meaning": "Salvation / Christ / the church"},
    {"name": "measuring_rod", "category": "object", "meaning": "Judgment / restoration / God's standard"},

    # Body parts
    {"name": "right_hand", "category": "body_part", "meaning": "Power / authority / honor"},
    {"name": "eyes", "category": "body_part", "meaning": "Understanding / God's watchfulness / Spirit"},
    {"name": "wings", "category": "body_part", "meaning": "Protection / shelter / divine presence"},
    {"name": "horns", "category": "body_part", "meaning": "Power / kingship / strength"},
    {"name": "heart", "category": "body_part", "meaning": "Inner being / will / center of life"},
    {"name": "feet", "category": "body_part", "meaning": "Walk / conduct / submission"},

    # Beings
    {"name": "cherubim", "category": "being", "meaning": "God's presence / glory bearers / throne attendants"},
    {"name": "seraphim", "category": "being", "meaning": "Heavenly beings / worshipers / purifiers"},
    {"name": "living_creatures", "category": "being", "meaning": "All creation / heavenly worship / stewardship"},
    {"name": "angel_of_lord", "category": "being", "meaning": "Theophany / divine messenger / pre-incarnate Christ"},
    {"name": "beast_from_sea", "category": "being", "meaning": "End-time power / opposition to God's people"},
    {"name": "beast_from_earth", "category": "being", "meaning": "False prophet / religious deception"},
    {"name": "lamb_slain", "category": "being", "meaning": "Christ sacrificed / worthy to open the scroll"},

    # Colors
    {"name": "white", "category": "color", "meaning": "Purity / righteousness / victory / joy"},
    {"name": "red_scarlet", "category": "color", "meaning": "Sin / blood / atonement / warfare"},
    {"name": "purple", "category": "color", "meaning": "Royalty / wealth / majesty"},
    {"name": "black", "category": "color", "meaning": "Mourning / judgment / famine / death"},
    {"name": "green", "category": "color", "meaning": "Life / growth / prosperity"},
    {"name": "blue", "category": "color", "meaning": "Heaven / priesthood / divine law"},

    # Materials
    {"name": "gold", "category": "material", "meaning": "Divinity / kingship / purity / precious faith"},
    {"name": "silver", "category": "material", "meaning": "Redemption / purification / value"},
    {"name": "brass_bronze", "category": "material", "meaning": "Judgment / strength / endurance"},
    {"name": "iron", "category": "material", "meaning": "Strength / oppression / unbending will"},
    {"name": "clay", "category": "material", "meaning": "Humanity / weakness / malleability / creation"},
    {"name": "stone", "category": "material", "meaning": "Christ / the church / God's enduring word"},

    # Places (symbolic)
    {"name": "wilderness", "category": "place", "meaning": "Testing / purification / temptation / refuge"},
    {"name": "mountain", "category": "place", "meaning": "God's presence / revelation / kingdom"},
    {"name": "garden", "category": "place", "meaning": "Presence of God / innocence / covenant"},
    {"name": "city", "category": "place", "meaning": "Civilization / human pride (Babylon) / God's presence (Jerusalem)"},
    {"name": "temple_house", "category": "place", "meaning": "God's dwelling / the church / the believer's body"},
    {"name": "sea", "category": "place", "meaning": "Chaos / nations / death / separation"},

    # Numbers (symbolic)
    {"name": "seven", "category": "number", "meaning": "Divine perfection / completeness / covenant"},
    {"name": "twelve", "category": "number", "meaning": "Divine government / the people of God"},
    {"name": "forty", "category": "number", "meaning": "Testing / preparation / trial"},
    {"name": "ten", "category": "number", "meaning": "Divine order / responsibility / testing"},
    {"name": "hundred_let", "category": "number", "meaning": "Seed of Abraham / fullness / blessing"},
    {"name": "thousand", "category": "number", "meaning": "Immensity / divine fullness / the Lords day"},
    {"name": "four", "category": "number", "meaning": "The earth / creation / universality"},
    {"name": "three", "category": "number", "meaning": "Divine completeness / resurrection / testimony"},
]

# === APOCALYPTIC VOCABULARY (Dan-Ezek-Isa-Rev shared symbols) ===

SEED_APOCALYPTIC = [
    # Format: (symbol_name, book_id, verse_id, context_note)
    # Living creatures / cherubim
    ("living_creatures", "ezek", "ezek.1.5", "Four living creatures with four faces and four wings"),
    ("living_creatures", "ezek", "ezek.10.1", "Cherubim in the temple vision"),
    ("living_creatures", "isa", "isa.6.2", "Seraphim with six wings"),
    ("living_creatures", "rev", "rev.4.6", "Four beasts full of eyes before and behind"),
    ("living_creatures", "rev", "rev.4.8", "Four beasts with six wings each"),

    # Four faces
    ("apocalyptic_creature", "ezek", "ezek.1.10", "Face of a man, lion, ox, eagle"),
    ("apocalyptic_creature", "rev", "rev.4.7", "Face of a lion, calf, man, flying eagle"),

    # Throne vision
    ("throne", "isa", "isa.6.1", "I saw the Lord sitting upon a throne"),
    ("throne", "ezek", "ezek.1.26", "The appearance of a man upon the throne"),
    ("throne", "dan", "dan.7.9", "Thrones were cast down, the Ancient of Days did sit"),
    ("throne", "rev", "rev.4.2", "A throne was set in heaven, and One sat on the throne"),

    # Scroll / book
    ("scroll", "ezek", "ezek.2.9", "A roll of a book was spread before me"),
    ("scroll", "ezek", "ezek.3.1", "Eat this roll"),
    ("scroll", "dan", "dan.12.4", "Shut up the words, and seal the book"),
    ("scroll", "rev", "rev.5.1", "A book written within and on the back, sealed with seven seals"),
    ("scroll", "rev", "rev.10.2", "A little book open in his hand"),

    # Trumpets
    ("trumpet", "isa", "isa.27.13", "The great trumpet shall be blown"),
    ("trumpet", "ezek", "ezek.33.3", "He blow the trumpet and warn the people"),
    ("trumpet", "rev", "rev.8.2", "Seven trumpets were given to the seven angels"),
    ("trumpet", "rev", "rev.8.7", "First angel sounded"),
    ("trumpet", "rev", "rev.9.1", "Fifth angel sounded"),
    ("trumpet", "rev", "rev.9.13", "Sixth angel sounded"),
    ("trumpet", "rev", "rev.11.15", "Seventh angel sounded"),

    # Seals
    ("seal", "dan", "dan.6.18", "The king sealed the den with his signet"),
    ("seal", "isa", "isa.29.11", "The words of a book that is sealed"),
    ("seal", "rev", "rev.5.1", "Book sealed with seven seals"),
    ("seal", "rev", "rev.6.1", "First seal opened"),
    ("seal", "rev", "rev.8.1", "Seventh seal opened"),

    # Beasts from sea
    ("beast_from_sea", "dan", "dan.7.1", "Four beasts from the sea"),
    ("beast_from_sea", "dan", "dan.7.3", "Four great beasts came up from the sea"),
    ("beast_from_sea", "rev", "rev.13.1", "A beast rise up out of the sea with seven heads and ten horns"),

    # Ten horns
    ("apocalyptic_creature", "dan", "dan.7.7", "The fourth beast had ten horns"),
    ("apocalyptic_creature", "dan", "dan.7.24", "The ten horns are ten kings"),
    ("apocalyptic_creature", "rev", "rev.13.1", "Seven heads and ten horns"),
    ("apocalyptic_creature", "rev", "rev.17.3", "A scarlet beast with seven heads and ten horns"),

    # Son of Man
    ("apocalyptic_creature", "dan", "dan.7.13", "One like the Son of Man came with the clouds"),
    ("apocalyptic_creature", "rev", "rev.1.13", "One like unto the Son of Man in the midst of the lampstands"),
    ("apocalyptic_creature", "rev", "rev.14.14", "A white cloud, and on the cloud one like the Son of Man"),

    # Measuring
    ("measuring_rod", "ezek", "ezek.40.3", "A man with a measuring reed"),
    ("measuring_rod", "ezek", "ezek.42.15", "He measured the house"),
    ("measuring_rod", "rev", "rev.11.1", "A reed given to measure the temple"),
    ("measuring_rod", "rev", "rev.21.15", "A golden reed to measure the city"),

    # New Jerusalem
    ("city", "ezek", "ezek.40.1", "The vision of the city/ temple"),
    ("city", "ezek", "ezek.48.35", "The name of the city: The Lord is There"),
    ("city", "rev", "rev.21.2", "A new Jerusalem coming down from heaven"),
    ("city", "rev", "rev.21.10", "The holy Jerusalem descending out of heaven"),

    # River of life
    ("water_living", "ezek", "ezek.47.1", "Water flowing from the temple"),
    ("water_living", "ezek", "ezek.47.9", "Everything shall live where the river goes"),
    ("water_living", "rev", "rev.22.1", "A pure river of water of life"),
    ("water_living", "rev", "rev.22.17", "Whosoever will, let him take the water of life freely"),

    # Tree of life
    ("tree_of_life", "ezek", "ezek.47.12", "Trees for meat on both sides of the river"),
    ("tree_of_life", "rev", "rev.22.2", "The tree of life in the midst of the city"),
    ("tree_of_life", "gen", "gen.2.9", "The tree of life also in the midst of the garden"),
    ("tree_of_life", "gen", "gen.3.22", "Lest he take also of the tree of life"),

    # Gog and Magog
    ("name_symbolic", "ezek", "ezek.38.2", "Set thy face against Gog of Magog"),
    ("name_symbolic", "ezek", "ezek.39.1", "Prophesy against Gog"),
    ("name_symbolic", "rev", "rev.20.8", "Gog and Magog to gather them to battle"),

    # Woman / Bride / Harlot
    ("name_symbolic", "isa", "isa.1.21", "The faithful city become a harlot"),
    ("name_symbolic", "isa", "isa.54.5", "Thy Maker is thine husband"),
    ("name_symbolic", "ezek", "ezek.16.1", "Jerusalem as an unfaithful wife"),
    ("name_symbolic", "ezek", "ezek.23.1", "The allegory of two harlot sisters"),
    ("name_symbolic", "rev", "rev.12.1", "A woman clothed with the sun"),
    ("name_symbolic", "rev", "rev.17.1", "The great whore that sitteth upon many waters"),
    ("name_symbolic", "rev", "rev.19.7", "The marriage of the Lamb is come"),
    ("name_symbolic", "rev", "rev.21.9", "The bride, the Lamb's wife"),

    # Dragon
    ("dragon", "isa", "isa.27.1", "Leviathan the piercing serpent shall be slain"),
    ("dragon", "rev", "rev.12.3", "A great red dragon with seven heads"),
    ("dragon", "rev", "rev.12.9", "That old serpent called the Devil and Satan"),
    ("dragon", "rev", "rev.20.2", "He laid hold on the dragon, that old serpent"),

    # Fire from heaven / earthquake
    ("fire", "rev", "rev.8.5", "Voices, thunderings, lightnings, earthquake"),
    ("fire", "rev", "rev.11.5", "Fire proceeds out of the mouths of the two witnesses"),
    ("fire", "rev", "rev.20.9", "Fire came down from God out of heaven"),
    ("earthquake", "rev", "rev.6.12", "A great earthquake"),
    ("earthquake", "rev", "rev.16.18", "A great earthquake, such as was not since men were upon the earth"),

    # Lamb
    ("lamb", "rev", "rev.5.6", "A Lamb as it had been slain standing"),  # Also passover, isa 53, etc.
    ("lamb", "rev", "rev.5.12", "Worthy is the Lamb that was slain"),
    ("lamb", "rev", "rev.7.17", "The Lamb which is in the midst of the throne"),
    ("lamb", "rev", "rev.21.22", "The Lord God Almighty and the Lamb are the temple"),
    ("lamb", "rev", "rev.22.1", "The throne of God and of the Lamb"),
]

# === TYPOLOGY SEED DATA ===

SEED_TYPOLOGY = [
    # (type_name, antitype_name, type_verse, antitype_verse, description)
    ("Adam", "Christ", "gen.2.7", "1cor.15.45", "Adam was a figure of Him that was to come"),
    ("Adam", "Christ", "gen.3.17", "rom.5.14", "Adam as type of Christ — the first and last Adam"),
    ("Eve", "Church", "gen.2.23", "eph.5.31", "Eve from Adams side — the church from Christs side"),
    ("Melchizedek", "Christ", "gen.14.18", "heb.7.1", "Melchizedek, king of righteousness and peace, priest forever"),
    ("Melchizedek", "Christ", "psa.110.4", "heb.7.17", "Thou art a priest forever after the order of Melchizedek"),
    ("Moses", "Christ", "deu.18.15", "acts.3.22", "A prophet like unto me shall ye hear"),
    ("Moses", "Christ", "exo.2.1", "heb.3.1", "Moses as a servant, Christ as a Son"),
    ("David", "Christ", "2sam.7.12", "luke.1.32", "The Lord God shall give unto him the throne of his father David"),
    ("Jonah", "Christ", "jonah.1.17", "matt.12.40", "Three days in the fish — three days in the tomb"),
    ("Elijah", "John the Baptist", "mal.4.5", "matt.11.14", "Elijah must come before the great day of the Lord"),
    ("Joshua", "Jesus", "josh.1.1", "heb.4.8", "Joshua leads into rest — Jesus leads into salvation"),

    # Event typology
    ("Passover", "Crucifixion", "exo.12.3", "1cor.5.7", "Christ our passover is sacrificed for us"),
    ("Exodus", "Redemption", "exo.14.1", "1cor.10.1", "The exodus as a type of redemption in Christ"),
    ("Passover", "Crucifixion", "exo.12.46", "john.19.36", "Not a bone of the passover lamb broken / not a bone of Christ broken"),
    ("Flood", "Baptism", "gen.7.1", "1pet.3.20", "Eight souls saved through water — the like figure of baptism"),
    ("Flood", "Judgment", "gen.6.1", "2pet.3.6", "The flood as a type of final judgment by fire"),
    ("Wilderness", "Testing", "num.14.1", "1cor.10.1", "All our fathers were under the cloud — examples for us"),
    ("Wilderness", "Testing", "deu.8.2", "matt.4.1", "Forty years/forty days of testing in the wilderness"),
    ("Tabernacle", "Heavenly Temple", "exo.25.40", "heb.8.5", "The pattern showed thee in the mount — the heavenly reality"),
    ("Day of Atonement", "Atonement of Christ", "lev.16.1", "heb.9.1", "The high priest enters the holy place — Christ enters heaven"),

    # Object typology
    ("Serpent_bronze", "Cross of Christ", "num.21.8", "john.3.14", "Look and live — the Son of Man lifted up"),
    ("Manna", "Bread of Life", "exo.16.4", "john.6.32", "Not Moses gave you bread from heaven — I am the bread of life"),
    ("Rock/water", "Christ/Living Water", "exo.17.6", "1cor.10.4", "They drank of that spiritual Rock which is Christ"),
    ("Rock/water", "Christ/Living Water", "exo.17.6", "john.4.10", "The water I give shall be a well of water springing up"),
    ("Cities of Refuge", "Christ/Refuge", "num.35.6", "heb.6.18", "Flee for refuge to lay hold on the hope set before us"),
    ("Brazen Altar", "Cross", "exo.27.1", "heb.13.10", "We have an altar"),
    ("Golden Lampstand", "Church/Spirit", "exo.25.31", "rev.1.20", "The seven lampstands are the seven churches"),
    ("Veil of Temple", "Body of Christ", "exo.26.31", "heb.10.20", "The veil is his flesh — a new and living way"),
]


def seed_symbol_tables(conn):
    """Populate the symbols and symbol_occurrences tables with seed data.
    Safe to run multiple times (uses INSERT OR IGNORE)."""

    count_s = 0
    count_o = 0
    count_t = 0

    # Insert symbols
    for sym in SEED_SYMBOLS:
        conn.execute("""
            INSERT OR IGNORE INTO symbols (name, category, meaning)
            VALUES (?, ?, ?)
        """, (sym["name"], sym["category"], sym["meaning"]))
        if conn.execute("SELECT changes()").fetchone()[0] > 0:
            count_s += 1

    # Insert apocalyptic occurrences
    for sym_name, _book, verse, note in SEED_APOCALYPTIC:
        # Get the symbol ID
        row = conn.execute("SELECT id FROM symbols WHERE name = ?", (sym_name,)).fetchone()
        if not row:
            continue
        sid = row["id"]
        conn.execute("""
            INSERT OR IGNORE INTO symbol_occurrences (symbol_id, verse_id, strength, context_note)
            VALUES (?, ?, 0.8, ?)
        """, (sid, verse, note))
        count_o += 1

        # Also create intertextual-style connections between apocalyptic verses
        # that share the same symbol (connect this verse to all previous ones for this symbol)
        siblings = conn.execute("""
            SELECT verse_id FROM symbol_occurrences
            WHERE symbol_id = ? AND verse_id != ?
        """, (sid, verse)).fetchall()
        for sib in siblings:
            with contextlib.suppress(Exception):
                add_connection(conn, verse, sib["verse_id"],
                              layer="symbolic", type_name="apocalyptic_creature",
                              subtype=sym_name, strength=0.7,
                              discovered_by="algorithm",
                              metadata={"symbol": sym_name})

    # Insert typology
    for t in SEED_TYPOLOGY:
        conn.execute("""
            INSERT OR IGNORE INTO typology (type_name, antitype_name, type_verse, antitype_verse, description)
            VALUES (?, ?, ?, ?, ?)
        """, t)
        count_t += 1

        # Create symbolic connections for each typology pair
        with contextlib.suppress(Exception):
            add_connection(conn, t[2], t[3],
                          layer="symbolic", type_name="person_type" if t[0] in [
                              "Adam", "Eve", "Melchizedek", "Moses", "David", "Jonah",
                              "Elijah", "Joshua"
                          ] else "event_type",
                          subtype=t[0].lower().replace(" ", "_"),
                          strength=0.85,
                          discovered_by="algorithm",
                          metadata={"type": t[0], "antitype": t[1]})

    conn.commit()
    return {"symbols": count_s, "occurrences": count_o, "typology": count_t}


def get_symbol(conn, name):
    """Get a symbol by name."""
    row = conn.execute("SELECT * FROM symbols WHERE name = ?", (name,)).fetchone()
    return dict(row) if row else None


def get_all_symbols(conn, category=None):
    """Get all symbols, optionally filtered by category."""
    sql = "SELECT * FROM symbols"
    params = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += " ORDER BY category, name"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def add_symbol(conn, name, category, meaning, ai_discovered=0):
    """Add a new symbol (used by AI for novel discoveries)."""
    conn.execute("""
        INSERT INTO symbols (name, category, meaning, ai_discovered)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            meaning = CASE WHEN excluded.ai_discovered = 1 THEN excluded.meaning ELSE meaning END
    """, (name, category, meaning, ai_discovered))
    conn.commit()


def get_occurrences(conn, symbol_name=None, verse_id=None):
    """Get symbol occurrences, filtered by symbol or verse."""
    sql = """
        SELECT so.*, s.name as symbol_name, s.category, s.meaning,
               v.text_english, b.title as book_title
        FROM symbol_occurrences so
        JOIN symbols s ON s.id = so.symbol_id
        JOIN verses v ON v.id = so.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE 1=1
    """
    params = []
    if symbol_name:
        sql += " AND s.name = ?"
        params.append(symbol_name)
    if verse_id:
        sql += " AND so.verse_id = ?"
        params.append(verse_id)
    sql += " ORDER BY s.category, so.verse_id"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def add_occurrence(conn, symbol_name, verse_id, strength=0.5, context_note=""):
    """Add a symbol occurrence (used by AI for novel discoveries)."""
    sym = get_symbol(conn, symbol_name)
    if not sym:
        return {"error": f"Symbol '{symbol_name}' not found. Add it first."}
    conn.execute("""
        INSERT OR IGNORE INTO symbol_occurrences (symbol_id, verse_id, strength, context_note)
        VALUES (?, ?, ?, ?)
    """, (sym["id"], verse_id, strength, context_note))
    conn.commit()
