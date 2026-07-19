#!/usr/bin/env python3
"""Auto-generate assessment items from knowledge_items table.

Takes the 685K knowledge items (high-quality verse→verse connections) and
generates assessment questions for them. Currently 247 items exist — this
script boosts to 1,000+.

Question types generated:
  - multiple_choice: "Which verse connects to X via type Y?"
  - short_answer: "What type of connection exists between X and Y?"

Usage:
  .venv/bin/python3 scripts/generate_assessment_items.py     # Generate new items
  .venv/bin/python3 scripts/generate_assessment_items.py --dry-run  # Preview only
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db

# Target: generate items for these connection types
TARGET_TYPES = [
    "same_lemma",
    "same_root",
    "direct_quotation",
    "allusion",
    "keyword_linking",
    "phrase_match",
    "gematria_sum",
    "chiasm_parallel",
    "parallelism",
    "same_morphology",
]

# Templates for multiple-choice questions
MC_TEMPLATES = [
    {
        "type": "cross_reference",
        "question": "Which verse below is connected to {source} via a **{conn_type}** connection?",
        "generate_options": True,  # options = 1 correct + 3 distractors from same type
    },
    {
        "type": "type_identification",
        "question": "What type of connection links {source} and {target}?",
        "generate_options": False,  # options = connection types
    },
    {
        "type": "layer_classification",
        "question": "What layer does the connection between {source} and {target} belong to?",
        "generate_options": False,  # options = layer names
    },
]


def get_existing_count(conn):
    """Count existing assessment items."""
    return conn.execute("SELECT COUNT(*) as c FROM assessment_items").fetchone()["c"]


def get_connection_types(conn):
    """Get all distinct connection types from knowledge_items."""
    rows = conn.execute(
        "SELECT DISTINCT connection_type FROM knowledge_items WHERE connection_type IS NOT NULL ORDER BY connection_type"
    ).fetchall()
    return [r["connection_type"] for r in rows]


def get_layers(conn):
    """Get all distinct layers from knowledge_items."""
    rows = conn.execute(
        "SELECT DISTINCT layer FROM knowledge_items WHERE layer IS NOT NULL ORDER BY layer"
    ).fetchall()
    return [r["layer"] for r in rows]


def get_verse_text(conn, verse_id):
    """Get a short text snippet for a verse."""
    row = conn.execute(
        "SELECT text_english FROM verses WHERE id = ?", (verse_id,)
    ).fetchone()
    if row and row["text_english"]:
        text = row["text_english"][:80]
        if len(row["text_english"]) > 80:
            text += "..."
        return text
    return ""


def generate_mc_cross_reference(conn, ki, layers, target_count, existing):
    """Generate a multiple-choice cross-reference question."""
    source = ki["verse_id"]
    target = ki["target_verse"]
    conn_type = ki["connection_type"] or "connection"

    # Get 3 distractors (other verses connected via the same type)
    distractors = conn.execute(
        """SELECT DISTINCT target_verse FROM knowledge_items
           WHERE connection_type = ? AND verse_id != ? AND target_verse != ?
           ORDER BY RANDOM() LIMIT 3""",
        (conn_type, source, target),
    ).fetchall()

    if len(distractors) < 3:
        return None

    options = [target] + [d["target_verse"] for d in distractors]
    random.shuffle(options)

    correct_idx = options.index(target)
    # Map to labels
    labels = [chr(65 + i) for i in range(len(options))]
    correct_label = labels[correct_idx]

    options_formatted = "\n".join(
        f"{labels[i]}. {opt}" for i, opt in enumerate(options)
    )

    source_text = get_verse_text(conn, source)
    question = f"**{source}**"
    if source_text:
        question += f"\n> {source_text}"
    question += f"\n\nWhich verse below is connected to **{source}** via a **{conn_type}** connection?\n\n{options_formatted}"

    return {
        "knowledge_item_id": ki["id"],
        "question_type": "multiple_choice",
        "question_text": question,
        "options_json": json.dumps(options),
        "correct_answer": correct_label,
        "layer": ki.get("layer", ""),
        "difficulty": 1.0 - (ki.get("star_rating", 3) / 5.0),
        "discrimination": 0.8,
        "guess_param": 0.25,
        "slip_param": 0.15,
    }


def generate_mc_type_identification(conn, ki, conn_types):
    """Generate multiple-choice: identify the connection type between two verses."""
    source = ki["verse_id"]
    target = ki["target_verse"]
    correct_type = ki["connection_type"]

    # Get 3 wrong connection types as distractors
    distractors = random.sample(
        [t for t in conn_types if t != correct_type], min(3, len(conn_types) - 1)
    )
    if len(distractors) < 3:
        return None

    options = [correct_type] + distractors
    random.shuffle(options)
    labels = [chr(65 + i) for i in range(len(options))]
    correct_label = labels[options.index(correct_type)]
    options_formatted = "\n".join(
        f"{labels[i]}. {opt}" for i, opt in enumerate(options)
    )

    question = f"What type of connection links **{source}** and **{target}**?\n\n{options_formatted}"

    return {
        "knowledge_item_id": ki["id"],
        "question_type": "multiple_choice",
        "question_text": question,
        "options_json": json.dumps(options),
        "correct_answer": correct_label,
        "layer": ki.get("layer", ""),
        "difficulty": 1.0 - (ki.get("star_rating", 3) / 5.0),
        "discrimination": 0.7,
        "guess_param": 0.25,
        "slip_param": 0.20,
    }


def generate_short_answer(conn, ki):
    """Generate a short-answer question."""
    source = ki["verse_id"]
    target = ki["target_verse"]
    conn_type = ki["connection_type"] or "connection"

    source_text = get_verse_text(conn, source)
    question = f"**{source}**"
    if source_text:
        question += f"\n> {source_text}"
    question += f"\n\nThis verse is connected to **{target}**. What type of connection is it?"

    return {
        "knowledge_item_id": ki["id"],
        "question_type": "short_answer",
        "question_text": question,
        "options_json": "[]",
        "correct_answer": conn_type,
        "layer": ki.get("layer", ""),
        "difficulty": 1.0 - (ki.get("star_rating", 3) / 5.0),
        "discrimination": 0.6,
        "guess_param": 0.0,
        "slip_param": 0.25,
    }


def generate_items(conn, dry_run=False, target_count=1000):
    """Generate assessment items from knowledge_items."""
    existing_count = get_existing_count(conn)
    print(f"Existing assessment items: {existing_count}")
    print(f"Target total: {target_count}")
    print(f"Need to generate: {max(0, target_count - existing_count)}")
    print()

    if existing_count >= target_count:
        print("Already at or above target. Skipping.")
        return 0

    conn_types = get_connection_types(conn)
    layers = get_layers(conn)
    print(f"Available connection types: {len(conn_types)}")
    print(f"Available layers: {len(layers)}")

    # Get high-quality knowledge items (>=3 stars) not yet used
    ki_rows = conn.execute(
        """SELECT ki.* FROM knowledge_items ki
           LEFT JOIN assessment_items ai ON ai.knowledge_item_id = ki.id
           WHERE ai.id IS NULL AND ki.star_rating >= 3
             AND ki.verse_id IS NOT NULL AND ki.target_verse IS NOT NULL
           ORDER BY RANDOM()
           LIMIT ?""",
        (target_count * 3,),
    ).fetchall()

    if not ki_rows:
        print("No unused high-quality knowledge items found.")
        return 0

    print(f"Candidate knowledge items: {len(ki_rows)}")
    print()

    generated = 0
    items_to_insert = []

    for ki in ki_rows:
        if generated >= target_count - existing_count:
            break

        # Pick a template randomly
        template = random.choice(MC_TEMPLATES)
        item = None

        if template["type"] == "cross_reference":
            item = generate_mc_cross_reference(conn, ki, layers, target_count, items_to_insert)
        elif template["type"] == "type_identification":
            item = generate_mc_type_identification(conn, ki, conn_types)
        elif template["type"] == "layer_classification":
            continue  # skip for now — simpler to just do the two above

        # Fall back to short answer if MC generation failed
        if item is None:
            item = generate_short_answer(conn, ki)

        if item is None:
            continue

        # Every 10th item, also add a short-answer version
        add_short_answer = generated > 0 and generated % 10 == 0
        if add_short_answer:
            sa = generate_short_answer(conn, ki)
            if sa:
                items_to_insert.append(sa)
                generated += 1

        items_to_insert.append(item)
        generated += 1

        if generated % 100 == 0:
            print(f"  Generated: {generated}...")

    # Insert into database
    if not dry_run and items_to_insert:
        BATCH_SIZE = 50
        for i in range(0, len(items_to_insert), BATCH_SIZE):
            batch = items_to_insert[i : i + BATCH_SIZE]
            for item in batch:
                try:
                    conn.execute(
                        """INSERT OR IGNORE INTO assessment_items
                           (knowledge_item_id, question_type, question_text, options_json,
                            correct_answer, layer, difficulty, discrimination, guess_param, slip_param)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            item["knowledge_item_id"],
                            item["question_type"],
                            item["question_text"],
                            item["options_json"],
                            item["correct_answer"],
                            item["layer"],
                            round(item["difficulty"], 4),
                            item["discrimination"],
                            item["guess_param"],
                            item["slip_param"],
                        ),
                    )
                except Exception:
                    continue
            conn.commit()

    final_count = get_existing_count(conn) if not dry_run else existing_count + len(items_to_insert)
    print(f"\nDone. Generated: {len(items_to_insert)}")
    print(f"Total assessment items: {final_count}")
    return len(items_to_insert)


def main():
    parser = argparse.ArgumentParser(
        description="Auto-generate assessment items from knowledge items"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB writes")
    parser.add_argument("--target", type=int, default=1000, help="Target total items (default: 1000)")
    args = parser.parse_args()

    print("=" * 60)
    print("  Assessment Item Generator")
    print(f"  Target: {args.target} items{' (DRY RUN)' if args.dry_run else ''}")
    print("=" * 60)

    conn = get_db()

    print("\n--- Generating items...\n")
    count = generate_items(conn, dry_run=args.dry_run, target_count=args.target)

    conn.close()
    print(f"\n  {'DRY RUN: Would add' if args.dry_run else 'Added'} {count} items")


if __name__ == "__main__":
    main()
