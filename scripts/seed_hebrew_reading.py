#!/usr/bin/env python3
"""Seed graded reading progression using Bullard's ETCBC difficulty data.

Research (Bullard, ETCBC 2017) shows Ruth and Jonah are NOT the easiest
texts for beginners — they rank ~450th in vocabulary difficulty. Instead:

Phase 1 - Entry (100+ frequency vocab): Exo 11, 14, 24; Num 36; Dt 5, 6
Phase 2 - Easy (70+ frequency vocab): Gen 47-48; Lev 9, 17; Isa 39; Zec 8
Phase 3 - Intermediate: Gen 1-3, 12, 22; Exo 3, 12, 19-20; 1 Sam 1, 3
Phase 4 - Narrative: Complete books (Joshua, Judges, Samuel, Kings)
Phase 5 - Poetry/Prophets: Psalms, Isaiah, Minor Prophets

Each reading lesson provides:
- Chapter reference + book context
- Key vocabulary preview (top-frequency words found in the chapter)
- Practice items: vocabulary recognition from the chapter
- Links to the passage guide / verse API for actual reading
"""

import json
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"
SCRIPTURE_DB = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"

# Graded reading progression: (id, book, chapter, level, title, key_vocab_glosses)
READING_ENTRIES = [
    # Phase 1: Entry (100+ frequency words)
    ("read_exo11", "exo", 11, 4, "Exodus 11 — The Final Plague",
     "said, LORD, Moses, come, go out, servant, people, land, not, all"),
    ("read_exo14", "exo", 14, 4, "Exodus 14 — The Red Sea Crossing",
     "said, LORD, Moses, Israel, sea, water, go, hand, Egypt, dry"),
    ("read_exo24", "exo", 24, 4, "Exodus 24 — The Covenant Ceremony",
     "Moses, LORD, blood, book, covenant, people, mountain, altar, sacrifice"),
    ("read_num36", "num", 36, 4, "Numbers 36 — Inheritance of Daughters",
     "tribe, inheritance, daughter, marry, land, commanded, LORD, Moses"),
    ("read_deut5", "deu", 5, 4, "Deuteronomy 5 — The Ten Commandments",
     "LORD, God, not, you shall, day, heaven, earth, commandment, keep, remember"),
    ("read_deut6", "deu", 6, 4, "Deuteronomy 6 — The Great Commandment",
     "LORD, God, heart, soul, might, command, teach, sons, house, gate"),
    ("read_deut12", "deu", 12, 4, "Deuteronomy 12 — One Place of Worship",
     "place, worship, offer, sacrifice, eat, rejoice, LORD, choose, tribe"),
    ("read_josh4", "josh", 4, 4, "Joshua 4 — The Twelve Stones",
     "people, cross, Jordan, stone, memorial, sign, hand, LORD, Joshua"),
    ("read_josh23", "josh", 23, 4, "Joshua 23 — Joshua's Farewell",
     "Joshua, old, days, LORD, God, keep, turn, way, nation, land"),

    # Phase 2: Easy (70+ frequency vocab)
    ("read_gen47", "gen", 47, 5, "Genesis 47 — Jacob Before Pharaoh",
     "Joseph, Pharaoh, land, Egypt, father, brothers, dwell, Goshen, bread"),
    ("read_gen48", "gen", 48, 5, "Genesis 48 — Jacob Blesses Ephraim & Manasseh",
     "Israel, Joseph, sons, bless, father, God, angel, seed, land"),
    ("read_lev9", "lev", 9, 5, "Leviticus 9 — The Priestly Ministry Begins",
     "Aaron, altar, sacrifice, sin, burnt, offering, bless, glory, fire, LORD"),
    ("read_lev17", "lev", 17, 5, "Leviticus 17 — The Blood Principle",
     "blood, life, atonement, altar, eat, soul, pour, priest, holy"),
    ("read_isa39", "isa", 39, 5, "Isaiah 39 — Hezekiah's Folly",
     "Hezekiah, Isaiah, king, house, treasure, word, LORD, days, peace, Babylon"),
    ("read_zec8", "zec", 8, 5, "Zechariah 8 — The Future of Jerusalem",
     "LORD, host, Jerusalem, city, truth, peace, people, strong, house, fast"),

    # Phase 3: Core narratives
    ("read_gen1", "gen", 1, 5, "Genesis 1 — The Creation",
     "God, create, heaven, earth, light, day, night, water, good, made"),
    ("read_gen2", "gen", 2, 5, "Genesis 2 — The Garden of Eden",
     "LORD, God, man, garden, tree, river, gold, good, eat, ground"),
    ("read_gen3", "gen", 3, 5, "Genesis 3 — The Fall",
     "serpent, woman, man, eat, tree, know, evil, good, curse, ground, die"),
    ("read_gen12", "gen", 12, 5, "Genesis 12 — The Call of Abram",
     "Abram, LORD, go, land, bless, seed, nation, family, altar, call"),
    ("read_gen22", "gen", 22, 5, "Genesis 22 — The Binding of Isaac",
     "Abraham, Isaac, son, offer, mountain, wood, fire, knife, angel, bless"),
    ("read_exo3", "exo", 3, 5, "Exodus 3 — The Burning Bush",
     "Moses, God, fire, bush, holy, name, people, Egypt, send, I AM"),
    ("read_exo12", "exo", 12, 5, "Exodus 12 — The Passover",
     "Passover, lamb, blood, house, door, eat, bread, night, LORD, Egypt"),
    ("read_exo19", "exo", 19, 5, "Exodus 19 — At Mount Sinai",
     "Sinai, mountain, LORD, thunder, cloud, fire, smoke, trumpet, descend"),
    ("read_exo20", "exo", 20, 5, "Exodus 20 — The Ten Commandments",
     "God, speak, word, commandment, LORD, house, servant, keep, honor, kill"),
    ("read_1sam1", "1sam", 1, 5, "1 Samuel 1 — Hannah's Prayer",
     "Hannah, Elkanah, LORD, pray, weep, vow, son, Samuel, give, house"),
    ("read_1sam3", "1sam", 3, 5, "1 Samuel 3 — The Call of Samuel",
     "Samuel, LORD, call, speak, word, servant, hear, judge, prophet, Eli"),
]


