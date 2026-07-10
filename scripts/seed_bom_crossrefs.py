#!/usr/bin/env python3
"""Seed Book of Mormon cross-reference connections from the OT Podcast PDFs."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection

# ─── BOM CROSS-REFERENCES FROM GILIADI'S OT PODCAST PDFs ───
# Each: (ot_source, bom_target, description, strength)
CROSS_REFS = [
    # Joseph's prophecies
    ("gen.49.22", "2ne.3.5", "Joseph's prophecy of a future seer — Joseph Smith", 0.6),
    ("gen.50.25", "2ne.3.7", "Joseph's prophecy of a choice seer", 0.6),
    ("gen.48.19", "3ne.5.21", "Ephraim's birthright — Gentiles gather Israel", 0.6),
    ("gen.48.19", "2ne.10.8", "Kings of Gentiles as nursing fathers", 0.6),
    
    # Exodus / Moses patterns
    ("exo.17.1", "hel.10.4", "Elijah's sealing power → Nephi son of Helaman", 0.6),
    ("exo.3.1", "1ne.17.26", "Moses called → Nephi compares to Moses", 0.6),
    ("exo.14.21", "1ne.4.2", "Red Sea parted → Nephi's faith", 0.6),
    
    # Isaiah connections in BoM
    ("isa.11.1", "2ne.25.19", "Rod of Jesse → Christ's coming", 0.6),
    ("isa.49.22", "1ne.21.22", "Nursing fathers → Gentiles nurture Israel", 0.6),
    ("isa.52.10", "1ne.22.11", "Arm of Jehovah bared", 0.6),
    ("isa.54.2", "ether.13.6", "New Jerusalem in America", 0.6),
    ("isa.60.1", "3ne.20.40", "Zion's glory → Nephite remnant", 0.6),
    ("isa.2.2", "2ne.12.2", "Mountain of the Lord → Temple", 0.6),
    ("isa.29.11", "2ne.27.6", "Sealed book → unsealed by servant", 0.6),
    ("isa.29.14", "2ne.27.26", "Marvelous work → BoM coming forth", 0.6),
    ("isa.11.10", "2ne.21.10", "Root of Jesse → Ensign to nations", 0.6),
    ("isa.11.11", "2ne.21.11", "Second gathering → remnant restored", 0.6),
    
    # Typological patterns
    ("gen.6.1", "3ne.22.9", "Noah's flood → end-time desolation type", 0.6),
    ("gen.19.1", "ether.13.6", "Sodom destroyed → New Jerusalem built", 0.6),
    ("exo.12.21", "mosiah.13.29", "Passover → Christ's atonement type", 0.6),
    ("exo.16.1", "john.6.32", "Manna → Bread of Life (quoted in BoM)", 0.6),
    ("num.21.8", "2ne.25.20", "Brazen serpent → Look to Christ", 0.6),
    ("josh.6.1", "hel.5.50", "Jericho → walls of prison fall", 0.6),
    ("josh.1.1", "1ne.17.31", "Joshua's conquest → Nephi's conquest", 0.6),
    ("judg.6.1", "mosiah.9.17", "Gideon → deliverance from Lamanites", 0.6),
    
    # D&C connections
    ("isa.11.1", "dc.113.1", "Stem of Jesse → queries about Isaiah", 0.6),
    ("isa.11.10", "dc.113.6", "Root of Jesse → descendant of Jesse and Joseph", 0.6),
    ("isa.52.1", "dc.113.7", "Zion's awakening → priesthood power", 0.6),
    ("isa.29.11", "dc.91.1", "Sealed book → Apocrypha", 0.6),
    ("isa.55.1", "dc.55.1", "Come to the waters → call to saints", 0.6),
    ("isa.11.12", "dc.38.33", "Gathering of Israel → latter-day gathering", 0.6),
    ("exo.19.5", "dc.84.33", "Peculiar treasure → priesthood covenant", 0.6),
    ("josh.1.1", "dc.100.1", "Strong and courageous → mission call", 0.6),
    
    # Pearl of Great Price
    ("gen.1.1", "moses.2.1", "Creation account → Moses' vision", 0.6),
    ("gen.2.8", "moses.3.8", "Garden of Eden → Moses' version", 0.6),
    ("exo.6.3", "abraham.1.16", "I am Jehovah → Abraham's vision", 0.7),
    ("gen.15.13", "abraham.2.9", "Abrahamic covenant → PGP version", 0.6),
]


def main():
    conn = get_db()
    print("=" * 60)
    print("  BOOK OF MORMON CROSS-REFERENCES")
    print("=" * 60)
    
    # Clear previous
    conn.execute("DELETE FROM connections WHERE subtype='bom_crossref_typology'")
    conn.commit()
    
    total = 0
    for ot_ref, bom_ref, desc, strength in CROSS_REFS:
        try:
            add_connection(conn, ot_ref, bom_ref,
                          layer="symbolic", type_name="event_type",
                          subtype="bom_crossref_typology",
                          strength=strength, confidence=0.55,
                          discovered_by="algorithm",
                          metadata={
                              "source": "Giliadi OT Podcast PDFs",
                              "crossref_type": "OT_type_to_BoM_antitype",
                              "description": desc,
                          })
            total += 1
        except Exception as e:
            pass
    
    conn.commit()
    print(f"  Seeded {total} cross-reference connections")
    
    # Verify
    total_check = conn.execute("SELECT COUNT(*) as c FROM connections WHERE subtype='bom_crossref_typology'").fetchone()["c"]
    print(f"  Total in DB: {total_check}")
    conn.close()


if __name__ == "__main__":
    main()
