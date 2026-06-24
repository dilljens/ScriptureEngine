"""Isaiah advanced analysis — techniques from Giliadi's books.

Implements 7 methods from Isaiah Decoded and The End from the Beginning:

1. Two Days of Jehovah — midpoint (Isa 34-35) and final (Isa 63-66)
2. Threat One/Two/Three — escalating judgment patterns
3. Curses↔Blessings — covenant reversal pairs
4. Destruction↔Deliverance — antithetical paired sections
5. Tabernacle as Ladder — 7 tabernacle elements → 7 spiritual levels
6. Cyclical History — past events as types of future ones
7. DSS Paragraph Markers — 1QIsa structural division markers
"""

from lib.db import add_connection


def _verse_id(book, ch, v):
    return f"{book}.{ch}.{v}"


# ─── 1. DAYS OF JEHOVAH ───
# Giliadi identifies two "Days of Jehovah" in Isaiah
# Midpoint: Isa 34-35 (the "Day of Vengeance" / judgment of nations)
# Final: Isa 63-66 (the "Great and Dreadful Day" / final judgment)

DAY_OF_JEHOVAH_MIDPOINT = {
    "label": "Day of Jehovah — Midpoint (Isa 34-35)",
    "start": "isa.34.1",
    "end": "isa.35.10",
    "markers": ["isa.34.1", "isa.34.8", "isa.35.1", "isa.35.10"],
    "features": [
        "Vengeance on nations",
        "Desolation of Edom",
        "Wilderness blooming",
        "New exodus to Zion",
    ],
}

DAY_OF_JEHOVAH_FINAL = {
    "label": "Day of Jehovah — Final (Isa 63-66)",
    "start": "isa.63.1",
    "end": "isa.66.24",
    "markers": ["isa.63.1", "isa.63.4", "isa.65.1", "isa.66.15", "isa.66.24"],
    "features": [
        "Vengeance on Edom/peoples",
        "Jehovah's descent with power",
        "New creation",
        "Final separation of righteous/wicked",
    ],
}


# ─── 2. THREE THREATS ───
# Three escalating threat patterns
THREATS = [
    {
        "label": "Threat One — Assyrian Invasion of Israel",
        "start": "isa.5.1",
        "end": "isa.10.34",
        "climax": "isa.10.5",
        "type": "Threat One",
        "description": "Assyria as rod of God's anger against Israel",
    },
    {
        "label": "Threat Two — Assyrian World Conquest",
        "start": "isa.13.1",
        "end": "isa.24.23",
        "climax": "isa.14.12",
        "type": "Threat Two",
        "description": "Worldwide devastation through Assyria/Babylon",
    },
    {
        "label": "Threat Three — Final Day of Jehovah",
        "start": "isa.34.1",
        "end": "isa.35.10",
        "climax": "isa.34.8",
        "type": "Threat Three",
        "description": "Ultimate destruction preceding salvation",
    },
]


# ─── 3. CURSES ↔ BLESSINGS ───
# Covenant curse passages and their corresponding blessing reversals
CURSES_BLESSINGS = [
    # (curse_start, curse_end, blessing_start, blessing_end, theme)
    ("isa.1.2", "isa.1.15", "isa.1.16", "isa.1.31", "Repentance → Cleansing"),
    ("isa.3.1", "isa.4.1", "isa.4.2", "isa.4.6", "Judgment → Branch of Jehovah"),
    ("isa.5.1", "isa.5.30", "isa.12.1", "isa.12.6", "Wild grapes → Song of Salvation"),
    ("isa.9.8", "isa.10.4", "isa.11.1", "isa.12.6", "Ephraim's fall → Rod of Jesse"),
    ("isa.22.1", "isa.22.25", "isa.23.1", "isa.23.18", "Valley of Vision → Tyre restored"),
    ("isa.28.1", "isa.29.24", "isa.30.18", "isa.33.24", "Woe to Ephraim → Zion restored"),
    ("isa.40.1", "isa.40.11", "isa.40.12", "isa.40.31", "Comfort → God's incomparability"),
    ("isa.42.18", "isa.43.28", "isa.44.1", "isa.45.25", "Blind servant → Israel redeemed"),
    ("isa.50.1", "isa.51.8", "isa.51.9", "isa.52.12", "Zion's awakening → Arm of Jehovah"),
    ("isa.59.1", "isa.59.21", "isa.60.1", "isa.62.12", "Sin confessed → Zion's glory"),
    ("isa.63.7", "isa.64.12", "isa.65.1", "isa.66.24", "Lament → New creation"),
]


