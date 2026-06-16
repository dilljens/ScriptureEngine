#!/usr/bin/env python3
"""Seed Avraham Gileadi's patterns from his Isaiah Explained website.

Includes:
1. Seven-part antithetical structure (domino pairs across Isaiah)
2. A-J-R-S domino chronologies (Apostasy-Judgment-Restoration-Salvation cycles)
3. ~70 metaphorical pseudonyms/keywords with verse references
4. Trouble-Homecoming three-part structure
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection
from lib.connections import pardes


# === 1. GILEADI'S SEVEN-PART ANTITHETICAL STRUCTURE ===
# Seven pairs of themes that form overlapping domino chains
# Each pair connects first-half chapters to second-half chapters

SEVEN_PART_DOMINO = [
    # (theme_name, first_half_start, first_half_end, second_half_start, second_half_end)
    ("Ruin & Rebirth", "isa.1.1", "isa.5.30", "isa.34.1", "isa.35.10"),
    ("Rebellion & Compliance", "isa.6.1", "isa.8.22", "isa.36.1", "isa.40.31"),
    ("Punishment & Deliverance", "isa.9.1", "isa.12.6", "isa.41.1", "isa.46.13"),
    ("Humiliation & Exaltation", "isa.13.1", "isa.23.18", "isa.47.1", "isa.47.15"),
    ("Suffering & Salvation", "isa.24.1", "isa.27.13", "isa.48.1", "isa.54.17"),
    ("Disloyalty & Loyalty", "isa.28.1", "isa.31.9", "isa.55.1", "isa.59.21"),
    ("Disinheritance & Inheritance", "isa.32.1", "isa.33.24", "isa.60.1", "isa.66.24"),
]

# === 2. A-J-R-S DOMINO CYCLE ===
# Apostasy → Judgment → Restoration → Salvation
# Each cycle connects to the next forming overlapping domino chains
# Giliadi describes this as a pattern that repeats at multiple scales

AJRS_CYCLES = [
    # (cycle_name, apostasy_verse, judgment_verse, restoration_verse, salvation_verse)
    # Major cycles across Isaiah
    ("macro_cycle_1", "isa.1.1", "isa.10.1", "isa.35.1", "isa.39.1"),
    ("macro_cycle_2", "isa.39.1", "isa.47.1", "isa.54.1", "isa.55.1"),
    ("macro_cycle_3", "isa.48.1", "isa.59.1", "isa.61.1", "isa.66.24"),
    
    # The domino pattern: each cycle's salvation connects to next cycle's apostasy
    # This forms the ABC / BCD / CDE overlapping chain
    # A (Apostasy) → B (Judgment) → C (Restoration) → D (Salvation)
    # Then D (Salvation) becomes A (Apostasy) for the next cycle
]

# === 3. TROUBLE-HOMECOMING THREE-PART STRUCTURE ===
TROUBLE_HOMECOMING = [
    ("Rebellion at Home", "isa.1.1", "isa.39.8"),
    ("Exile Abroad", "isa.40.1", "isa.54.17"),
    ("Happy Homecoming", "isa.55.1", "isa.66.24"),
]

# === 4. GILEADI'S KEYWORDS / PSEUDONYMS ===
# From his website: each keyword with its meaning and key verse references
# Format: (keyword, meaning, category, [verse_refs])

KEYWORDS = [
    # Divine names
    ("Salvation", "Jehovah God of Israel — personifies salvation, Savior of His people", "divine",
     ["isa.12.2", "isa.17.10", "isa.25.9", "isa.26.1", "isa.33.2", "isa.33.6",
      "isa.45.8", "isa.45.17", "isa.46.13", "isa.49.6", "isa.51.5", "isa.52.7",
      "isa.52.10", "isa.56.1", "isa.59.11", "isa.59.16", "isa.60.18", "isa.61.10",
      "isa.62.1", "isa.62.11", "isa.63.5"]),
    
    ("Rock (1)", "Jehovah God of Israel — rock of his people's salvation, stronghold and sanctuary", "divine",
     ["isa.8.14", "isa.17.10", "isa.26.4", "isa.30.29", "isa.44.8", "isa.48.21", "isa.51.1"]),
    
    ("Faithfulness", "Jehovah God of Israel — exemplifies faithfulness to his covenants", "divine",
     ["isa.11.5", "isa.16.5", "isa.25.1", "isa.33.6", "isa.38.18"]),
    
    ("Lamb", "Jehovah God of Israel — as sacrificial lamb during his earthly ministry", "divine",
     ["isa.53.7"]),
    
    ("Light (1)", "Jehovah God of Israel — the greater light that lights the earth at his coming", "divine",
     ["isa.60.19", "isa.60.20"]),
    
    # Servant pseudonyms
    ("Righteousness", "Jehovah's end-time servant — personifies righteousness, keeps God's law in apostasy", "servant",
     ["isa.1.21", "isa.1.26", "isa.1.27", "isa.5.16", "isa.9.7", "isa.10.22",
      "isa.11.4", "isa.11.5", "isa.16.5", "isa.26.9", "isa.26.10", "isa.28.17",
      "isa.32.1", "isa.32.16", "isa.32.17", "isa.33.5", "isa.41.2", "isa.42.21",
      "isa.45.8", "isa.45.19", "isa.45.23", "isa.46.12", "isa.46.13", "isa.48.1",
      "isa.48.18", "isa.51.1", "isa.51.5", "isa.51.6", "isa.51.8", "isa.54.14",
      "isa.56.1", "isa.58.2", "isa.58.8", "isa.59.4", "isa.59.9", "isa.59.14",
      "isa.59.16", "isa.59.17", "isa.60.17", "isa.61.3", "isa.61.10", "isa.61.11",
      "isa.62.1", "isa.62.2", "isa.63.1", "isa.64.5"]),
    
    ("Arm (2)", "Jehovah's end-time servant — arm of righteousness", "servant",
     ["isa.30.30", "isa.40.10", "isa.40.11", "isa.48.14", "isa.51.5", "isa.51.9",
      "isa.52.10", "isa.53.1", "isa.59.16", "isa.62.8", "isa.63.5", "isa.63.12"]),
    
    ("Hand (1)", "Jehovah's end-time servant — hand of deliverance", "servant",
     ["isa.1.25", "isa.5.12", "isa.11.11", "isa.11.14", "isa.11.15", "isa.14.26",
      "isa.14.27", "isa.19.25", "isa.25.10", "isa.26.11", "isa.29.23", "isa.34.17",
      "isa.41.20", "isa.43.13", "isa.45.9", "isa.45.11", "isa.45.12", "isa.48.13",
      "isa.49.2", "isa.49.22", "isa.50.2", "isa.51.16", "isa.51.22", "isa.53.10",
      "isa.59.1", "isa.60.21", "isa.62.3", "isa.64.8", "isa.65.2", "isa.66.2", "isa.66.14"]),
    
    ("Light (2)", "Jehovah's end-time servant — light to the nations", "servant",
     ["isa.2.5", "isa.5.20", "isa.9.2", "isa.10.17", "isa.42.6", "isa.42.16",
      "isa.45.7", "isa.49.6", "isa.58.8", "isa.58.10", "isa.59.9", "isa.60.1",
      "isa.60.3", "isa.62.1"]),
    
    ("Covenant (2)", "Jehovah's end-time servant — personifies and mediates the covenant", "servant",
     ["isa.42.6", "isa.49.8", "isa.54.10", "isa.55.3", "isa.56.4", "isa.56.6", "isa.59.21", "isa.61.8"]),
    
    ("Ensign (1)", "Jehovah's end-time servant — rallies a remnant", "servant",
     ["isa.11.10", "isa.11.12", "isa.18.3", "isa.30.17", "isa.31.9", "isa.49.22", "isa.62.10"]),
    
    ("Mouth (1)", "Jehovah's end-time servant — Jehovah's mouthpiece", "servant",
     ["isa.1.20", "isa.11.4", "isa.30.2", "isa.34.16", "isa.40.5", "isa.45.23",
      "isa.48.3", "isa.49.2", "isa.51.16", "isa.55.11", "isa.58.14", "isa.59.21", "isa.62.2"]),
    
    ("Voice (1)", "Jehovah's end-time servant — Jehovah's voice", "servant",
     ["isa.24.14", "isa.28.23", "isa.29.4", "isa.30.19", "isa.30.30", "isa.30.31",
      "isa.32.9", "isa.40.3", "isa.40.6", "isa.40.9", "isa.48.20", "isa.50.10",
      "isa.51.3", "isa.52.8", "isa.58.1", "isa.58.4", "isa.66.6"]),
    
    ("Sword (1)", "Jehovah's end-time servant — sword against Assyria/Babylon", "servant",
     ["isa.27.1", "isa.31.8", "isa.37.7", "isa.41.2", "isa.49.2"]),
    
    ("Rod (1)", "Jehovah's end-time servant — rules the nations", "servant",
     ["isa.11.4"]),
    
    ("Trumpet", "Jehovah's end-time servant — rallies a remnant", "servant",
     ["isa.18.3", "isa.27.13", "isa.58.1"]),
    
    ("Arrow", "Jehovah's end-time servant — secret weapon", "servant",
     ["isa.49.2"]),
    
    ("Bird of prey", "Jehovah's end-time servant — raised up from the east", "servant",
     ["isa.46.11"]),
    
    ("Bow (1)", "Jehovah's end-time servant — against Assyrian alliance", "servant",
     ["isa.41.2"]),
    
    ("Fire (2)", "Jehovah's end-time servant — devours Assyrian alliance", "servant",
     ["isa.10.16", "isa.10.17", "isa.30.30", "isa.31.9"]),
    
    ("Sprig", "Jehovah's end-time servant — descendant of David/Jesse", "servant",
     ["isa.11.10"]),
    
    ("Zeal", "Jehovah's end-time servant — exemplifies Jehovah's zeal", "servant",
     ["isa.9.7", "isa.26.11", "isa.37.32", "isa.63.15"]),
    
    # Archtyrant (King of Assyria/Babylon) pseudonyms
    ("Anger", "End-time king of Assyria/Babylon — personifies Jehovah's anger", "tyrant",
     ["isa.5.25", "isa.9.12", "isa.9.17", "isa.9.21", "isa.10.4", "isa.10.5",
      "isa.10.25", "isa.12.1", "isa.13.3", "isa.13.9", "isa.13.13", "isa.14.6",
      "isa.27.4", "isa.42.25", "isa.54.9", "isa.63.3", "isa.63.6", "isa.64.5", "isa.66.15"]),
    
    ("Rod (2)", "End-time king of Assyria/Babylon — rod of punishment", "tyrant",
     ["isa.9.4", "isa.10.5", "isa.10.15", "isa.10.24", "isa.14.5", "isa.30.31"]),
    
    ("Hand (2)", "End-time king of Assyria/Babylon — hand of punishment", "tyrant",
     ["isa.5.12", "isa.5.25", "isa.9.12", "isa.9.17", "isa.9.21", "isa.10.4",
      "isa.10.5", "isa.13.2", "isa.14.26", "isa.14.27", "isa.19.16", "isa.19.25",
      "isa.23.11", "isa.25.10", "isa.26.11", "isa.28.2", "isa.29.23", "isa.31.3",
      "isa.36.15", "isa.36.18", "isa.36.19", "isa.36.20", "isa.37.10", "isa.37.20",
      "isa.38.6", "isa.40.2", "isa.43.13", "isa.45.9", "isa.45.11", "isa.47.6",
      "isa.47.14", "isa.50.11", "isa.51.17", "isa.51.23", "isa.60.21", "isa.64.7",
      "isa.64.8", "isa.65.2"]),
    
    ("Fire (3)", "End-time king of Assyria/Babylon — burns up the wicked", "tyrant",
     ["isa.1.7", "isa.5.24", "isa.9.18", "isa.9.19", "isa.26.11", "isa.30.27",
      "isa.33.11", "isa.33.14", "isa.37.19", "isa.43.2", "isa.47.14", "isa.64.11",
      "isa.66.15", "isa.66.16"]),
    
    ("River", "End-time king of Assyria/Babylon — a power of chaos, like a flood", "tyrant",
     ["isa.7.20", "isa.8.7", "isa.11.15", "isa.27.12"]),
    
    ("Sea (1)", "End-time king of Assyria/Babylon — a power of chaos", "tyrant",
     ["isa.5.30", "isa.10.26", "isa.11.15", "isa.27.1", "isa.43.16", "isa.50.2",
      "isa.51.10", "isa.51.15", "isa.57.20", "isa.60.5", "isa.63.11"]),
    
    ("Darkness", "End-time king of Assyria/Babylon — powers of darkness", "tyrant",
     ["isa.5.20", "isa.9.2", "isa.29.18", "isa.42.7", "isa.42.16", "isa.45.7",
      "isa.45.19", "isa.49.9", "isa.58.10", "isa.59.9", "isa.60.2"]),
    
    ("Wrath", "End-time king of Assyria/Babylon — personifies Jehovah's wrath", "tyrant",
     ["isa.9.19", "isa.10.5", "isa.10.25", "isa.13.5", "isa.13.9", "isa.13.13",
      "isa.14.6", "isa.26.20", "isa.30.27", "isa.48.9", "isa.51.13", "isa.51.17",
      "isa.51.20", "isa.51.22", "isa.59.18", "isa.63.3", "isa.63.5"]),
    
    ("Axe", "End-time king of Assyria/Babylon — instrument of destruction", "tyrant",
     ["isa.10.15"]),
    
    ("Saw", "End-time king of Assyria/Babylon — instrument of cutting down", "tyrant",
     ["isa.10.15"]),
    
    ("Staff (2)", "End-time king of Assyria/Babylon — staff of punishment", "tyrant",
     ["isa.9.4", "isa.10.5", "isa.10.15", "isa.10.24", "isa.14.5"]),
    
    ("Yoke", "End-time king of Assyria/Babylon — imposes bondage", "tyrant",
     ["isa.9.4", "isa.10.27", "isa.14.25", "isa.47.6", "isa.58.6"]),
    
    ("Ensign (2)", "End-time king of Assyria/Babylon — rallies alliance against God's people", "tyrant",
     ["isa.5.26", "isa.13.2"]),
    
    ("Broom", "End-time king of Assyria/Babylon — sweeps earth clean", "tyrant",
     ["isa.14.23"]),
    
    ("Death", "End-time king of Assyria/Babylon — commits global genocide", "tyrant",
     ["isa.9.2", "isa.25.8", "isa.28.15", "isa.28.18", "isa.38.18"]),
    
    ("Deluge", "End-time king of Assyria/Babylon — floods the earth like a new Flood", "tyrant",
     ["isa.28.2"]),
]


def seed_domino_patterns(conn):
    """Create overlapping domino chain connections for Giliadi's A-J-R-S cycles."""
    count = 0
    
    # 1. Seven-part antithetical structure — connect first-half to second-half
    for theme, start1, end1, start2, end2 in SEVEN_PART_DOMINO:
        try:
            add_connection(conn, start1, start2,
                          layer="structural", type_name="chiastic",
                          subtype="giliadi_seven_part",
                          strength=0.8, confidence=0.7,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "theme": theme,
                              "first_half": f"{start1}–{end1}",
                              "second_half": f"{start2}–{end2}",
                              "structure": "seven_part_antithetical",
                          })
            count += 1
        except Exception:
            pass
        
        # Connect end of first half to start of second half (domino transition)
        try:
            add_connection(conn, end1, start2,
                          layer="chronological", type_name="prophetic_timeline",
                          subtype="giliadi_domino",
                          strength=0.7, confidence=0.65,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "theme": theme,
                              "pattern": "ABC_BCD_crossover",
                              "note": f"{theme}: first half concludes → second half begins",
                          })
            count += 1
        except Exception:
            pass
    
    # 2. Domino chain: connect successive themes (crossover)
    # Theme N's second half connects to Theme N+1's first half
    for i in range(len(SEVEN_PART_DOMINO) - 1):
        _, _, end_current, _, start_next = SEVEN_PART_DOMINO[i]
        theme_next = SEVEN_PART_DOMINO[i + 1][0]
        try:
            add_connection(conn, end_current, start_next,
                          layer="chronological", type_name="prophetic_timeline",
                          subtype="giliadi_domino_chain",
                          strength=0.65, confidence=0.6,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "pattern": "ABCD_chain",
                              "note": f"Domino chain: theme {i+1} → theme {i+2} ({theme_next})",
                          })
            count += 1
        except Exception:
            pass
    
    return count


