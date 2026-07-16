#!/usr/bin/env python3
"""Batch-fill transliteration for all Hebrew vocabulary and lexicon entries.

Fills empty transliteration fields using the biblical-transliteration library
with SIMPLE scheme (ASCII-friendly) for vocabulary lessons and SBL for lexicon.

Usage:
    python3 scripts/fill_transliteration.py              # Dry run
    python3 scripts/fill_transliteration.py --apply      # Apply changes
    python3 scripts/fill_transliteration.py --apply --db data/processed/scripture.db
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))
from lib.hebrew_util import transliterate, clean_hebrew


def fill_vocab_lessons(mem_db, scrip_db, dry_run=True):
    """Fill transliteration in vocabulary lessons using pointed Hebrew from lexicon."""
    mem = sqlite3.connect(str(mem_db))
    mem.row_factory = sqlite3.Row
    scrip = sqlite3.connect(str(scrip_db))
    scrip.row_factory = sqlite3.Row

    # Build lookup: unpointed hebrew → best pointed form from lexicon
    lex_rows = scrip.execute(
        "SELECT hebrew, hebrew_plain, frequency FROM lexicon WHERE hebrew IS NOT NULL AND hebrew != '' ORDER BY frequency DESC"
    ).fetchall()

    pointed_lookup = {}
    for r in lex_rows:
        plain = r["hebrew_plain"]
        if plain and plain not in pointed_lookup:
            pointed_lookup[plain] = r["hebrew"]

    lessons = mem.execute(
        "SELECT node_id, content_json FROM hebrew_lessons WHERE node_id LIKE 'vocab_%'"
    ).fetchall()

    filled = 0
    skipped = 0
    for row in lessons:
        try:
            content = json.loads(row["content_json"])
        except (json.JSONDecodeError, TypeError):
            continue

        hebrew = content.get("hebrew", "")
        if not hebrew:
            skipped += 1
            continue

        # Check if transliteration already exists
        existing = content.get("transliteration", "")
        if existing:
            skipped += 1
            continue

        # Find pointed form from lexicon
        pointed = pointed_lookup.get(hebrew)
        if not pointed:
            # Try with the first 3 chars as fallback
            for plain, p_form in pointed_lookup.items():
                if plain.startswith(hebrew[:3]):
                    pointed = p_form
                    break
        if not pointed:
            skipped += 1
            continue

        # Generate transliteration from pointed form (SIMPLE scheme for vocab)
        translit = transliterate(pointed, scheme="simple")
        if not translit:
            skipped += 1
            continue

        content["transliteration"] = translit
        if not dry_run:
            mem.execute(
                "UPDATE hebrew_lessons SET content_json = ? WHERE node_id = ?",
                (json.dumps(content, ensure_ascii=False), row["node_id"])
            )
        filled += 1

    mem.commit()
    mem.close()
    scrip.close()
    return filled, skipped


def fill_lexicon(scripture_db, dry_run=True):
    """Fill empty transliteration in the lexicon table using SBL scheme."""
    conn = sqlite3.connect(str(scripture_db) if scripture_db else BASE / "data" / "processed" / "scripture.db")
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT lemma, hebrew, transliteration FROM lexicon WHERE hebrew IS NOT NULL AND hebrew != ''"
    ).fetchall()

    filled = 0
    skipped = 0
    for row in rows:
        if row["transliteration"] and row["transliteration"].strip():
            skipped += 1
            continue

        hebrew = row["hebrew"]
        translit = transliterate(hebrew, scheme="sbl")
        if not translit:
            skipped += 1
            continue

        if not dry_run:
            conn.execute(
                "UPDATE lexicon SET transliteration = ? WHERE lemma = ?",
                (translit, row["lemma"])
            )
        filled += 1

    conn.commit()
    conn.close()
    return filled, skipped


def main():
    parser = argparse.ArgumentParser(description="Batch-fill transliteration")
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    parser.add_argument("--mem-db", type=str, default="")
    parser.add_argument("--scrip-db", type=str, default="")
    args = parser.parse_args()

    mem_db = Path(args.mem_db) if args.mem_db else BASE / "data" / "memorize.db"
    scrip_db = Path(args.scrip_db) if args.scrip_db else BASE / "data" / "processed" / "scripture.db"

    print("=== Batch-Fill Transliteration ===")
    print(f"  Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    if mem_db.exists() and scrip_db.exists():
        v_filled, v_skipped = fill_vocab_lessons(mem_db, scrip_db, dry_run=not args.apply)
        print(f"Vocabulary lessons: {v_filled} filled, {v_skipped} skipped")
    else:
        print(f"Memorize DB not found at {mem_db}")

    if scrip_db.exists():
        l_filled, l_skipped = fill_lexicon(scrip_db, dry_run=not args.apply)
        print(f"Lexicon entries:   {l_filled} filled, {l_skipped} skipped")
    else:
        print(f"Scripture DB not found at {scrip_db}")


if __name__ == "__main__":
    main()
