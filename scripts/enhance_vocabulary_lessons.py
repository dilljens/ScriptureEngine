#!/usr/bin/env python3
"""Enhance vocabulary lessons: add real verse context + 3 KP structure.

For each vocabulary word lesson, finds a real verse containing the word
and adds it as a worked example. Also restructures practice items into
3 Knowledge Points (recognition → recall → production).

Usage:
    python3 scripts/enhance_vocabulary_lessons.py
    python3 scripts/enhance_vocabulary_lessons.py --dry-run
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"
SCRIPTURE_DB = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"


def find_verse_for_word(word, conn):
    """Find a real verse containing this Hebrew word."""
    row = conn.execute(
        "SELECT v.id, v.text_hebrew, v.text_english FROM gematria g "
        "JOIN verses v ON v.id = g.verse_id "
        "WHERE g.word_hebrew LIKE ? AND v.text_english IS NOT NULL "
        "LIMIT 1",
        (f'%{word}%',)).fetchone()
    if row:
        return row[0], row[1], row[2]
    return None, None, None


def main():
    parser = argparse.ArgumentParser(description="Enhance vocabulary lessons with verse examples")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    args = parser.parse_args()

    mem = sqlite3.connect(str(MEM_DB))
    scrip = sqlite3.connect(str(SCRIPTURE_DB))

    # Get all vocabulary lesson nodes
    vocab_nodes = mem.execute(
        "SELECT n.id, n.title, n.description, l.content_json "
        "FROM hebrew_nodes n JOIN hebrew_lessons l ON l.node_id=n.id "
        "WHERE n.category='word' AND n.id LIKE 'vocab_%'"
    ).fetchall()

    print(f"Processing {len(vocab_nodes)} vocabulary lessons...")
    enhanced = 0
    new_items = 0

    for nid, _title, _desc, content_json in vocab_nodes:
        try:
            content = json.loads(content_json)
        except (json.JSONDecodeError, ValueError):
            content = {}

        hebrew = content.get('hebrew', '')
        if not hebrew:
            continue

        # Find a real verse containing this word
        ref, heb_text, eng_text = find_verse_for_word(hebrew, scrip)
        if ref:
            # Add verse example to lesson content
            content['verse_example'] = ref
            content['verse_hebrew'] = heb_text
            content['verse_english'] = eng_text

            if not args.dry_run:
                mem.execute("UPDATE hebrew_lessons SET content_json=? WHERE node_id=?",
                           (json.dumps(content, ensure_ascii=False), nid))

            # Check if there's already a cloze or typing item for this lesson
            has_cloze = mem.execute(
                "SELECT COUNT(*) FROM hebrew_practice_items WHERE node_id=? AND question_type='cloze'",
                (nid,)).fetchone()[0] > 0
            has_typing = mem.execute(
                "SELECT COUNT(*) FROM hebrew_practice_items WHERE node_id=? AND question_type='typing'",
                (nid,)).fetchone()[0] > 0

            # Add KP2: Cloze from the actual verse (if not exists)
            if not has_cloze and heb_text:
                # Find the word in the verse text and blank it
                blanked = heb_text.replace(hebrew, "______")
                if "______" in blanked and not args.dry_run:
                        mem.execute(
                            "INSERT INTO hebrew_practice_items (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation) VALUES (?,?,?,?,?,?,?)",
                            (nid, 'cloze', f"Complete the verse:\n\n{blanked}\n\n(Reference: {ref})", '', hebrew, 0.6, f"This completes the verse from {ref}."))
                        new_items += 1

            # Add KP3: Translate the verse (if not exists)
            if not has_typing and eng_text:
                ref_short = ref.replace('dss.', '').replace('pseu.', '').replace('apo.', '').replace('bom.', '')
                if not args.dry_run:
                    mem.execute(
                        "INSERT INTO hebrew_practice_items (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation) VALUES (?,?,?,?,?,?,?)",
                        (nid, 'typing', f"Translate this back to Hebrew:\n\n\"{eng_text}\"", '', hebrew, 0.8, f"This is the key word from {ref_short}."))
                    new_items += 1

            # Add KP1: Recognition from verse context (if not exists)
            existing_mc = mem.execute(
                "SELECT COUNT(*) FROM hebrew_practice_items WHERE node_id=? AND question_type='multiple_choice' AND question_text LIKE ?",
                (nid, '%verse%')).fetchone()[0]
            if not existing_mc and heb_text and eng_text:
                # Use a different word from the verse as a distractor
                distractor_words = []
                for w in heb_text.split():
                    clean = re.sub(r'[\u0591-\u05AF]', '', w).replace('/','')
                    if clean and clean != hebrew and len(clean) >= 2:
                        distractor_words.append(clean)
                distractors = distractor_words[:3]
                while len(distractors) < 3:
                    distractors.append("יהוה")
                opts = [hebrew] + distractors[:3]
                if not args.dry_run:
                    mem.execute(
                        "INSERT INTO hebrew_practice_items (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation) VALUES (?,?,?,?,?,?,?)",
                        (nid, 'multiple_choice', f"In the verse '{eng_text[:80]}...', which Hebrew word means '{content.get('gloss', '')}'?", json.dumps(opts, ensure_ascii=False), hebrew, 0.3, f"The word '{hebrew}' in {ref} means '{content.get('gloss', '')}'."))
                    new_items += 1

            enhanced += 1
            if enhanced % 50 == 0:
                if not args.dry_run:
                    mem.commit()
                print(f"  Progress: {enhanced}/{len(vocab_nodes)}...")

    if not args.dry_run:
        mem.commit()

    print(f"\n✓ Enhanced {enhanced}/{len(vocab_nodes)} lessons with real verse examples")
    print(f"  Added {new_items} new practice items (KP1 recognition, KP2 cloze, KP3 typing)")

    # Stats
    total_items = mem.execute("SELECT COUNT(*) FROM hebrew_practice_items").fetchone()[0]
    by_type = mem.execute(
        "SELECT question_type, COUNT(*) FROM hebrew_practice_items GROUP BY question_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    print(f"\n  Total practice items: {total_items}")
    for t, c in by_type:
        print(f"    {t}: {c}")

    mem.close()
    scrip.close()


if __name__ == '__main__':
    main()