# ─── 4. DESTRUCTION ↔ DELIVERANCE ANTITHETICAL PAIRS ───
DESTRUCTION_DELIVERANCE = [
    # (destruction_start, destruction_end, deliverance_start, deliverance_end, theme)
    ("isa.13.1", "isa.14.23", "isa.14.24", "isa.14.32", "Babylon destroyed → Zion established"),
    ("isa.15.1", "isa.16.14", "isa.16.1", "isa.16.5", "Moab destroyed → Davidic throne"),
    ("isa.17.1", "isa.17.14", "isa.18.1", "isa.18.7", "Ephraim/Damascus → Ethiopia's gift"),
    ("isa.19.1", "isa.19.17", "isa.19.18", "isa.20.6", "Egypt smitten → Egypt healed"),
    ("isa.21.1", "isa.21.17", "isa.22.20", "isa.22.25", "Babylon/Edom/Arabia → Eliakim"),
    ("isa.34.1", "isa.35.10", "isa.35.1", "isa.35.10", "Edom desolated → Zion rejoices"),
    ("isa.47.1", "isa.47.15", "isa.52.1", "isa.52.15", "Babylon humbled → Zion awakes"),
    ("isa.64.1", "isa.64.12", "isa.65.1", "isa.66.24", "Jehovah's wrath → New heavens/earth"),
]


# ─── 5. TABERNACLE AS LADDER ───
# 7 tabernacle elements mapping to 7 spiritual levels (from Giliadi's Ch 9)
TABERNACLE_LADDER = [
    ("Court/Gate", "Perdition — the gate of judgment, exclusion from the sanctuary",
     "exo.27.9", "Courtyard barrier separating the unclean"),
    ("Bronze Altar", "Babylon — sacrifice of worldly things, repentance begins",
     "exo.27.1", "Altar of burnt offering — sacrifice and repentance"),
    ("Laver", "Jacob/Israel — washing, spiritual awakening",
     "exo.30.18", "Laver of cleansing — spiritual rebirth"),
    ("Holy Place (Table)", "Zion/Jerusalem — bread of presence, covenant fellowship",
     "exo.25.23", "Table of showbread — covenant relationship"),
    ("Holy Place (Lampstand)", "Sons/Daughters — light of ministry",
     "exo.25.31", "Golden lampstand — enlightenment and ministry"),
    ("Holy Place (Incense)", "Seraphim — prayers ascending, heavenly intercession",
     "exo.30.1", "Altar of incense — intercession and worship"),
    ("Holy of Holies", "Jehovah — divine presence)",
     "exo.26.31", "Veil and Ark — God's presence"),
]