def seed_keyword_connections(conn):
    """Create connections for Gileadi's keywords/pseudonyms.
    
    For each keyword, connects its verse references together,
    showing how the same keyword functions across Isaiah.
    """
    count = 0
    
    for keyword, meaning, category, verses in KEYWORDS:
        if len(verses) < 2:
            continue
        
        # Connect adjacent verse references (domino pattern within the keyword)
        for i in range(len(verses) - 1):
            try:
                add_connection(conn, verses[i], verses[i + 1],
                              layer="symbolic", type_name="shared_symbol",
                              subtype=f"giliadi_{keyword.lower().replace(' ', '_').replace('(','').replace(')','')}",
                              strength=0.65, confidence=0.6,
                              discovered_by="algorithm",
                              metadata={
                                  "scholar": "Avraham Gileadi",
                                  "keyword": keyword,
                                  "meaning": meaning[:100],
                                  "category": category,
                              })
                count += 1
            except Exception:
                pass
    
    return count


def seed_pseudonym_connections(conn):
    """Create connections linking pseudonyms to their referents.
    
    Gileadi identifies three main actors and their pseudonyms.
    This connects the pseudonym occurrences to the main actors.
    """
    # Main actors with key defining verses
    actors = {
        "Jehovah (Salvation)": "isa.12.2",
        "Jehovah's Servant (Righteousness)": "isa.41.2",
        "King of Assyria/Babylon (Anger)": "isa.10.5",
    }
    
    count = 0
    for keyword, meaning, category, verses in KEYWORDS:
        if not verses:
            continue
        
        # Connect each keyword's first occurrence to the defining verse of its category
        if category == "divine":
            hub = "isa.12.2"
        elif category == "servant":
            hub = "isa.41.2"
        elif category == "tyrant":
            hub = "isa.10.5"
        else:
            continue
        
        for v in verses[:3]:  # Limit to first 3 to avoid explosion
            try:
                add_connection(conn, hub, v,
                              layer="symbolic", type_name="name_symbolic",
                              subtype=f"giliadi_pseudonym_{category}",
                              strength=0.7, confidence=0.65,
                              discovered_by="algorithm",
                              metadata={
                                  "scholar": "Avraham Gileadi",
                                  "keyword": keyword,
                                  "meaning": f"{keyword} is a pseudonym for {category}",
                                  "note": f"{meaning[:120]}",
                              })
                count += 1
            except Exception:
                pass
    
    return count


