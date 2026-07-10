#!/usr/bin/env python3
"""Seed semantic domains — algorithmic lemma classification from English glosses.

Uses lemma_gloss table (3770 entries with Strong's → English) to classify
lemmas into semantic domains via keyword matching. No LLM needed — pure
keyword intersection with curated domain vocabularies.

Domains are seeded from well-known Hebrew lexical fields. Each domain
has a set of English gloss keywords that, if matched in a lemma's gloss,
classify that lemma into the domain.

Usage:
  python3 scripts/seed_domains.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# ─── Domain Definitions (keyword → semantic field) ───
# Each domain: name, description, and set of English keywords/patterns
# that identify lemmas belonging to that domain.

DOMAINS = [
    {
        "name": "sacrifice",
        "description": "Sacrificial terms — offerings, altars, blood rites, atonement",
        "keywords": [
            "sacrifice", "offering", "altar", "oblation", "victim",
            "burnt", "incense", "atonement", "expiate", "propitiation",
            "slain", "slay", "kill", "butcher", "blood",
        ],
    },
    {
        "name": "temple",
        "description": "Temple/tabernacle architecture and furnishings",
        "keywords": [
            "temple", "tabernacle", "sanctuary", "holy place", "holy of holies",
            "veil", "curtain", "ark", "cherub", "mercy seat", "candlestick",
            "lampstand", "shewbread", "laver", "court", "gate",
            "pillar", "altar of", "censer", "basin", "ephod",
        ],
    },
    {
        "name": "covenant",
        "description": "Covenant and treaty terms — binding agreements, promises, oaths",
        "keywords": [
            "covenant", "oath", "swear", "vow", "promise", "pledge",
            "treaty", "league", "bond", "testament", "confirm",
            "establish", "everlasting",
        ],
    },
    {
        "name": "judgment",
        "description": "Judicial and judgment terms — law, justice, courtroom",
        "keywords": [
            "judgment", "judge", "justice", "righteous", "law", "statute",
            "commandment", "ordinance", "testimony", "decree",
            "verdict", "sentence", "condemn", "acquit", "plead",
            "controversy", "rebuke", "chastise",
        ],
    },
    {
        "name": "kingship",
        "description": "Royal and governmental terms — kings, thrones, dominion",
        "keywords": [
            "king", "queen", "throne", "royal", "kingdom", "dominion",
            "reign", "rule", "ruler", "prince", "princess", "noble",
            "sceptre", "crown", "diadem", "majesty", "sovereign",
            "governor", "deputy", "satrap",
        ],
    },
    {
        "name": "warfare",
        "description": "Military and combat terms — weapons, battles, armies",
        "keywords": [
            "war", "battle", "army", "host", "soldier", "captain",
            "weapon", "sword", "spear", "shield", "bow", "arrow",
            "armour", "helmet", "breastplate", "chariot", "fortress",
            "siege", "camp", "encamp",
        ],
    },
    {
        "name": "agriculture",
        "description": "Farming, harvest, and pastoral terms",
        "keywords": [
            "plow", "plough", "sow", "seed", "harvest", "reap",
            "grain", "wheat", "barley", "vine", "vineyard", "field",
            "flock", "shepherd", "herd", "cattle", "ox", "sheep",
            "goat", "pasture", "tillage", "fruit", "thresh",
        ],
    },
    {
        "name": "wisdom",
        "description": "Wisdom and knowledge terms — understanding, instruction",
        "keywords": [
            "wisdom", "wise", "understanding", "knowledge", "instruction",
            "discretion", "prudence", "counsel", "discern",
            "teach", "learn", "skilful", "cunning", "intelligent",
        ],
    },
    {
        "name": "prophecy",
        "description": "Prophetic and visionary terms — revelation, seers, oracles",
        "keywords": [
            "prophet", "prophecy", "prophesy", "seer", "vision",
            "oracle", "burden", "reveal", "revelation", "divine",
            "soothsayer", "enchanter", "dreamer", "interpret",
        ],
    },
    {
        "name": "praise",
        "description": "Worship and praise terms — song, music, adoration",
        "keywords": [
            "praise", "worship", "sing", "song", "psalm", "hymn",
            "thanksgiving", "give thanks", "bless", "blessing",
            "magnify", "exalt", "glorify", "honour", "rejoice",
            "shout", "trumpet", "harp", "lyre", "timbrel", "dance",
        ],
    },
    {
        "name": "repentance",
        "description": "Repentance and restoration terms — turning, forgiveness, renewal",
        "keywords": [
            "repent", "repentance", "turn", "return", "restore",
            "forgive", "forgiveness", "pardon", "blot out", "cleanse",
            "purify", "wash", "renew", "revive", "convert",
        ],
    },
    {
        "name": "creation",
        "description": "Creation and cosmic order terms — heavens, earth, foundations",
        "keywords": [
            "create", "creation", "maker", "foundation", "establish",
            "heaven", "earth", "firmament", "deep", "waters",
            "light", "darkness", "day", "night", "sun", "moon",
            "star", "constellation",
        ],
    },
    {
        "name": "exile",
        "description": "Exile, captivity, and diaspora terms",
        "keywords": [
            "exile", "captivity", "captive", "capture", "carry away",
            "banish", "disperse", "scatter", "remnant", "return",
            "restore", "gather",
        ],
    },
    {
        "name": "tribulation",
        "description": "Suffering, affliction, and distress terms",
        "keywords": [
            "afflict", "affliction", "trouble", "distress", "anguish",
            "sorrow", "grief", "mourn", "lament", "weep", "tears",
            "suffering", "persecute", "oppress", "tribulation",
            "calamity", "adversity", "misery",
        ],
    },
    {
        "name": "redemption",
        "description": "Redemption and deliverance terms — saving, ransoming, freeing",
        "keywords": [
            "redeem", "redemption", "ransom", "deliver", "deliverance",
            "save", "salvation", "rescue", "free", "liberty",
            "release", "loose",
        ],
    },
]


def seed_domains(conn):
    """Populate semantic_domains and domain_members tables."""
    # Get lemma_gloss data for English keyword matching
    gloss_rows = conn.execute("""
        SELECT lemma, english_gloss FROM lemma_gloss
        WHERE lemma != '' AND english_gloss != ''
    """).fetchall()
    
    # Build lemma → set of domain names
    lemma_domains = {}  # lemma → set of domain names
    
    for r in gloss_rows:
        lemma = r["lemma"]
        gloss = r["english_gloss"].lower()
        
        for domain in DOMAINS:
            name = domain["name"]
            for keyword in domain["keywords"]:
                if keyword in gloss:
                    if lemma not in lemma_domains:
                        lemma_domains[lemma] = set()
                    lemma_domains[lemma].add(name)
                    break  # one keyword match per domain is enough
    
    # Insert domains
    domain_ids = {}
    for domain in DOMAINS:
        conn.execute(
            "INSERT OR IGNORE INTO semantic_domains (name, description, ai_generated) VALUES (?, ?, 0)",
            (domain["name"], domain["description"])
        )
    
    # Get domain IDs
    rows = conn.execute("SELECT id, name FROM semantic_domains").fetchall()
    for r in rows:
        domain_ids[r["name"]] = r["id"]
    
    # Insert domain members
    count = 0
    batch = []
    for lemma, domains in lemma_domains.items():
        for domain_name in domains:
            did = domain_ids.get(domain_name)
            if did:
                batch.append((did, lemma))
                count += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    conn.commit()
    return count


def _batch_insert(conn, batch):
    conn.executemany(
        "INSERT OR IGNORE INTO domain_members (domain_id, lemma) VALUES (?, ?)",
        batch
    )


def main():
    conn = get_db()
    print("=" * 60)
    print("  Seeding Semantic Domains (Algorithmic)")
    print("=" * 60)
    print()
    
    print(f"  Domains defined: {len(DOMAINS)}")
    total = seed_domains(conn)
    print(f"  Domain members assigned: {total}")
    
    # Stats
    rows = conn.execute("""
        SELECT sd.name, COUNT(dm.lemma) as c
        FROM semantic_domains sd
        LEFT JOIN domain_members dm ON dm.domain_id = sd.id
        GROUP BY sd.id
        ORDER BY c DESC
    """).fetchall()
    print()
    for r in rows:
        print(f"    {r['name']}: {r['c']} lemmas")
    
    conn.close()


if __name__ == "__main__":
    main()