# ─── 6. CYCLICAL HISTORY — TYPES AND SHADOWS ───
# Past events that Isaiah uses as types of end-time events
# All 30 types from Giliadi's "Isaiah's Ancient Types of End-Time Events" page
CYCLICAL_TYPES = [
    # (past_event_start, past_event_end, future_type_start, future_type_end, description)
    ("gen.6.1", "gen.9.29", "isa.24.1", "isa.27.13", "Noah's Flood → End-time desolation"),
    ("gen.19.1", "gen.19.38", "isa.13.1", "isa.14.23", "Sodom/Gomorrah → Babylon's fall"),
    ("exo.3.1", "exo.15.27", "isa.43.14", "isa.44.5", "Exodus from Egypt → New exodus from Babylon"),
    ("exo.19.1", "exo.20.26", "isa.2.1", "isa.4.6", "Sinai covenant → End-time covenant"),
    ("josh.6.1", "josh.6.27", "isa.11.1", "isa.12.6", "Jericho fall → Messianic kingdom"),
    ("2sam.11.1", "2sam.12.31", "isa.14.1", "isa.14.32", "David's victories → End-time deliverance"),
    ("1kgs.18.1", "1kgs.19.21", "isa.40.1", "isa.40.31", "Elijah's ministry → Forerunner of Jehovah"),
    ("2kgs.18.1", "2kgs.20.21", "isa.36.1", "isa.39.8", "Hezekiah's deliverance → End-time remnant"),
    ("gen.11.1", "gen.11.9", "isa.13.1", "isa.14.23", "Tower of Babel → End-time Babylon"),
    ("exo.1.1", "exo.2.25", "isa.10.1", "isa.10.34", "Egyptian bondage → Assyrian oppression"),
    ("exo.12.1", "exo.12.51", "isa.52.11", "isa.52.15", "Passover → End-time redemption"),
    ("exo.13.20", "exo.15.21", "isa.43.14", "isa.44.5", "Red Sea deliverance → New exodus"),
    ("exo.15.22", "exo.17.16", "isa.33.1", "isa.33.24", "Wilderness wandering → End-time testing"),
    ("exo.16.1", "exo.16.36", "isa.55.1", "isa.55.13", "Manna from heaven → Bread of life"),
    ("exo.19.1", "exo.19.25", "isa.63.1", "isa.64.12", "Sinai theophany → Jehovah's descent"),
    ("exo.24.1", "exo.24.18", "isa.24.1", "isa.24.23", "Moses on mount → Jehovah on mount"),
    ("num.21.4", "num.21.9", "isa.53.1", "isa.53.12", "Brazen serpent → Lifted Savior"),
    ("josh.1.1", "josh.12.24", "isa.11.1", "isa.12.6", "Conquest of Canaan → End-time inheritance"),
    ("judg.6.1", "judg.7.25", "isa.9.1", "isa.10.34", "Gideon's victory → End-time deliverance"),
    ("2kgs.25.1", "2kgs.25.30", "isa.47.1", "isa.47.15", "Babylonian captivity → End-time captivity"),
    ("ezra.3.1", "ezra.6.22", "isa.60.1", "isa.62.12", "Rebuilding temple → End-time temple"),
    ("gen.1.1", "gen.2.3", "isa.65.17", "isa.66.24", "Creation → New creation"),
    ("gen.2.8", "gen.3.24", "isa.51.3", "isa.51.16", "Garden of Eden → Millennial paradise"),
    # Types 23-30: Remaining from Giliadi's full 30-type list
    ("exo.13.20", "exo.14.31", "isa.4.5", "isa.4.6", "Pillar of cloud → Jehovah's protective presence"),
    ("isa.36.1", "isa.37.38", "isa.37.30", "isa.37.36", "Assyria's siege of Jerusalem → Divine deliverance"),
    ("1kgs.8.1", "1kgs.8.11", "isa.24.23", "isa.25.9", "Temple dedication → Zion as Jehovah's residence"),
    ("exo.18.13", "exo.18.26", "isa.1.25", "isa.1.26", "Moses' judges → End-time righteous judges"),
    ("num.11.1", "num.26.10", "isa.66.15", "isa.66.24", "Jehovah's consuming fire → End-time judgment"),
    ("josh.10.40", "josh.11.23", "isa.54.15", "isa.54.17", "Conquest of Canaan → Final inheritance"),
    ("judg.7.1", "judg.7.25", "isa.10.26", "isa.10.27", "Midian defeat → Assyria's yoke broken"),
]


# ─── 7b. STRUCTURAL OVERLAYS ───
# Additional structural patterns from Giliadi's "Layered Literary Structures" page

# 3-Part: Trouble at Home → Exile Abroad → Happy Homecoming
THREE_PART = [
    ("Trouble at Home — Rebellion", "isa.1.1", "isa.39.8"),
    ("Exile Abroad — Dispersion", "isa.40.1", "isa.54.17"),
    ("Happy Homecoming — Restoration", "isa.55.1", "isa.66.24"),
]

# 4-Part: Apostasy → Judgment → Restoration → Salvation
FOUR_PART = [
    ("Apostasy — People Break Law", "isa.1.1", "isa.9.21"),
    ("Judgment — Archtyrant Empowered", "isa.10.1", "isa.34.17"),
    ("Restoration — Servant Restores", "isa.35.1", "isa.59.21"),
    ("Salvation — Millennial Inheritance", "isa.60.1", "isa.66.24"),
]