def seed_ajrs_domino(conn):
    """Create the ABC/BCD/ CDE overlapping domino chain from Gileadi's A-J-R-S cycles.
    
    Each cycle is: Apostasy → Judgment → Restoration → Salvation
    The domino effect: each cycle's Salvation leads to the next cycle's Apostasy,
    forming an overlapping chain: A-B-C-D / B-C-D-E / C-D-E-F
    """
    count = 0
    
    # Macro cycles across Isaiah
    cycles = [
        ("cycle_1", ["isa.1.1", "isa.10.1", "isa.35.1", "isa.39.8"]),
        ("cycle_2", ["isa.39.8", "isa.47.1", "isa.55.1", "isa.59.21"]),
        ("cycle_3", ["isa.59.1", "isa.66.1", "isa.66.10", "isa.66.24"]),
    ]
    
    for name, verses in cycles:
        a, j, r, s = verses
        # Apostasy → Judgment
        try:
            add_connection(conn, a, j, layer="chronological", type_name="prophetic_timeline",
                          subtype="ajrs_domino", strength=0.7, confidence=0.65,
                          discovered_by="algorithm",
                          metadata={"scholar": "Avraham Gileadi", "pattern": "A→J (Apostasy→Judgment)", "cycle": name})
            count += 1
        except Exception:
            pass
        
        # Judgment → Restoration
        try:
            add_connection(conn, j, r, layer="chronological", type_name="prophetic_timeline",
                          subtype="ajrs_domino", strength=0.7, confidence=0.65,
                          discovered_by="algorithm",
                          metadata={"scholar": "Avraham Gileadi", "pattern": "J→R (Judgment→Restoration)", "cycle": name})
            count += 1
        except Exception:
            pass
        
        # Restoration → Salvation
        try:
            add_connection(conn, r, s, layer="chronological", type_name="prophetic_timeline",
                          subtype="ajrs_domino", strength=0.7, confidence=0.65,
                          discovered_by="algorithm",
                          metadata={"scholar": "Avraham Gileadi", "pattern": "R→S (Restoration→Salvation)", "cycle": name})
            count += 1
        except Exception:
            pass
    
    # Connect cycles: each cycle's Salvation → next cycle's Apostasy (the domino overlap)
    for i in range(len(cycles) - 1):
        s_this = cycles[i][1][3]  # Salvation of this cycle
        a_next = cycles[i + 1][1][0]  # Apostasy of next cycle
        try:
            add_connection(conn, s_this, a_next,
                          layer="structural", type_name="chiastic",
                          subtype="ajrs_domino_transition",
                          strength=0.6, confidence=0.55,
                          discovered_by="algorithm",
                          metadata={
                              "scholar": "Avraham Gileadi",
                              "pattern": "S→A (Salvation→Apostasy transition)",
                              "note": "Domino overlap: one cycle's salvation becomes the next cycle's preparation for apostasy",
                          })
            count += 1
        except Exception:
            pass
    
    return count


