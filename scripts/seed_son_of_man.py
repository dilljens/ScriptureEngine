#!/usr/bin/env python3
"""Seed Abraham 3 / Daniel 7 / Son of Man connections.

Tracks the distinction between 'Son of Man' (Jehovah/Jesus) and
'one LIKE unto the Son of Man' (a being who appears in His likeness).

Interpretive framework (LDS):
  - abraham.3.27: "one answered LIKE UNTO the Son of Man" — the responder
    is distinct from the Son of Man Himself, appearing in His likeness
  - dan.7.13: "one LIKE a son of man" — same comparative construction
  - gen.1.26: "Let us make man in OUR image, after OUR likeness" — Adam
    made in the form/likeness of God

Scholarly connections (Sod layer, Barker/Orlov):
  - The human-like form on the divine throne (ezek.1.26)
  - The Angel of YHWH who appears in human form
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import init_db, add_connection


# ─── Connections ───
# Each entry: (source, target, layer, type_name, subtype, strength, confidence, discovered_by, metadata)

CONNECTIONS = [
    # ── 1. Abraham 3:27 ↔ Daniel 7:13 — the comparative "like" construction ──
    {
        "source": "abraham.3.27", "target": "dan.7.13",
        "layer": "interpretive", "type_name": "latter_day_saint_reading",
        "subtype": "latter_day_saint",
        "strength": 0.65, "confidence": 0.5, "discovered_by": "algorithm",
        "metadata": {
            "tradition": "latter_day_saint",
            "note": "Both abraham.3.27 and dan.7.13 use the comparative 'like' (kaf prefix) — 'like unto the Son of Man' / 'like a son of man' — describing a being who appears in the form/likeness of the Son of Man but is a distinct personage from the Son Himself",
            "type": "interpretive_tradition",
            "label": "LDS: The comparative 'like' distinguishes the premortal responder from the Son of Man",
        },
    },
    # ── 2. Abraham 3:27 ↔ Genesis 1:26 — the image/likeness connection ──
    {
        "source": "abraham.3.27", "target": "gen.1.26",
        "layer": "interpretive", "type_name": "latter_day_saint_reading",
        "subtype": "latter_day_saint",
        "strength": 0.6, "confidence": 0.45, "discovered_by": "algorithm",
        "metadata": {
            "tradition": "latter_day_saint",
            "note": "Adam was made in the 'image' and 'likeness' of God (gen.1.26). The responder in abraham.3.27 is described as 'like unto the Son of Man' — the same comparative construction suggests the responder is one who bears the image/likeness of the Son (Adam or one of the noble and great ones)",
            "type": "interpretive_tradition",
            "label": "LDS: The one 'like unto the Son of Man' bears His image as Adam was made in God's image",
        },
    },
    # ── 3. Abraham 3:24 ↔ Abraham 3:27 — the two "like" statements ──
    {
        "source": "abraham.3.24", "target": "abraham.3.27",
        "layer": "structural", "type_name": "keyword_linking",
        "subtype": "like_comparative",
        "strength": 0.7, "confidence": 0.55, "discovered_by": "algorithm",
        "metadata": {
            "note": "Two comparative 'like' statements frame the premortal council: 'like unto God' (Jehovah, abraham.3.24) and 'like unto the Son of Man' (the first responder, abraham.3.27). The pattern distinguishes three beings: the one like God, the one like the Son of Man, and the adversary",
            "type": "structural_pattern",
            "label": "Structural: Two 'like' statements distinguish the divine beings in the premortal council",
        },
    },
    # ── 4. Daniel 7:13 ↔ Genesis 1:26 — the human form on the throne ──
    {
        "source": "dan.7.13", "target": "gen.1.26",
        "layer": "sod", "type_name": "angelomorphic",
        "subtype": "human_form_throne",
        "strength": 0.5, "confidence": 0.4, "discovered_by": "algorithm",
        "metadata": {
            "scholar": "Margaret Barker / Andrei Orlov",
            "note": "The 'one like a son of man' in Daniel 7:13 receives dominion and approaches the Ancient of Days. Genesis 1:26-28 describes Adam made in God's image receiving dominion. Both use the human-form-as-divine-mediator pattern — the one like a son of man as the heavenly counterpart to Adam",
            "source": "Temple Theology / The Enoch-Metatron Tradition",
            "tag": "barker_temple",
        },
    },
    # ── 6. Abraham 3:27 ↔ Moses 4:1 — premortal council parallel ──
    {
        "source": "abraham.3.27", "target": "moses.4.1",
        "layer": "interpretive", "type_name": "latter_day_saint_reading",
        "subtype": "latter_day_saint",
        "strength": 0.7, "confidence": 0.6, "discovered_by": "algorithm",
        "metadata": {
            "tradition": "latter_day_saint",
            "note": "Moses 4:1-4 describes the same premortal council: 'I will send the first' echoes Abraham 3:27's 'I will send the first.' The responder who is 'like unto the Son of Man' in Abraham corresponds to the one who says 'Here am I, send me' in the Moses account",
            "type": "interpretive_tradition",
            "label": "LDS: Abraham 3 and Moses 4 both describe the premortal council with the first responder",
        },
    },
    # ── 6. Daniel 7:13 ↔ Psalm 8:4 — the two "son of man" usages contrasted ──
    {
        "source": "dan.7.13", "target": "psa.8.4",
        "layer": "sod", "type_name": "divine_ascent",
        "subtype": "son_of_man_contrast",
        "strength": 0.55, "confidence": 0.45, "discovered_by": "algorithm",
        "metadata": {
            "scholar": "Richard Bauckham",
            "note": "Psalm 8:4 asks 'What is man (enosh) and the son of man (ben adam) that thou visitest him?' — generic humanity. Daniel 7:13 uses 'like a son of man' (k'var enash) — a divine being in human form. The contrast between mortal 'son of man' and the heavenly 'one like a son of man' reveals the distinction",
            "source": "Jesus and the God of Israel",
            "tag": "bauckham_christology",
        },
    },
    # ── 7. Abraham 3:27 ↔ Abraham 3.22-23 — the noble and great ones ──
    {
        "source": "abraham.3.27", "target": "abraham.3.22",
        "layer": "interpretive", "type_name": "latter_day_saint_reading",
        "subtype": "latter_day_saint",
        "strength": 0.6, "confidence": 0.5, "discovered_by": "algorithm",
        "metadata": {
            "tradition": "latter_day_saint",
            "note": "The responder 'like unto the Son of Man' comes from among the 'noble and great ones' (abraham.3.22-23) whom God saw and chose before the world was. This places the responder among the premortal spirits, distinct from the Son of Man who is 'like unto God' (abraham.3.24)",
            "type": "interpretive_tradition",
            "label": "LDS: The responder is one of the noble and great ones, distinct from Jehovah",
        },
    },
    # ── 8. Daniel 7:13 ↔ Ezekiel 1:26 — the merkabah tradition ──
    {
        "source": "dan.7.13", "target": "ezek.1.26",
        "layer": "sod", "type_name": "merkabah",
        "subtype": "human_form_throne",
        "strength": 0.65, "confidence": 0.55, "discovered_by": "algorithm",
        "metadata": {
            "scholar": "Andrei Orlov",
            "note": "Ezekiel 1:26 describes 'a likeness like the appearance of a MAN (adam) above upon the throne' — this is the same heavenly human-like being as Daniel's 'one like a son of man.' Both use the comparative kaf (like) to describe a divine being who appears in human form on or near the divine throne",
            "source": "The Enoch-Metatron Tradition",
            "tag": "orlov_merkabah",
        },
    },
]


def run(conn=None):
    """Seed all Abraham 3 / Daniel 7 / Son of Man connections."""
    if conn is None:
        conn = init_db()

    count = 0
    for c in CONNECTIONS:
        try:
            add_connection(
                conn,
                c["source"], c["target"],
                layer=c["layer"],
                type_name=c["type_name"],
                subtype=c["subtype"],
                strength=c["strength"],
                confidence=c["confidence"],
                discovered_by=c["discovered_by"],
                metadata=c["metadata"],
            )
            count += 1
        except Exception as e:
            print(f"  Error adding {c['source']} → {c['target']}: {e}")

    conn.commit()
    print(f"Seeded {count} Son of Man / Abraham 3 / Daniel 7 connections (8 total)")
    return count


if __name__ == "__main__":
    print("╔═══════════════════════════════════════╗")
    print("║  Son of Man — Abraham 3 / Daniel 7    ║")
    print("╚═══════════════════════════════════════╝")
    run()