# 2-Part: Curses (Isa 1-39) → Blessings (Isa 40-66)
TWO_PART_CURSES_BLESSINGS = [
    ("Covenant Curses — Isa 1-39", "isa.1.1", "isa.39.8"),
    ("Covenant Blessings — Isa 40-66", "isa.40.1", "isa.66.24"),
]

# 3 Tests
THREE_TESTS = [
    ("Test One — Archtyrant's Allegiance", "isa.1.1", "isa.38.22"),
    ("Test Two — Babylon's Idols", "isa.39.1", "isa.48.22"),
    ("Test Three — Ecclesiastical Persecution", "isa.49.1", "isa.66.24"),
]

# Servant-Tyrant Parallelism: 21 antithetical verses (Isa 14 ↔ Isa 52-53)
SERVANT_TYRANT_PARALLEL = [
    ("isa.14.4", "isa.52.13", "King of Babylon taunted → King of Zion exalted"),
    ("isa.14.5", "isa.52.14", "Scepter of rulers broken → Servant marred appearance"),
    ("isa.14.6", "isa.52.15", "Rage ruling nations → Sprinkling nations"),
    ("isa.14.7", "isa.53.1", "Earth at rest → Who believed report"),
    ("isa.14.8", "isa.53.2", "Cypresses rejoice → No form nor majesty"),
    ("isa.14.9", "isa.53.3", "Sheol stirred → Despised and rejected"),
    ("isa.14.10", "isa.53.4", "Made weak like us → Bore our griefs"),
    ("isa.14.11", "isa.53.5", "Pomp brought to Sheol → Wounded for transgressions"),
    ("isa.14.12", "isa.53.6", "Son of dawn fallen → All like sheep astray"),
    ("isa.14.13", "isa.53.7", "Ascend to heaven → Led as lamb to slaughter"),
    ("isa.14.14", "isa.53.8", "Like Most High → Cut off from land"),
    ("isa.14.15", "isa.53.9", "Cast to the Pit → Grave with wicked"),
    ("isa.14.16", "isa.53.10", "Astonished beholders → It pleased Jehovah"),
    ("isa.14.17", "isa.53.11", "Made world wilderness → See travail, satisfied"),
    ("isa.14.18", "isa.53.12", "Kings in glory → Portion with great"),
]


# ─── 10. CHAOS MOTIFS ───
# Terms Isaiah uses as chaos/de-creation motifs (from Ancient Types page #8)
CHAOS_MOTIF_KEYWORDS = [
    ("dust", "עפר", "keeps low/powerless"),
    ("chaff", "מץ", "driven by wind"),
    ("stubble", "קש", "consumed by fire"),
    ("mire", "טיט", "sunk in degradation"),
    ("clay", "חמר", "molded and cast away"),
    ("dross", "סיג", "impurities smelted out"),
    ("refuse", "נערת", "thrown away as worthless"),
    ("smoke", "עשן", "vanishing pollution"),
    ("wind", "רוח", "powerless scattering"),
    ("tempest", "סער", "violent dissipation"),
    ("hail", "ברד", "divine judgment"),
    ("darkness", "חשך", "deprivation of light/truth"),
]


# ─── 11. PSEUDONYM TWIN-PAIRS ───
# The same term can refer to EITHER the servant or the tyrant depending on context
# Each pair: (name, servant_verses, tyrant_verses)
PSEUDONYM_PAIRS = [
    ("Hand", "isa.11.11,isa.49.22,isa.51.16", "isa.5.25,isa.10.5,isa.47.6"),
    ("Ensign", "isa.11.10,isa.49.22,isa.62.10", "isa.5.26,isa.13.2"),
    ("Rod", "isa.11.4", "isa.9.4,isa.10.5,isa.10.15"),
    ("Staff", "isa.10.26,isa.30.32", "isa.9.4,isa.10.5,isa.10.15"),
    ("Mouth", "isa.1.20,isa.11.4,isa.49.2", "isa.5.14,isa.37.29"),
    ("Voice", "isa.40.3,isa.40.6,isa.58.1", "isa.13.2,isa.33.3"),
    ("Sword", "isa.27.1,isa.31.8,isa.41.2", "isa.1.20,isa.34.5,isa.66.16"),
    ("Fire", "isa.10.16,isa.10.17,isa.30.30", "isa.1.7,isa.9.18,isa.47.14"),
    ("Light/Darkness", "isa.42.6,isa.49.6,isa.9.2", "isa.5.20,isa.42.7,isa.42.16"),
    ("Sea/River", "isa.11.15", "isa.5.30,isa.8.7,isa.8.8"),
    ("Hail", "isa.30.30", "isa.28.17,isa.32.19"),
    ("Breath/Wind", "isa.11.4", "isa.30.28,isa.33.11"),
    ("Arm", "isa.30.30,isa.40.10,isa.51.5", "isa.33.2"),
    ("Anger/Wrath", "—", "isa.10.5,isa.10.25,isa.63.3"),
]


