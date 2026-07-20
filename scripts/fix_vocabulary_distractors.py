#!/usr/bin/env python3
"""
Phase 2.1: Replace generic vocabulary distractors with plausible alternatives.

The current MC questions use ["LORD", "God", "Israel"] as the wrong answers
for every vocabulary item. These are never plausible — any learner can eliminate
them by common sense.

This script replaces them with a pool of common Hebrew word glosses that are
actually plausible: words the learner might confuse the target with.
"""

import json
import random
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

# Pool of plausible distractor glosses — common BH words the learner
# might actually confuse with the target. These are all in the top ~150
# most frequent words.
DISTRACTOR_POOL = [
    "king", "man", "land", "day", "word", "house", "son", "hand", "way",
    "people", "father", "God", "water", "soul", "life", "light", "death",
    "peace", "truth", "wisdom", "flesh", "blood", "fire", "gold", "silver",
    "bread", "wine", "mountain", "heavens", "earth", "sea", "night", "morning",
    "name", "voice", "heart", "spirit", "glory", "servant", "priest", "kingdom",
    "covenant", "altar", "sacrifice", "offering", "throne", "city", "gate",
    "war", "judgment", "righteousness", "sin", "law", "commandment", "statute",
    "witness", "congregation", "corner", "whole", "face", "seed", "fruit",
    "work", "song", "prayer", "praise", "wisdom", "strength", "glory",
    "to say", "to see", "to hear", "to know", "to give", "to take", "to eat",
    "to drink", "to go", "to come", "to stand", "to sit", "to walk", "to run",
    "to bless", "to curse", "to kill", "to save", "to judge", "to write",
    "to speak", "to answer", "to remember", "to forget", "to love", "to hate",
    "to fear", "to trust", "to hope", "to rejoice", "to weep", "to build",
    "good", "bad", "great", "small", "old", "new", "holy", "clean", "unclean",
    "all", "many", "few", "much", "one", "two", "three", "four", "five",
    "first", "last", "strong", "weak", "wise", "foolish", "righteous", "wicked",
    "before", "after", "under", "upon", "with", "without", "from", "to",
    "in", "and", "or", "if", "because", "therefore", "then", "now", "behold",
    "why", "what", "who", "how", "this", "that", "these", "those",
]


def fix_distractors():
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    # Find vocabulary MC items whose options contain the old generic distractors
    items = conn.execute("""
        SELECT p.id, p.node_id, p.question_text, p.correct_answer, p.options_json
        FROM hebrew_practice_items p
        JOIN hebrew_nodes n ON n.id = p.node_id
        WHERE n.category = 'word'
        AND p.question_type = 'multiple_choice'
        AND (p.options_json LIKE '%LORD%' OR p.options_json LIKE '%GOD%' 
             OR p.options_json LIKE '%Israel%' OR p.options_json LIKE '%direct object%')
        ORDER BY p.node_id
    """).fetchall()

    fixed = 0
    for item in items:
        try:
            opts = json.loads(item['options_json'])
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(opts, list) or len(opts) < 2:
            continue

        correct = item['correct_answer']

        # Check if options contain any of the bad generic distractors
        bad_distractors = ['LORD', 'God', 'Israel', 'direct object']
        has_bad = any(d in opts for d in bad_distractors)
        if not has_bad:
            continue

        # Rebuild options: keep the correct answer, replace other slots
        # with random draw from the plausible pool
        new_opts = [correct]
        pool = [d for d in DISTRACTOR_POOL if d != correct and d not in new_opts]
        random.shuffle(pool)

        target_count = min(4, len(pool) + 1)  # aim for 4 options total
        needed = target_count - 1  # how many distractors we need

        for i in range(needed):
            if i < len(pool):
                new_opts.append(pool[i])
            else:
                # Fallback: just add a placeholder
                new_opts.append("(other)")

        # If pool is exhausted, replace leftover bad distractors
        if len(new_opts) < 4:
            new_opts.append("(other)")
        while len(new_opts) < 4:
            new_opts.append("(other)")

        # Only update if different
        if new_opts != opts:
            conn.execute(
                "UPDATE hebrew_practice_items SET options_json=? WHERE id=?",
                (json.dumps(new_opts[:4], ensure_ascii=False), item['id'])
            )
            fixed += 1

    conn.commit()
    conn.close()
    print(f"  Fixed {fixed} practice items with better distractors")


def fix_phrase_distractors():
    """
    Phase 2.2: Fix phrase lesson distractors.
    Phrase lessons currently use ["Hello", "Goodbye", "Amen", "Peace"] as
    distractors. Replace with real Hebrew phrase meanings.
    """
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    phrase_items = conn.execute("""
        SELECT p.id, p.node_id, p.question_text, p.correct_answer, p.options_json
        FROM hebrew_practice_items p
        JOIN hebrew_nodes n ON n.id = p.node_id
        WHERE n.category = 'phrase'
        AND p.question_type = 'multiple_choice'
        AND (p.options_json LIKE '%Hello%' OR p.options_json LIKE '%Goodbye%'
             OR p.options_json LIKE '%God is great%' OR p.options_json LIKE '%The end%')
        ORDER BY p.node_id, p.id
    """).fetchall()

    # Pool of plausible phrase-level distractors
    phrase_pool = [
        "Thus says the LORD", "The word of YHWH", "Blessed be YHWH",
        "Do not fear", "Hear O Israel", "In that day", "Behold, here I am",
        "To YHWH be the glory", "The LORD is one", "The LORD our God",
        "You shall love", "I am YHWH", "The God of Israel",
        "The LORD of Hosts", "Holy, holy, holy", "Fear not",
        "Thus says YHWH", "And God said", "The angel of YHWH",
    ]

    fixed = 0
    for item in phrase_items:
        try:
            opts = json.loads(item['options_json'])
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(opts, list):
            continue

        correct = item['correct_answer']
        bad = ['Hello', 'Goodbye', 'God is great', 'The end', 'Peace', 'Amen']
        has_bad = any(d in opts for d in bad)
        if not has_bad:
            continue

        # Keep correct answer, replace bad distractors
        new_opts = [correct]
        pool = [d for d in phrase_pool if d != correct]
        random.shuffle(pool)

        needed = min(3, len(pool))
        for i in range(needed):
            new_opts.append(pool[i])

        while len(new_opts) < 4:
            new_opts.append("(other phrase)")

        if new_opts != opts:
            conn.execute(
                "UPDATE hebrew_practice_items SET options_json=? WHERE id=?",
                (json.dumps(new_opts[:4], ensure_ascii=False), item['id'])
            )
            fixed += 1

    conn.commit()
    conn.close()
    print(f"  Fixed {fixed} phrase practice items with better distractors")


if __name__ == '__main__':
    print("=== Phase 2.1: Fix vocabulary distractors ===")
    fix_distractors()
    print("\n=== Phase 2.2: Fix phrase distractors ===")
    fix_phrase_distractors()
    print("\n✓ Done!")
