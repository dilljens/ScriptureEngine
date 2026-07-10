#!/usr/bin/env python3
"""Seed interpretive disagreements from existing connection data + well-known disagreements.

Uses rule-based detection to find contradictory interpretations across traditions
for the same verse, then supplements with curated well-known disagreements.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import get_db


def find_disagreements(conn):
    """Find potential disagreements by looking at the same verse
    with different interpretive connections from different traditions."""
    rows = conn.execute("""
        SELECT c1.source_verse as verse, 
               c1.subtype as tradition_a, 
               c2.subtype as tradition_b,
               c1.target_verse as target_a,
               c2.target_verse as target_b
        FROM connections c1
        JOIN connections c2 ON c1.source_verse = c2.source_verse 
            AND c1.layer = 'interpretive' 
            AND c2.layer = 'interpretive'
            AND c1.id < c2.id
            AND c1.subtype != c2.subtype
        WHERE c1.target_verse != c2.target_verse
        LIMIT 100
    """).fetchall()
    return rows


def seed_known_disagreements(conn):
    """Seed well-known interpretive disagreements."""
    known = [
        # Psalm 110:1 — Rabbinic vs Christian
        ("psa.110.1", "jewish", "christian",
         "Jewish tradition reads 'my Lord' as Abraham or David; Christian tradition reads it as the Messiah (Jesus)"),
        # Isaiah 7:14 — Jewish vs Christian
        ("isa.7.14", "jewish", "christian",
         "Jewish tradition reads 'almah' as a young woman; Christian tradition reads 'parthenos' as a virgin and sees Messianic prophecy"),
        # Genesis 1 — Creation days: literal vs figurative
        ("gen.1.1", "jewish", "critical_scholarship",
         "Traditional reading sees 6 literal days; critical scholarship sees poetic/liturgical framework"),
        # Exodus 20 — Ten Commandments numbering
        ("exo.20.1", "jewish", "reformation",
         "Jewish tradition counts 'I am the LORD' as the first word; Reformation tradition counts it as preamble and splits differently"),
        # Song of Solomon — Allegory vs Literal
        ("song.1.1", "jewish", "critical_scholarship",
         "Traditional reading (Jewish + Christian) sees allegory for God-Israel or Christ-Church; critical scholarship sees erotic poetry"),
        # Jonah — Historical vs Parable
        ("jonah.1.1", "faith", "critical_scholarship",
         "Faith traditions read Jonah as historical; critical scholarship reads it as allegorical midrash"),
        # Genesis 6 — Sons of God: angels vs Sethites
        ("gen.6.2", "jewish", "patristic",
         "Early Jewish tradition interprets 'sons of God' as fallen angels; later Jewish and some patristic reading interprets as Sethites"),
        # Romans 9-11 — Israel and the Church
        ("rom.9.6", "reformation", "patristic",
         "Reformation tradition sees Israel replaced by Church (supersessionism); patristic reading varies"),
        # Revelation 20 — Millennial views
        ("rev.20.1", "patristic", "reformation",
         "Patristic tradition largely amillennial; Reformation tradition includes premillennial and amillennial views"),
        # Matthew 16:18 — Rock: Peter vs his confession
        ("matt.16.18", "patristic", "reformation",
         "Catholic tradition identifies 'rock' as Peter; Reformation tradition identifies it as Peter's confession or Christ"),
        # Mark 16 — Longer ending authenticity
        ("mark.16.9", "critical_scholarship", "faith",
         "Critical scholarship regards verses 9-20 as later addition; faith traditions accept them as canonical"),
        # Genesis 22 — Binding of Isaac
        ("gen.22.2", "jewish", "christian",
         "Jewish tradition reads Akedah as test of Abraham; Christian tradition reads as type of Christ's sacrifice"),
        # Exodus 3:14 — I AM
        ("exo.3.14", "jewish", "christian",
         "Jewish tradition reads 'Ehyeh Asher Ehyeh' as God's refusal to name; Christian tradition reads it as identification with Jesus's 'I AM' sayings"),
        # Deuteronomy 18:15 — Prophet like Moses
        ("deu.18.15", "jewish", "christian",
         "Jewish tradition sees a succession of prophets; Christian tradition identifies this as Messianic prophecy of Jesus"),
        # Psalm 22 — Suffering psalm
        ("psa.22.1", "jewish", "christian",
         "Jewish tradition reads as David's personal lament; Christian tradition reads as Messianic prophecy of crucifixion"),
        # Isaiah 53 — Suffering Servant
        ("isa.53.3", "jewish", "christian",
         "Jewish tradition identifies Servant as Israel; Christian tradition identifies as Jesus Messiah"),
        # Daniel 9 — Seventy Weeks
        ("dan.9.24", "jewish", "christian",
         "Jewish tradition sees prophecy fulfilled in Maccabean period; Christian tradition sees Messianic timeline to Jesus"),
        # Hosea 11:1 — Out of Egypt
        ("hos.11.1", "jewish", "christian",
         "Jewish tradition reads as historical Exodus; Christian tradition reads as Messianic prophecy of Jesus (Matthew 2:15)"),
        # Proverbs 8 — Wisdom personified
        ("prov.8.22", "jewish", "christian",
         "Jewish tradition reads Wisdom as a poetic personification; Christian tradition identifies as pre-existent Christ (Logos)"),
        # Zechariah 12:10 — Pierced One
        ("zech.12.10", "jewish", "christian",
         "Jewish tradition reads as mourning over a national leader; Christian tradition reads as looking upon Christ crucified"),
    ]
    for verse, trad_a, trad_b, desc in known:
        conn.execute(
            """INSERT INTO interpretive_disagreements 
               (verse_id, tradition_a, tradition_b, description)
               VALUES (?, ?, ?, ?)""",
            (verse, trad_a, trad_b, desc)
        )
    print(f"Seeded {len(known)} known disagreements")


def seed_disagreements():
    conn = get_db()

    # Ensure table exists
    from lib.db import SCHEMA_SQL
    if "interpretive_disagreements" not in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall():
        # Table creation is handled by init_db; just ensure it exists
        pass

    # Clean any existing
    conn.execute("DELETE FROM interpretive_disagreements")

    # Find candidate disagreements from connection graph
    candidates = find_disagreements(conn)
    print(f"Found {len(candidates)} candidate disagreements from connection graph")

    seeds = []
    for c in candidates:
        verse = c["verse"]
        trad_a = c["tradition_a"]
        trad_b = c["tradition_b"]
        target_a = c["target_a"]
        target_b = c["target_b"]

        description = f"Tradition '{trad_a}' connects {verse} to {target_a}, while tradition '{trad_b}' connects it to {target_b}"

        conn.execute(
            """INSERT INTO interpretive_disagreements 
               (verse_id, tradition_a, tradition_b, description)
               VALUES (?, ?, ?, ?)""",
            (verse, trad_a, trad_b, description)
        )
        seeds.append({"verse": verse, "traditions": f"{trad_a} vs {trad_b}"})

    # Seed well-known disagreements
    seed_known_disagreements(conn)

    conn.commit()

    # Count total
    total = conn.execute("SELECT COUNT(*) FROM interpretive_disagreements").fetchone()[0]
    conn.close()
    print(f"Total disagreements seeded: {total}")
    return {"auto_detected": len(seeds), "total": total}


if __name__ == "__main__":
    seed_disagreements()