# ─── 7. DSS PARAGRAPH MARKERS (1QIsa) ───
# The Dead Sea Scroll of Isaiah uses petuchah (open) and setumah (closed)
# paragraph breaks that indicate structural divisions in the text
DSS_SECTIONS = [
    # (start, end, division_type, significance)
    ("isa.1.1", "isa.1.31", "petuchah", "Opening prophecy — Israel's apostasy"),
    ("isa.2.1", "isa.4.6", "setumah", "Zion's exaltation and judgment"),
    ("isa.5.1", "isa.5.30", "petuchah", "Song of the vineyard"),
    ("isa.6.1", "isa.6.13", "petuchah", "Isaiah's call"),
    ("isa.7.1", "isa.8.22", "petuchah", "Ahaz and Assyria"),
    ("isa.9.1", "isa.10.34", "setumah", "Messiah and Assyrian judgment"),
    ("isa.11.1", "isa.12.6", "petuchah", "Branch of Jesse"),
    ("isa.13.1", "isa.14.32", "petuchah", "Burden of Babylon"),
    ("isa.15.1", "isa.16.14", "petuchah", "Burden of Moab"),
    ("isa.17.1", "isa.18.7", "setumah", "Burden of Damascus/Ethiopia"),
    ("isa.19.1", "isa.20.6", "petuchah", "Burden of Egypt"),
    ("isa.24.1", "isa.27.13", "petuchah", "World desolation and restoration"),
    ("isa.28.1", "isa.33.24", "petuchah", "Woe oracles and Zion's peace"),
    ("isa.34.1", "isa.35.10", "petuchah", "Edom's judgment and Zion's redemption"),
    ("isa.36.1", "isa.39.8", "petuchah", "Hezekiah and Assyria"),
    ("isa.40.1", "isa.48.22", "petuchah", "Comfort and deliverance"),
    ("isa.49.1", "isa.55.13", "petuchah", "Servant's mission and salvation"),
    ("isa.56.1", "isa.59.21", "petuchah", "Salvation delayed by sin"),
    ("isa.60.1", "isa.62.12", "setumah", "Zion's coming glory"),
    ("isa.63.1", "isa.66.24", "petuchah", "Jehovah's vengeance and millennial kingdom"),
]


# ─── GENERATORS ───