def main():
    conn = get_db()
    
    print("=" * 60)
    print("  AVRAHAM GILEADI — Patterns from Isaiah Explained")
    print("=" * 60)
    
    print("\n--- Seven-Part Antithetical Structure ---", flush=True)
    c = seed_domino_patterns(conn)
    print(f"  {c} domino structure connections", flush=True)
    
    print("\n--- A-J-R-S Domino Cycles ---", flush=True)
    c2 = seed_ajrs_domino(conn)
    print(f"  {c2} AJRS domino connections", flush=True)
    
    print("\n--- Keyword/Pseudonym Connections ---", flush=True)
    c3 = seed_keyword_connections(conn)
    print(f"  {c3} keyword connections", flush=True)
    
    print("\n--- Pseudonym-to-Actor Links ---", flush=True)
    c4 = seed_pseudonym_connections(conn)
    print(f"  {c4} pseudonym links", flush=True)
    
    conn.commit()
    
    total = c + c2 + c3 + c4
    structural = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='structural' AND (type='chiastic' OR type='keyword_linking')").fetchone()["c"]
    symbolic = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='symbolic'").fetchone()["c"]
    
    print(f"\n  Total new connections: {total}")
    print(f"  Structural layer: {structural}")
    print(f"  Symbolic layer: {symbolic}")
    conn.close()


if __name__ == "__main__":
    main()
