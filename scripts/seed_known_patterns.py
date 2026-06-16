#!/usr/bin/env python3
"""Seed the known_chiasms database with patterns from Giliadi, Welch, and other scholars."""

import sys
import json
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, add_known_chiasm


def seed():
    conn = get_db()

    # First, clear existing seed data (keep AI-discovered ones)
    conn.execute("DELETE FROM known_chiasms WHERE discovered_by = 'human'")

    patterns = []

    # === GILIADI: Integral Structures ===
    # Giliadi's documented word-count chiasms and integral structures

    # Genesis: the toledot structure forms a chiasm
    patterns.append({
        "scholar": "Giliadi",
        "reference": "Integral Structure of Genesis",
        "book_id": "gen",
        "start_verse": "gen.1.1",
        "end_verse": "gen.50.26",
        "pivot_verse": "gen.25.19",
        "chiasm_type": "integral",
        "confidence": 0.6,
        "notes": "Giliadi sees the entire book of Genesis as structured around the toledot (generations) formula, forming a massive chiasm from creation (1-2) through the patriarchs (12-50). The pivot at Gen 25:19 marks the transition from Abraham narratives to Isaac/Jacob.",
    })

    # Genesis 6-9: Flood narrative chiasm
    patterns.append({
        "scholar": "Giliadi",
        "reference": "Integral Structure of the Flood Narrative",
        "book_id": "gen",
        "start_verse": "gen.6.9",
        "end_verse": "gen.9.29",
        "pivot_verse": "gen.8.1",
        "chiasm_type": "word_count",
        "confidence": 0.8,
        "notes": "The flood narrative forms a classic chiasm: A (6:9-12 corruption), B (6:13-22 building ark), C (7:1-24 entering flood), D (8:1 God remembers), C' (8:2-14 waters recede), B' (8:15-22 exiting ark), A' (9:1-29 covenant). Word counts of corresponding sections are closely matched.",
    })

    # Exodus 1-15: Exodus narrative
    patterns.append({
        "scholar": "Giliadi",
        "reference": "Integral Structure of Exodus",
        "book_id": "exo",
        "start_verse": "exo.1.1",
        "end_verse": "exo.15.21",
        "pivot_verse": "exo.6.2",
        "chiasm_type": "integral",
        "confidence": 0.55,
        "notes": "The first half of Exodus (oppression through Red Sea) forms a chiastic structure with the revelation of God's name at the center.",
    })

    # Isaiah: book-level structure
    patterns.append({
        "scholar": "Giliadi",
        "reference": "Integral Structure of Isaiah",
        "book_id": "isa",
        "start_verse": "isa.1.1",
        "end_verse": "isa.66.24",
        "pivot_verse": "isa.36.1",
        "chiasm_type": "integral",
        "confidence": 0.5,
        "notes": "Giliadi divides Isaiah into two halves (1-35 judgment, 40-66 consolation) around the historical interlude of Hezekiah (36-39). The word counts of corresponding sections in each half show mirror patterns. This is more controversial than the Flood chiasm.",
    })

    # Leviticus: Mary Douglas's chiasm
    patterns.append({
        "scholar": "Giliadi",
        "reference": "Following Mary Douglas, Ring Composition in Leviticus",
        "book_id": "lev",
        "start_verse": "lev.1.1",
        "end_verse": "lev.27.34",
        "pivot_verse": "lev.19.1",
        "chiasm_type": "thematic",
        "confidence": 0.7,
        "notes": "The book of Leviticus forms a ring composition (chiasm) around the Holiness Code (19-26). Section pairs: offerings (1-7) ↔ vows/tithes (27), priesthood (8-10) ↔ blessings/curses (26), purity (11-15) ↔ holy days (23-25), Day of Atonement (16) ↔ laws of holiness (17-22), with chapter 19 (love your neighbor) at the center.",
    })

    # === WELCH: Chiasmus in the Book of Mormon and Bible ===

    # Alma 36 — Welch's most famous discovery
    patterns.append({
        "scholar": "Welch",
        "reference": "Chiasmus in Alma 36 — BYU Studies 1974",
        "book_id": "alma",
        "start_verse": "alma.36.1",
        "end_verse": "alma.36.30",
        "pivot_verse": "alma.36.18",
        "chiasm_type": "word_level",
        "confidence": 0.95,
        "notes": "The classic Book of Mormon chiasm. 20+ parallel elements in mirror order: A (1-3: my son/listen), B (4-5: born of God), C (6-8: pains of hell), D (9-11: remember Jesus), E (12-16: hungering/three days), F (17: Almighty/justice), PIVOT (18: O Jesus/mercy), F' (19-20: justice/mercy), E' (21-22: joy/light), D' (23-25: remember Christ), C' (26-27: pains/deliver), B' (28-29: born of God), A' (30: my son).",
    })

    # Mosiah 5:10-12 — Taking Christ's name
    patterns.append({
        "scholar": "Welch",
        "reference": "Chiasmus in the Book of Mormon",
        "book_id": "mosiah",
        "start_verse": "mosiah.5.10",
        "end_verse": "mosiah.5.12",
        "pivot_verse": "mosiah.5.11",
        "chiasm_type": "word_level",
        "confidence": 0.85,
        "notes": "A compact chiasm about taking Christ's name: A (10: enter covenant), B (10: name of Christ), C (11: remembered), D (11: always remember), C' (11: not forgotten), B' (12: name written), A' (12: depart from Christ).",
    })

    # 1 Nephi 1 — Lehi's vision
    patterns.append({
        "scholar": "Welch",
        "reference": "Chiasmus in the Book of Mormon",
        "book_id": "1ne",
        "start_verse": "1ne.1.1",
        "end_verse": "1ne.1.20",
        "pivot_verse": "1ne.1.10",
        "chiasm_type": "thematic",
        "confidence": 0.7,
        "notes": "First Nephi chapter 1 has chiastic structure: A (1-2: Nephi's introduction), B (3-5: Lehi's family), C (6-7: Lehi prays), D (8-9: pillar of fire), PIVOT (10: book/record), D' (11: God's messengers), C' (12-14: Lehi prophesies), B' (15-19: opposition), A' (20: Nephi's testimony).",
    })

    # 2 Nephi 29 — Book of Mormon and Bible
    patterns.append({
        "scholar": "Welch",
        "reference": "Chiasmus in the Book of Mormon",
        "book_id": "2ne",
        "start_verse": "2ne.29.1",
        "end_verse": "2ne.29.14",
        "pivot_verse": "2ne.29.7",
        "chiasm_type": "word_level",
        "confidence": 0.75,
        "notes": "Chiasm about the gathering of records and the word of God going forth.",
    })

    # New Testament chiasms (Welch)

    # Matthew 1-28 (entire Gospel structure, Nils Lund / Welch)
    patterns.append({
        "scholar": "Welch",
        "reference": "Chiasmus in the New Testament — Nils Lund, elaborated by Welch",
        "book_id": "matt",
        "start_verse": "matt.1.1",
        "end_verse": "matt.28.20",
        "pivot_verse": "matt.13.1",
        "chiasm_type": "thematic",
        "confidence": 0.5,
        "notes": "The entire Gospel of Matthew may have chiastic macrostructure: Infancy (1-4) ↔ Resurrection (28), Sermon (5-7) ↔ Olivet Discourse (24-25), Miracles (8-9) ↔ Parousia (21-23), Mission (10) ↔ Authority (18-20), Rejection (11-12) ↔ Community (14-17), with parables at the center (13). Less consensus than other chiasms.",
    })

    # John 1:1-18 — Prologue
    patterns.append({
        "scholar": "Welch",
        "reference": "Chiasmus in John's Prologue",
        "book_id": "john",
        "start_verse": "john.1.1",
        "end_verse": "john.1.18",
        "pivot_verse": "john.1.9",
        "chiasm_type": "word_level",
        "confidence": 0.8,
        "notes": "The Prologue of John forms an intricate chiasm: A (1-2: Word with God/divine), B (3: creation), C (4-5: light/darkness), D (6-8: John the witness), PIVOT (9: true light comes), D' (10-11: world didn't know), C' (12-13: children of light), B' (14: Word became flesh), A' (15-18: divine glory/only Son).",
    })

    # === CLASSIC OT CHIASMS (Multiple Scholars) ===

    # Amos 1-2: Oracles against nations
    patterns.append({
        "scholar": "Multiple",
        "reference": "Classic chiastic structure, noted by many scholars",
        "book_id": "amos",
        "start_verse": "amos.1.1",
        "end_verse": "amos.2.16",
        "pivot_verse": "amos.2.6",
        "chiasm_type": "word_level",
        "confidence": 0.9,
        "notes": "Seven oracles against nations (Damascus, Gaza, Tyre, Edom, Ammon, Moab, Israel). The first six have identical structure, the seventh (Israel) is the longest and the pivot. This 6+1 pattern is itself chiastic with the judgment on Israel at the center.",
    })

    # Genesis 1 — Days of creation (already in our wiki)
    patterns.append({
        "scholar": "Multiple",
        "reference": "Classic: Days 1-3 (forming) parallel Days 4-6 (filling)",
        "book_id": "gen",
        "start_verse": "gen.1.1",
        "end_verse": "gen.2.3",
        "pivot_verse": "gen.1.1",
        "chiasm_type": "thematic",
        "confidence": 0.9,
        "notes": "The six days of creation form a classic parallel chiasm: Day 1 (light) ↔ Day 4 (luminaries), Day 2 (waters/sky) ↔ Day 5 (fish/birds), Day 3 (land/plants) ↔ Day 6 (animals/humans). The seventh day (rest) is the crown.",
    })

    # === INSERT ALL ===
    count = 0
    for p in patterns:
        try:
            add_known_chiasm(
                conn,
                scholar=p["scholar"],
                book_id=p["book_id"],
                start_verse=p["start_verse"],
                end_verse=p["end_verse"],
                pivot_verse=p["pivot_verse"],
                chiasm_type=p["chiasm_type"],
                layers_json=json.dumps(p.get("layers", [])),
                confidence=p["confidence"],
                notes=p["notes"],
                reference=p.get("reference", ""),
            )
            count += 1
        except Exception as e:
            print(f"  ERROR adding {p['book_id']} {p['start_verse']}-{p['end_verse']}: {e}")

    print(f"Seeded {count} known patterns")

    # Verify
    rows = conn.execute("SELECT COUNT(*) as c FROM known_chiasms").fetchone()
    print(f"Total known_chiasms: {rows['c']}")

    # Show by scholar
    rows = conn.execute("SELECT scholar, COUNT(*) as c FROM known_chiasms GROUP BY scholar ORDER BY c DESC").fetchall()
    for r in rows:
        print(f"  {r['scholar']}: {r['c']}")

    conn.close()


if __name__ == "__main__":
    seed()