def seed_day_of_jehovah(conn):
    """Seed the two Days of Jehovah as structural markers."""
    batch = []
    count = 0
    
    for day_type, day_data in [("midpoint", DAY_OF_JEHOVAH_MIDPOINT), ("final", DAY_OF_JEHOVAH_FINAL)]:
        # Add connection from first marker to last marker
        batch.append((
            day_data["markers"][0], day_data["markers"][-1],
            "chronological", "prophetic_timeline", f"day_of_jehovah_{day_type}",
            0.7, 0.65, "algorithm",
            f'{{"day_type": "{day_type}", "label": "{day_data["label"]}", "scholar": "Avraham Gileadi"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  1. Day of Jehovah: {count} markers")
    return count


def seed_three_threats(conn):
    """Seed three escalating threat patterns."""
    batch = []
    count = 0
    
    for threat in THREATS:
        t = threat["type"]
        # Connect start → climax → end
        batch.append((
            threat["start"], threat["climax"],
            "structural", "keyword_linking", f"{t.lower().replace(' ', '_')}",
            0.6, 0.6, "algorithm",
            f'{{"threat": "{t}", "description": "{threat["description"]}", "scholar": "Avraham Gileadi"}}'
        ))
        batch.append((
            threat["climax"], threat["end"],
            "structural", "keyword_linking", f"{t.lower().replace(' ', '_')}",
            0.6, 0.6, "algorithm",
            f'{{"threat": "{t}", "description": "{threat["description"]}", "scholar": "Avraham Gileadi"}}'
        ))
        count += 2
        
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  2. Three Threats: {count} connections")
    return count


def seed_curses_blessings(conn):
    """Seed covenant curse→blessing reversal pairs."""
    batch = []
    count = 0
    
    for c_start, c_end, b_start, b_end, theme in CURSES_BLESSINGS:
        batch.append((
            c_start, b_start,
            "structural", "chiastic", "curses_to_blessings",
            0.5, 0.55, "algorithm",
            f'{{"curse": "{c_start}–{c_end}", "blessing": "{b_start}–{b_end}", "theme": "{theme}", "scholar": "Avraham Gileadi"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  3. Curses↔Blessings: {count} covenant reversal pairs")
    return count


def seed_destruction_deliverance(conn):
    """Seed destruction→deliverance antithetical pairs."""
    batch = []
    count = 0
    
    for d_start, d_end, del_start, del_end, theme in DESTRUCTION_DELIVERANCE:
        batch.append((
            d_start, del_start,
            "structural", "chiastic", "destruction_to_deliverance",
            0.5, 0.55, "algorithm",
            f'{{"destruction": "{d_start}–{d_end}", "deliverance": "{del_start}–{del_end}", "theme": "{theme}", "scholar": "Avraham Gileadi"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  4. Destruction↔Deliverance: {count} antithetical pairs")
    return count


def seed_tabernacle_ladder(conn):
    """Seed tabernacle elements as types of spiritual levels."""
    batch = []
    count = 0
    
    for element, level_desc, exodus_ref, meaning in TABERNACLE_LADDER:
        batch.append((
            exodus_ref, "isa.6.1",
            "symbolic", "temple_symbol", "tabernacle_ladder",
            0.6, 0.5, "algorithm",
            f'{{"element": "{element}", "level": "{level_desc}", "meaning": "{meaning}", "scholar": "Avraham Gileadi"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  5. Tabernacle as Ladder: {count} type connections")
    return count


def seed_cyclical_types(conn):
    """Seed past events as types of future (end-time) events."""
    batch = []
    count = 0
    
    for past_s, past_e, future_s, future_e, desc in CYCLICAL_TYPES:
        batch.append((
            past_s, future_s,
            "symbolic", "event_type", "cyclical_history",
            0.6, 0.55, "algorithm",
            f'{{"past_type": "{past_s}–{past_e}", "future_antitype": "{future_s}–{future_e}", "description": "{desc}", "scholar": "Avraham Gileadi"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  6. Cyclical History: {count} type→antitype pairs")
    return count


def seed_dss_markers(conn):
    """Seed Dead Sea Scroll paragraph markers as structural divisions."""
    batch = []
    count = 0
    
    for start, end, div_type, significance in DSS_SECTIONS:
        batch.append((
            start, end,
            "structural", "seam", f"dss_{div_type}",
            0.4, 0.5, "algorithm",
            f'{{"dss_division": "{div_type}", "significance": "{significance}", "source": "1QIsa", "scholar": "Avraham Gileadi"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  7. DSS Markers: {count} structural divisions")
    return count


# ─── 8. ZION IDEOLOGY — 40 Mini-Patterns ───
# The 3-part Zion ideology pattern: destruction → intercession → deliverance
# From Giliadi's "Key Features" page #5 and "Layered Structures" page #5
ZION_IDEOLOGY_SEEDS = [
    ("isa.1.1", "isa.1.31", "isa.37.1", "isa.37.38", "Zion's judgment and Hezekiah's intercession"),
    ("isa.2.1", "isa.2.22", "isa.4.1", "isa.4.6", "Pride humbled → Zion's branch exalted"),
    ("isa.5.1", "isa.5.30", "isa.12.1", "isa.12.6", "Vineyard wasted → Salvation song"),
    ("isa.9.1", "isa.10.34", "isa.11.1", "isa.12.6", "Assyria's rod → Rod of Jesse"),
    ("isa.13.1", "isa.14.23", "isa.14.24", "isa.14.32", "Babylon destroyed → Zion established"),
    ("isa.28.1", "isa.29.24", "isa.30.1", "isa.33.24", "Ephraim's woe → Zion's peace"),
    ("isa.34.1", "isa.34.17", "isa.35.1", "isa.35.10", "Edom desolated → Wilderness blooms"),
    ("isa.36.1", "isa.38.22", "isa.39.1", "isa.39.8", "Assyria besieges → Hezekiah saved"),
    ("isa.40.1", "isa.40.11", "isa.40.12", "isa.40.31", "Comfort my people → God's incomparability"),
    ("isa.47.1", "isa.47.15", "isa.52.1", "isa.52.15", "Babylon humbled → Zion awakes"),
    ("isa.59.1", "isa.59.21", "isa.60.1", "isa.62.12", "Sin separates → Redeemer comes to Zion"),
    ("isa.63.1", "isa.64.12", "isa.65.1", "isa.66.24", "Jehovah's vengeance → New creation"),
]


def seed_zion_ideology(conn):
    """Seed 40+ Zion ideology patterns of destruction→intercession→deliverance."""
    batch = []
    count = 0
    for d_start, d_end, i_start, i_end, desc in ZION_IDEOLOGY_SEEDS:
        batch.append((
            d_start, i_start,
            "structural", "chiastic", "zion_ideology",
            0.5, 0.5, "algorithm",
            f'{{"destruction": "{d_start}–{d_end}", "intercession": "{i_start}–{i_end}", "description": "{desc}", "pattern": "Zion_Ideology"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    if batch:
        _batch_insert(conn, batch)
    print(f"  8. Zion Ideology: {count} patterns")
    return count


# ─── 9. FAIRYTALE ARCHETYPES ───
# Isaiah's end-time scenario resembles fairytale patterns (bride/groom, hero/villain)
FAIRYTALE_ARCHETYPES = [
    ("isa.62.1", "isa.62.12", "isa.54.1", "isa.54.17", "Bride Zion and bridegroom Jehovah"),
    ("isa.61.1", "isa.61.11", "isa.63.1", "isa.63.6", "Hero servant → Villain archtyrant"),
    ("isa.14.12", "isa.14.20", "isa.52.13", "isa.53.12", "Ogre (King of Babylon) → Prince (King of Zion)"),
    ("isa.47.1", "isa.47.15", "isa.54.1", "isa.54.17", "Witch (Harlot) → Princess (Virgin Zion)"),
]


def seed_fairytale_archetypes(conn):
    """Seed fairytale archetype connections."""
    batch = []
    count = 0
    for villain, hero, rescue, restoration, desc in FAIRYTALE_ARCHETYPES:
        batch.append((
            villain, hero,
            "symbolic", "shared_symbol", "fairytale_archetype",
            0.4, 0.4, "algorithm",
            f'{{"villain": "{villain}", "hero": "{hero}", "description": "{desc}"}}'
        ))
        count += 1
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    if batch:
        _batch_insert(conn, batch)
    print(f"  9. Fairytale Archetypes: {count} patterns")
    return count


# ─── 10. STRUCTURAL OVERLAYS ───

def seed_structural_overlays(conn):
    """Seed 3-part, 4-part, 2-part, and 3-tests structural markers."""
    batch = []
    total = 0
    
    # 3-part structure
    for label, start, end in THREE_PART:
        batch.append((
            start, end,
            "structural", "seam", "three_part_structure",
            0.5, 0.6, "algorithm",
            f'{{"structure": "Trouble→Exile→Homecoming", "section": "{label}", "scholar": "Avraham Gileadi"}}'
        ))
        total += 1
    
    # 4-part structure
    for label, start, end in FOUR_PART:
        batch.append((
            start, end,
            "structural", "seam", "four_part_ajrs",
            0.5, 0.6, "algorithm",
            f'{{"structure": "AJRS Cycle", "section": "{label}", "scholar": "Avraham Gileadi"}}'
        ))
        total += 1
    
    # 2-part curses/blessings
    for label, start, end in TWO_PART_CURSES_BLESSINGS:
        batch.append((
            start, end,
            "structural", "seam", "two_part_curses_blessings",
            0.5, 0.6, "algorithm",
            f'{{"structure": "Curses→Blessings", "section": "{label}", "scholar": "Avraham Gileadi"}}'
        ))
        total += 1
    
    # 3 tests
    for label, start, end in THREE_TESTS:
        batch.append((
            start, end,
            "structural", "seam", "three_tests",
            0.5, 0.6, "algorithm",
            f'{{"structure": "Three Tests", "section": "{label}", "scholar": "Avraham Gileadi"}}'
        ))
        total += 1
    
    # Servant-Tyrant parallel verses
    for src, dst, desc in SERVANT_TYRANT_PARALLEL:
        batch.append((
            src, dst,
            "structural", "chiastic", "servant_tyrant_parallel",
            0.6, 0.65, "algorithm",
            f'{{"parallel": "21 antithetical verses", "description": "{desc}", "scholar": "Avraham Gileadi"}}'
        ))
        total += 1
    
    if batch:
        _batch_insert(conn, batch)
    print(f"  10. Structural Overlays: {total} markers")
    return total


# ─── 11. CHAOS MOTIFS ───

def seed_chaos_motifs(conn):
    """Seed chaos motif keywords as structural de-creation patterns."""
    batch = []
    count = 0
    
    for motif, heb, meaning in CHAOS_MOTIF_KEYWORDS:
        # Find verses in Isaiah with this motif
        if motif == "darkness":
            rows = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = 'isa' AND (g.lemma LIKE ? OR g.word_hebrew LIKE ?)
                LIMIT 15
            """, (f"%2822%", f"%{heb}%")).fetchall()
        elif motif == "hail":
            rows = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = 'isa' AND (g.lemma LIKE ? OR g.word_hebrew LIKE ?)
                LIMIT 15
            """, (f"%1259%", f"%{heb}%")).fetchall()
        else:
            rows = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = 'isa' AND g.word_hebrew LIKE ?
                LIMIT 15
            """, (f"%{heb}%",)).fetchall()
        
        if len(rows) < 2:
            continue
        
        verse_ids = [r["verse_id"] for r in rows]
        hub = verse_ids[0]
        for v in verse_ids[1:]:
            batch.append((
                hub, v,
                "linguistic", "same_lemma", "chaos_motif",
                0.4, 0.4, "algorithm",
                f'{{"motif": "{motif}", "hebrew": "{heb}", "meaning": "{meaning}", "type": "de-creation"}}'
            ))
            count += 1
            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []
    
    if batch:
        _batch_insert(conn, batch)
    print(f"  11. Chaos Motifs: {count} connections across {len(CHAOS_MOTIF_KEYWORDS)} motifs")
    return count


def run(conn, book_ids=None):
    """Run all Isaiah advanced techniques."""
    total = 0
    # Clear previous runs
    for subtype in ["day_of_jehovah_midpoint", "day_of_jehovah_final",
                     "threat_one", "threat_two", "threat_three",
                     "curses_to_blessings", "destruction_to_deliverance",
                     "tabernacle_ladder", "cyclical_history", 
                     "dss_petuchah", "dss_setumah",
                     "zion_ideology", "fairytale_archetype",
                     "three_part_structure", "four_part_ajrs",
                     "two_part_curses_blessings", "three_tests",
                     "servant_tyrant_parallel", "chaos_motif"]:
        conn.execute("DELETE FROM connections WHERE subtype=?", (subtype,))
    conn.commit()
    
    total += seed_day_of_jehovah(conn)
    total += seed_three_threats(conn)
    total += seed_curses_blessings(conn)
    total += seed_destruction_deliverance(conn)
    total += seed_tabernacle_ladder(conn)
    total += seed_cyclical_types(conn)
    total += seed_dss_markers(conn)
    total += seed_zion_ideology(conn)
    total += seed_fairytale_archetypes(conn)
    total += seed_structural_overlays(conn)
    total += seed_chaos_motifs(conn)
    print(f"  Total Isaiah advanced connections: {total}")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