def seed_reading(mem_db, scrip_db):
    conn = sqlite3.connect(str(mem_db))
    scrip = sqlite3.connect(str(scrip_db))

    new_nodes = 0
    new_items = 0

    for rid, book, chapter, level, title, vocab_hint in READING_ENTRIES:
        existing = conn.execute("SELECT id FROM hebrew_practice_items WHERE node_id=? LIMIT 1", (rid,)).fetchone()
        if existing:
            continue

        # Get chapter data from scripture
        verses = scrip.execute(
            "SELECT text_english, text_hebrew FROM verses WHERE book_id=? AND chapter=? AND text_english != '' ORDER BY verse LIMIT 50",
            (book, chapter)
        ).fetchall()

        # Build chapter summary
        n_verses = len(verses)
        full_english = " ".join(v[0] for v in verses if v[0])
        prev_text = full_english[:300] + "..." if len(full_english) > 300 else full_english

        # Chapter explanation
        explanation = f"""Reading Assignment: {title}

This chapter has {n_verses} verses. Read it in your preferred Bible version.

Context: This passage is from the {'entry-level' if level == 4 else 'easy' if level == 5 else 'intermediate'} reading phase.

Key vocabulary to note:
{vocab_hint}

Before reading:
1. Review the key vocabulary above
2. Read the English to understand the narrative flow
3. Read the Hebrew aloud — pay attention to familiar roots and patterns
4. Identify at least 3 words you recognize from vocabulary lessons

After reading:
- Note any words you've seen in vocabulary lessons
- Try to identify verb forms you recognize
- Look for construct chains"""

        content = {
            "node_id": rid,
            "title": title,
            "category": "reading",
            "level": level,
            "explanation": explanation,
            "key_points": [
                f"Chapter: {book}.{chapter} ({n_verses} verses)",
                f"Reading phase: {'Entry' if level == 4 else 'Easy' if level == 5 else 'Intermediate'}",
                f"Key vocabulary: {vocab_hint}",
            ],
            "verse_preview": prev_text,
        }

        # Insert node and lesson
        conn.execute("INSERT OR IGNORE INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, 'reading', ?)",
                     (rid, title, level, f"Read {book}.{chapter} — {n_verses} verses"))
        conn.execute("INSERT OR IGNORE INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)",
                     (rid, json.dumps(content, ensure_ascii=False)))

        # Prerequisite: link to the book-level reading node
        book_map = {"exo": "reading_torah", "num": "reading_torah", "deu": "reading_torah",
                    "josh": "reading_torah", "gen": "reading_genesis",
                    "lev": "reading_torah", "isa": "reading_isaiah",
                    "zec": "reading_isaiah", "1sam": "reading_genesis"}
        prereq = book_map.get(book, "reading_torah")
        conn.execute("INSERT OR IGNORE INTO hebrew_edges (source_id, target_id, edge_type) VALUES (?, ?, 'prerequisite')",
                     (rid, prereq))

        # Practice items
        def add(q, ans, qtype="recall"):
            conn.execute("INSERT OR IGNORE INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty) VALUES (?,?,?,?,?,?)",
                        (rid, qtype, q, "[]", ans, 0.5))
            nonlocal new_items
            new_items += 1

        # 1. Reference recall
        add(f"What is the reference of this reading? (book chapter.verse)", f"{book}.{chapter}.1")

        # 2-4. Key vocabulary recognition from the chapter
        eng_words = [w for w in full_english.split()[:30] if len(w) > 3]
        seen = set()
        for word in eng_words[:5]:
            w = word.strip(".,;:!?()\"'").lower()
            if w and w not in seen and len(w) > 3:
                seen.add(w)
                add(f"In '{title}', match this English word you'll see: '{w}'", w)

        # 5. First verse recall/open
        first_verse_text = verses[0][0][:100] if verses else ""
        if first_verse_text:
            add(f"Open and begin reading {title}. The first verse starts: '{first_verse_text[:50]}...'",
                f"{book}.{chapter}.1")

        # 6. Count check
        add(f"How many verses in {title}?", str(n_verses))

        new_nodes += 1
        if new_nodes % 5 == 0:
            conn.commit()
            print(f"  Progress: {new_nodes}/{len(READING_ENTRIES)}...")

    conn.commit()
    conn.close()
    scrip.close()

    print(f"\n✓ Seeded {new_nodes} graded reading lessons, {new_items} practice items")
    print(f"  Total reading lessons now: {new_nodes}")


if __name__ == "__main__":
    seed_reading(MEM_DB, SCRIPTURE_DB)
