"""Isaiah Pseudonym Twin-Pair System — Giliadi's keyword methodology.

The same Hebrew term can refer to EITHER the end-time servant (God's
righteous deliverer) OR the end-time tyrant (king of Assyria/Babylon)
depending on context. Giliadi identified ~20 such twin-pairs.

This generator creates connections linking each pseudonym occurrence
to its respective actor hub verse, with context from parallel lines
to disambiguate servant vs tyrant usage.
"""

from lib.db import add_connection

# ─── PSEUDONYM ACTOR HUBS ───
SERVANT_HUB = "isa.42.1"       # Defining verse: "Behold my servant"
TYRANT_HUB = "isa.10.5"        # Defining verse: "Hail the Assyrian, rod of my anger"

# ─── TWIN PAIR PSEUDONYMS ───
# Each pair: (name, servant_strongs, tyrant_strongs, servant_verses, tyrant_verses)
TWIN_PAIRS = [
    ("Hand", ["3027", "3225"], ["3027", "3225"], 
     ["isa.11.11", "isa.49.22", "isa.51.16", "isa.62.8"],
     ["isa.5.25", "isa.10.5", "isa.47.6", "isa.64.7"]),
    ("Ensign", ["5251"], ["5251"],
     ["isa.11.10", "isa.11.12", "isa.49.22", "isa.62.10"],
     ["isa.5.26", "isa.13.2"]),
    ("Rod", ["7626"], ["7626", "4294"],
     ["isa.11.4"],
     ["isa.9.4", "isa.10.5", "isa.10.15", "isa.10.24", "isa.14.5"]),
    ("Staff", ["4938", "7626"], ["4938", "4294"],
     ["isa.10.26", "isa.30.32"],
     ["isa.9.4", "isa.10.5", "isa.10.15", "isa.14.5"]),
    ("Sword", ["2719"], ["2719"],
     ["isa.27.1", "isa.31.8", "isa.41.2"],
     ["isa.1.20", "isa.34.5", "isa.34.6", "isa.66.16"]),
    ("Fire", ["784"], ["784"],
     ["isa.10.16", "isa.10.17", "isa.30.30", "isa.31.9"],
     ["isa.1.7", "isa.9.18", "isa.9.19", "isa.47.14"]),
    ("Mouth", ["6310"], ["6310"],
     ["isa.1.20", "isa.11.4", "isa.49.2"],
     ["isa.5.14", "isa.37.29"]),
    ("Voice", ["6963"], ["6963"],
     ["isa.40.3", "isa.40.6", "isa.58.1"],
     ["isa.13.2", "isa.33.3"]),
    ("Light", ["216", "215"], ["2822"],  # Light = servant, Darkness = tyrant
     ["isa.42.6", "isa.49.6", "isa.9.2", "isa.60.1"],
     ["isa.5.20", "isa.42.7", "isa.42.16", "isa.59.9"]),
    ("Sea/River", ["3220", "5104"], ["3220", "5104"],
     ["isa.11.15", "isa.27.1"],
     ["isa.5.30", "isa.8.7", "isa.8.8", "isa.51.15"]),
    ("Arm", ["2220"], ["2220"],
     ["isa.30.30", "isa.40.10", "isa.40.11", "isa.51.5", "isa.52.10", "isa.59.16"],
     ["isa.33.2"]),
    ("Breath/Wind", ["7307", "5397"], ["7307"],
     ["isa.11.4"],
     ["isa.30.28", "isa.33.11"]),
]

# ─── SINGLE-ACTOR PSEUDONYMS ───
# Unique to either servant or tyrant (no twin)
SINGLE_PSEUDONYMS = {
    "servant": [
        ("Arrow", "2671", ["isa.49.2"]),
        ("Bird of prey", "5861", ["isa.46.11"]),
        ("Trumpet", "7782", ["isa.18.3", "isa.27.13", "isa.58.1"]),
        ("Righteousness", "6664", ["isa.41.2", "isa.46.12", "isa.46.13", "isa.51.5"]),
        ("Covenant", "1285", ["isa.42.6", "isa.49.8"]),
        ("Stone", "68", ["isa.28.16"]),
        ("Whip", "7752", ["isa.10.26"]),
        ("Zeal", "7068", ["isa.9.7", "isa.26.11", "isa.37.32", "isa.63.15"]),
    ],
    "tyrant": [
        ("Anger", "639", ["isa.10.5", "isa.10.25", "isa.63.3"]),
        ("Wrath", "5678", ["isa.10.5", "isa.10.25", "isa.13.5", "isa.13.9"]),
        ("Darkness", "2822", ["isa.5.20", "isa.42.7", "isa.42.16", "isa.59.9"]),
        ("Death", "4194", ["isa.25.8", "isa.28.15", "isa.28.18"]),
        ("Yoke", "5923", ["isa.9.4", "isa.10.27", "isa.14.25", "isa.47.6"]),
        ("Broom", "2892", ["isa.14.23"]),
        ("Axe", "1631", ["isa.10.15"]),
        ("Saw", "4050", ["isa.10.15"]),
        ("River (flood)", "5104", ["isa.8.7", "isa.28.2", "isa.28.15", "isa.28.18"]),
        ("Razor", "8593", ["isa.7.20"]),
    ],
}


def run(conn, book_ids=None):
    """Create pseudonym twin-pair connections in Isaiah.
    
    For each pseudonym, links occurrences to their actor hub
    (servant or tyrant), with the context from the parallel line
    determining which actor.
    """
    total = 0
    batch = []
    
    # Clear previous runs
    conn.execute("DELETE FROM connections WHERE subtype IN ('pseudonym_servant', 'pseudonym_tyrant', 'pseudonym_single')")
    conn.commit()
    
    # ── Twin Pairs ──
    for name, servant_ss, tyrant_ss, s_verses, t_verses in TWIN_PAIRS:
        # Servant connections
        for v in s_verses:
            batch.append((
                SERVANT_HUB, v,
                "symbolic", "name_symbolic", "pseudonym_servant",
                0.6, 0.6, "algorithm",
                f'{{"pseudonym": "{name}", "actor": "servant", "hub_defining": "{SERVANT_HUB}"}}'
            ))
            total += 1
        
        # Tyrant connections
        for v in t_verses:
            batch.append((
                TYRANT_HUB, v,
                "symbolic", "name_symbolic", "pseudonym_tyrant",
                0.6, 0.6, "algorithm",
                f'{{"pseudonym": "{name}", "actor": "tyrant", "hub_defining": "{TYRANT_HUB}"}}'
            ))
            total += 1
        
        if len(batch) >= 200:
            _batch_insert(conn, batch)
            batch = []
    
    # ── Single-Actor Pseudonyms ──
    for actor, pseudonyms in SINGLE_PSEUDONYMS.items():
        hub = SERVANT_HUB if actor == "servant" else TYRANT_HUB
        for name, strongs, verses in pseudonyms:
            for v in verses:
                batch.append((
                    hub, v,
                    "symbolic", "name_symbolic", "pseudonym_single",
                    0.55, 0.55, "algorithm",
                    f'{{"pseudonym": "{name}", "actor": "{actor}", "hub_defining": "{hub}"}}'
                ))
                total += 1
                
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Pseudonym system: {total} connections ({len(TWIN_PAIRS)} twin-pairs, {sum(len(v) for v in SINGLE_PSEUDONYMS.values())} single-actor)")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
