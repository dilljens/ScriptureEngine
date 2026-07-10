#!/usr/bin/env python3
"""Generate 500+ frequency-ranked Hebrew word lessons.

Takes the top N words from the vocabulary frequency data and creates
lesson nodes + practice items in the memorize.db. Each lesson includes:
- Hebrew word with transliteration
- English gloss
- Triconsonantal root
- Verse example from the actual text
- Audio reference (Shmueloff alignment if available)
- Practice items: recognition (MC) → recall (cloze) → production (typing)

Usage:
    python3 scripts/seed_hebrew_vocabulary.py
    python3 scripts/seed_hebrew_vocabulary.py --count 500
    python3 scripts/seed_hebrew_vocabulary.py --db data/memorize.db
"""

import argparse
import json
import os
import random
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
DB_PATH = BASE / "data" / "processed" / "scripture.db"
MEM_DB = BASE / "data" / "memorize.db"


def get_top_words(count=500, cutoff=10):
    """Get top N Hebrew words by frequency from the lexicon."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    rows = conn.execute("""
        SELECT DISTINCT
            l.lemma,
            l.hebrew_plain as hebrew_word,
            l.transliteration,
            l.root_letters as root,
            l.definition,
            l.morphology,
            l.frequency as lex_freq,
            COALESCE(lg.english_gloss, l.lemma, '') as gloss
        FROM lexicon l
        LEFT JOIN lemma_gloss lg ON 
            l.lemma = lg.lemma
            OR (instr(l.lemma, '/') > 0 AND 
                substr(l.lemma, instr(l.lemma, '/') + 1) = lg.lemma)
        WHERE l.lemma NOT IN ('b', 'c', 'd', 'H', 'G', 'l', 'm', 'k', 'H')
          AND l.frequency > ?
          AND l.hebrew_plain IS NOT NULL AND l.hebrew_plain != ''
        ORDER BY l.frequency DESC
        LIMIT ?
    """, (cutoff, count * 2)).fetchall()
    conn.close()
    
    # Deduplicate by hebrew_word
    seen = set()
    words = []
    for r in rows:
        hw = (r['hebrew_word'] or '').strip()
        if not hw or hw in seen:
            continue
        seen.add(hw)
        gloss = (r['gloss'] or '').strip()
        if len(hw) <= 1 or not gloss:
            continue
        # Skip if gloss is a Strong's number (bad mapping)
        if gloss.replace(' ', '').isdigit():
            continue
        words.append({
            'lemma': r['lemma'],
            'hebrew': hw,
            'transliteration': (r['transliteration'] or '').strip(),
            'gloss': gloss,
            'root': (r['root'] or '').strip(),
            'definition': (r['definition'] or '').strip()[:200],
            'morphology': (r['morphology'] or '').strip(),
            'frequency': r['lex_freq'] or 0,
        })
        if len(words) >= count:
            break
    
    return words


def find_verse_example(hebrew_word):
    """Find a verse containing this Hebrew word. Returns (ref, verse_text) or None."""
    conn = sqlite3.connect(str(DB_PATH))
    # Try exact match in gematria table
    row = conn.execute("""
        SELECT v.id, v.text_hebrew, v.text_english
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        WHERE g.word_hebrew LIKE ?
        LIMIT 1
    """, (f'%{hebrew_word}%',)).fetchone()
    conn.close()
    
    if row:
        return (row[0], row[1], row[2])
    return None


def make_lesson_id(hebrew_word, idx):
    """Generate a stable lesson ID from a Hebrew word."""
    # Use the first 2 letters + index
    clean = ''.join(c for c in hebrew_word if c.isalpha())[:4]
    return f"vocab_{clean}_{idx}"


def strip_cantillation(w):
    import re
    return re.sub(r'[\u0591-\u05AF\u05BD\u05BF\u05C0\u05C3\u05C6]', '', w)


def clean_for_id(w):
    """Clean a Hebrew word for use in IDs."""
    w = strip_cantillation(w)
    w = w.replace('/', '')
    return w.replace(' ', '_')


def generate_practice_items(hebrew_word, gloss, transliteration, root, verse_data):
    """Generate practice items for a vocabulary lesson."""
    items = []
    
    # 1. Recognition: multiple choice — "Which word means X?"
    options_list = []
    common_words = ["יהוה", "אלהים", "ישראל", "בראשית", "ויאמר", "כי", "אשר", "על", "את", "לא"]
    # Mix in some other common words as distractors
    for w in common_words:
        if w != clean_for_id(hebrew_word):
            options_list.append(w)
            if len(options_list) >= 4:
                break
    # If not enough distractors, use the word itself
    while len(options_list) < 3:
        options_list.append(clean_for_id(hebrew_word) if len(options_list) % 2 == 0 else "יהוה")
    
    items.append({
        "question_type": "multiple_choice",
        "question_text": f"What does '{hebrew_word}' mean?",
        "options_json": json.dumps([gloss, "LORD", "God", "Israel"][:4], ensure_ascii=False),
        "correct_answer": gloss,
        "difficulty": 0.3,
        "explanation": f"'{hebrew_word}' means '{gloss}'."
    })
    
    # 2. Recognition reverse: "Which Hebrew word means X?"
    items.append({
        "question_type": "multiple_choice",
        "question_text": f"Which Hebrew word means '{gloss}'?",
        "options_json": json.dumps([clean_for_id(hebrew_word), "יהוה", "אלהים", "ישראל"], ensure_ascii=False),
        "correct_answer": clean_for_id(hebrew_word),
        "difficulty": 0.4,
        "explanation": f"'{gloss}' is '{hebrew_word}' in Hebrew."
    })
    
    # 3. Transliteration practice
    if transliteration:
        items.append({
            "question_type": "transliteration",
            "question_text": f"How do you pronounce '{hebrew_word}'? Type the transliteration.",
            "options_json": "",
            "correct_answer": transliteration,
            "difficulty": 0.5,
            "explanation": f"'{hebrew_word}' is pronounced '{transliteration}'."
        })
    
    # 4. Cloze from verse example
    if verse_data:
        ref, heb_text, eng_text = verse_data
        # Blank out the target word from the Hebrew text
        import re
        # Try to find and blank the exact word
        blanked_heb = heb_text.replace(hebrew_word, "______")
        if blanked_heb == heb_text:
            # Try without cantillation
            clean_target = strip_cantillation(hebrew_word)
            for w in heb_text.split():
                if clean_target in strip_cantillation(w) or strip_cantillation(w) in clean_target:
                    blanked_heb = heb_text.replace(w, "______")
                    break
        
        if "______" in blanked_heb:
            items.append({
                "question_type": "cloze",
                "question_text": f"Complete the verse:\n\n{blanked_heb}\n\n(Reference: {ref})",
                "options_json": "",
                "correct_answer": hebrew_word,
                "difficulty": 0.6,
                "explanation": f"The word '{hebrew_word}' means '{gloss}'. From {ref}."
            })
            
            # 5. Sentence forming (English→Hebrew)
            items.append({
                "question_type": "typing",
                "question_text": f"Translate this into Hebrew:\n\n\"{eng_text}\"\n\n(Type the Hebrew word '{hebrew_word}' from this verse)",
                "options_json": "",
                "correct_answer": hebrew_word,
                "difficulty": 0.7,
                "explanation": f"The Hebrew word is '{hebrew_word}' ({transliteration or gloss})."
            })
    
    # 6. Recall: give gloss, type Hebrew
    items.append({
        "question_type": "recall",
        "question_text": f"What is the Hebrew word for '{gloss}'? Type it using the keyboard.",
        "options_json": "",
        "correct_answer": clean_for_id(hebrew_word),
        "difficulty": 0.8,
        "explanation": f"The Hebrew word for '{gloss}' is '{hebrew_word}'."
    })
    
    # 7. Root identification
    if root:
        items.append({
            "question_type": "multiple_choice",
            "question_text": f"What is the triconsonantal root of '{hebrew_word}' ({gloss})?",
            "options_json": json.dumps([root, "אמש", "פעל", "קדש"], ensure_ascii=False),
            "correct_answer": root,
            "difficulty": 0.7,
            "explanation": f"The root of '{hebrew_word}' is {root}."
        })
    
    return items


def main():
    parser = argparse.ArgumentParser(description="Seed Hebrew vocabulary lessons")
    parser.add_argument("--count", type=int, default=500, help="Number of word lessons to create")
    parser.add_argument("--db", default=str(MEM_DB), help="Path to memorize.db")
    parser.add_argument("--min-frequency", type=int, default=10, help="Minimum word frequency")
    args = parser.parse_args()
    
    mem_db = Path(args.db)
    
    # Get top words
    print(f"Fetching top {args.count} Hebrew words...")
    words = get_top_words(args.count, args.min_frequency)
    print(f"  Got {len(words)} words (frequency range: {words[0]['frequency']} - {words[-1]['frequency']})")
    
    # Connect to memorize.db
    conn = sqlite3.connect(str(mem_db))
    conn.execute("PRAGMA foreign_keys=OFF")
    
    # Ensure tables exist
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hebrew_nodes (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 4,
            category TEXT NOT NULL DEFAULT 'word',
            description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS hebrew_lessons (
            node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
            content_json TEXT DEFAULT '{}',
            version INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS hebrew_practice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
            question_type TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options_json TEXT DEFAULT '',
            correct_answer TEXT NOT NULL,
            difficulty REAL DEFAULT 0.5,
            explanation TEXT DEFAULT ''
        );
    """)
    
    # Get existing word lessons (category='word') to find the max level
    existing = conn.execute("SELECT COUNT(*) FROM hebrew_nodes WHERE category='word'").fetchone()[0]
    print(f"  Existing word lessons: {existing}")
    start_level = 4  # word level
    
    new_nodes = 0
    new_items = 0
    
    for i, w in enumerate(words):
        lid = make_lesson_id(w['hebrew'], i)
        
        # Skip if practice items already exist for this node
        existing_items = conn.execute("SELECT id FROM hebrew_practice_items WHERE node_id=? LIMIT 1", (lid,)).fetchone()
        if existing_items:
            continue
        
        # Find a verse example
        verse_data = find_verse_example(w['hebrew'])
        
        # Create node
        title = f"{w['hebrew']} — {w['gloss']}"
        desc = w.get('definition', f"Frequency: {w['frequency']}x | Root: {w['root'] or '—'}")
        if len(desc) > 200:
            desc = desc[:200] + '...'
        
        conn.execute(
            "INSERT INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, 'word', ?)",
            (lid, title, start_level, desc)
        )
        new_nodes += 1
        
        # Create lesson content
        content = {
            "node_id": lid,
            "title": title,
            "category": "word",
            "description": desc,
            "hebrew": w['hebrew'],
            "transliteration": w['transliteration'],
            "gloss": w['gloss'],
            "root": w['root'],
            "frequency": w['frequency'],
            "verse_example": verse_data[0] if verse_data else None,
        }
        conn.execute(
            "INSERT INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)",
            (lid, json.dumps(content, ensure_ascii=False))
        )
        
        # Generate practice items
        items = generate_practice_items(
            w['hebrew'], w['gloss'], w['transliteration'],
            w['root'], verse_data
        )
        for item in items:
            conn.execute(
                "INSERT INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (lid, item['question_type'], item['question_text'], item['options_json'], item['correct_answer'], item['difficulty'], item['explanation'])
            )
            new_items += 1
        
        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"  Progress: {i+1}/{len(words)} lessons...")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Done! Created {new_nodes} new word lessons with {new_items} practice items")
    print(f"  Total vocabulary lessons now: {existing + new_nodes}")

    # Count by type
    conn2 = sqlite3.connect(str(mem_db))
    counts = conn2.execute("SELECT question_type, COUNT(*) FROM hebrew_practice_items GROUP BY question_type ORDER BY COUNT(*) DESC").fetchall()
    print(f"\nPractice items by type:")
    for t, c in counts:
        print(f"  {t}: {c}")
    conn2.close()


if __name__ == '__main__':
    main()
