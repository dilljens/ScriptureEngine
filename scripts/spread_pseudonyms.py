#!/usr/bin/env python3
"""Spread Gileadi's pseudonyms across the entire canon.

Gileadi's 70+ keywords from Isaiah apply to the full canon.
This searches for each keyword in ALL books and creates connections
between all occurrences, showing how the same divine/servant/tyrant
language appears throughout scripture.
"""

import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection
from lib.gematria import extract_consonants


# Gileadi's keywords with their English search terms across the canon
PSEUDONYM_SEARCH = [
    # Divine — Jehovah
    ("Salvation", "salvation", "divine", "isa.12.2"),
    ("Righteousness (divine)", "righteousness", "divine", "psa.11.7"),
    ("Faithfulness", "faithfulness", "divine", "psa.89.1"),
    ("Light (divine)", "light", "divine", "psa.27.1"),
    
    # Servant — Righteousness personified
    ("Righteousness (servant)", "righteousness", "servant", "isa.41.2"),
    ("Arm of Lord", "arm of the lord", "servant", "isa.53.1"),
    ("Hand of Lord", "hand of the lord", "servant", "1kgs.18.46"),
    ("Servant of Lord", "servant of the lord", "servant", "isa.42.1"),
    ("Anointed", "anointed", "servant", "psa.2.2"),
    ("Chosen", "chosen", "servant", "isa.42.1"),
    ("Beloved", "beloved", "servant", "matt.3.17"),
    ("Branch", "branch", "servant", "jer.23.5"),
    ("Shepherd", "shepherd", "servant", "ezek.34.23"),
    ("Redeemer", "redeemer", "servant", "job.19.25"),
    ("Witness", "witness", "servant", "isa.55.4"),
    ("Leader", "leader", "servant", "isa.55.4"),
    ("Stone", "stone", "servant", "psa.118.22"),
    ("Rock (servant)", "rock", "servant", "1cor.10.4"),
    ("Light to nations", "light to the nations", "servant", "isa.49.6"),
    ("Mediator", "mediator", "servant", "1tim.2.5"),
    ("Advocate", "advocate", "servant", "1jn.2.1"),
    ("Deliverer", "deliverer", "servant", "rom.11.26"),
    
    # Tyrant — Assyria/Babylon
    ("Wicked", "wicked", "tyrant", "psa.1.1"),
    ("Pride", "pride", "tyrant", "prov.16.18"),
    ("Oppressor", "oppressor", "tyrant", "psa.72.4"),
    ("Destroyer", "destroyer", "tyrant", "jer.4.7"),
    ("Devil", "devil", "tyrant", "matt.4.1"),
    ("Satan", "satan", "tyrant", "job.1.6"),
    ("Adversary", "adversary", "tyrant", "1pet.5.8"),
    ("Serpent", "serpent", "tyrant", "gen.3.1"),
    ("Dragon", "dragon", "tyrant", "rev.12.3"),
    ("Beast", "beast", "tyrant", "rev.13.1"),
    ("Antichrist", "antichrist", "tyrant", "1jn.2.18"),
    ("Man of sin", "man of sin", "tyrant", "2thes.2.3"),
    ("Son of perdition", "son of perdition", "tyrant", "2thes.2.3"),
    
    # Thematic keywords
    ("Covenant", "covenant", "thematic", "gen.9.11"),
    ("Remnant", "remnant", "thematic", "isa.10.20"),
    ("Zion", "zion", "thematic", "psa.2.6"),
    ("Holy One of Israel", "holy one of israel", "thematic", "isa.1.4"),
    ("Day of the Lord", "day of the lord", "thematic", "joel.2.31"),
]


def main():
    conn = get_db()
    print("=" * 60)
    print("  SPREADING PSEUDONYMS ACROSS THE CANON")
    print("=" * 60)
    
    # Get all verse IDs for quick existence checks
    all_verses = set(r["id"] for r in conn.execute("SELECT id FROM verses").fetchall())
    
    total = 0
    for keyword, search_term, category, seed_verse in PSEUDONYM_SEARCH:
        print(f"  {keyword:25s} ({search_term:20s})...", flush=True)
        
        # Search across ALL books in English text
        rows = conn.execute("""
            SELECT id, book_id, text_english FROM verses
            WHERE text_english LIKE ?
            ORDER BY book_id, chapter, verse
        """, (f"%{search_term}%",)).fetchall()
        
        if len(rows) < 2:
            print(f"    -> Only {len(rows)} occurrence, skipping")
            continue
        
        found_verses = []
        for r in rows:
            if r["id"] in all_verses:
                found_verses.append(r["id"])
        
        if len(found_verses) < 2:
            continue
        
        # Create connections — hub-and-spoke to the first occurrence (the seed or first found)
        hub = seed_verse if seed_verse in found_verses else found_verses[0]
        
        pair_count = 0
        for v in found_verses:
            if v == hub:
                continue
            try:
                add_connection(conn, hub, v,
                              layer="symbolic", type_name="name_symbolic",
                              subtype=f"pseudonym_{category}",
                              strength=0.5, confidence=0.45,
                              discovered_by="algorithm",
                              metadata={
                                  "keyword": keyword,
                                  "search_term": search_term,
                                  "category": category,
                                  "note": f"'{keyword}' as {category} pseudonym connecting {hub} ↔ {v}",
                              })
                pair_count += 1
            except Exception:
                pass
            
            if pair_count % 50 == 0:
                conn.commit()
        
        conn.commit()
        print(f"    -> {pair_count} connections across {len(found_verses)} verses")
        total += pair_count
    
    # Summary
    symbolic_total = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='symbolic'").fetchone()["c"]
    print(f"\n  Total pseudonym spread: {total} connections")
    print(f"  Symbolic layer total: {symbolic_total}")
    conn.close()


if __name__ == "__main__":
    main()
