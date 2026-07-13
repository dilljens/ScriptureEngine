#!/usr/bin/env python3
"""Add production practice items to Hebrew teaching system.

Generates typing, transliteration, and free-recall practice items
for all 102 Hebrew nodes, complementing the existing recognition items.

Usage:
    python3 scripts/seed_hebrew_production.py
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB = sys.argv[1] if len(sys.argv) > 1 else "data/memorize.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

nodes = cur.execute("SELECT id, title, level, category, description FROM hebrew_nodes ORDER BY level, id").fetchall()

added = 0

for nid, title, level, category, desc in nodes:
    glyph = title.split("(")[1].split(")")[0] if "(" in title else ""
    clean = title.split("(")[0].strip()

    # Typing practice: type the letter/word
    if category == "consonant":
        cur.execute("""INSERT OR IGNORE INTO hebrew_practice_items
            (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
            VALUES (?, 'typing', ?, '[]', ?, 0.5, ?)""",
            (nid, f"Type the letter: {clean}", glyph,
             f"Type the Hebrew character for {clean} ({glyph})"))
        added += 1

    elif category == "vowel":
        cur.execute("""INSERT OR IGNORE INTO hebrew_practice_items
            (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
            VALUES (?, 'typing', ?, '[]', ?, 0.6, ?)""",
            (nid, f"Type the vowel symbol for {clean}", glyph,
             f"The vowel {clean} is written as {glyph} under the consonant"))
        added += 1

    elif category == "verb":
        cur.execute("""INSERT OR IGNORE INTO hebrew_practice_items
            (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
            VALUES (?, 'recall', ?, '[]', ?, 0.7, ?)""",
            (nid, f"Describe the function of the {clean} binyan", clean,
             f"The {clean} binyan: {desc[:100]}"))
        added += 1

    # Transliteration practice for all categories
    if "(" in title:
        cur.execute("""INSERT OR IGNORE INTO hebrew_practice_items
            (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
            VALUES (?, 'transliteration', ?, '[]', ?, 0.5, ?)""",
            (nid, f"How is {glyph} ({clean}) transliterated?", clean,
             f"The Hebrew character {glyph} is transliterated as part of {clean}"))
        added += 1

    # Free recall for key concepts
    if level <= 3:
        cur.execute("""INSERT OR IGNORE INTO hebrew_practice_items
            (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
            VALUES (?, 'recall', ?, '[]', ?, 0.4, ?)""",
            (nid, f"What is {clean} in Hebrew?", clean, desc[:100]))
        added += 1

conn.commit()
conn.close()
print(f"Added {added} production practice items")
