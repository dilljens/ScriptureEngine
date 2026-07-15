#!/usr/bin/env python3
"""Build trigram FTS5 full-text search index for typo-tolerant scripture search.

Creates a verses_fts_trigram virtual table using the trigram tokenizer,
enabling substring matching and typo-tolerant search across English, Hebrew,
and Greek text in a single combined field.

Usage:
  .venv/bin/python3 scripts/build_fts_index.py              # Create/populate
  .venv/bin/python3 scripts/build_fts_index.py --reset       # Rebuild from scratch
  .venv/bin/python3 scripts/build_fts_index.py --dry-run     # Show what would be done
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db


FTS_TABLE = "verses_fts_trigram"


def build_search_text(row):
    """Build a single searchable text from all available language texts."""
    parts = []
    if row["text_hebrew"]:
        parts.append(f"hebrew: {row['text_hebrew']}")
    if row["text_greek"]:
        parts.append(f"greek: {row['text_greek']}")
    if row["text_english"]:
        parts.append(f"english: {row['text_english']}")
    return "  ".join(parts)


def build_fts_index(conn, reset=False, dry_run=False):
    """Create and populate the trigram FTS5 index."""
    if reset and not dry_run:
        conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}")
        # Also drop content/suffix shadow tables
        conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}_config")
        conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}_data")
        conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}_idx")
        conn.execute(f"DROP TABLE IF EXISTS {FTS_TABLE}_docsize")
        conn.commit()
        print(f"  Dropped existing {FTS_TABLE}")

    if not dry_run:
        conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
                verse_id UNINDEXED,
                book_id UNINDEXED,
                search_text,
                tokenize='trigram'
            )
        """)
        conn.commit()

    # Get all verses with text
    rows = conn.execute("""
        SELECT id, book_id, text_english, text_hebrew, text_greek
        FROM verses
        WHERE text_english != '' OR text_hebrew != '' OR text_greek != ''
        ORDER BY id
    """).fetchall()
    total = len(rows)
    print(f"  Verses with text: {total}")

    # Check already indexed
    try:
        already = set(
            r["verse_id"]
            for r in conn.execute(f"SELECT verse_id FROM {FTS_TABLE}").fetchall()
        )
    except Exception:
        already = set()
    print(f"  Already indexed: {len(already)}")

    to_index = [r for r in rows if r["id"] not in already]
    if not to_index:
        print("  All verses already indexed.")
        return 0, len(already)

    print(f"  New to index: {len(to_index)}")

    if dry_run:
        print(f"  [DRY RUN] Would insert {len(to_index)} rows")
        return len(to_index), len(already)

    # Insert in batches
    BATCH_SIZE = 500
    indexed = 0
    for i in range(0, len(to_index), BATCH_SIZE):
        batch = to_index[i:i + BATCH_SIZE]
        texts = [build_search_text(r) for r in batch]

        insert_batch = []
        for r, t in zip(batch, texts):
            if t:
                insert_batch.append((r["id"], r["book_id"], t))

        conn.executemany(
            f"INSERT INTO {FTS_TABLE} (verse_id, book_id, search_text) VALUES (?, ?, ?)",
            insert_batch,
        )
        conn.commit()
        indexed += len(insert_batch)

        if (i // BATCH_SIZE) % 20 == 0:
            print(f"  Progress: {indexed}/{len(to_index)}", flush=True)

    return indexed, len(already)


def verify(conn):
    """Check the trigram index is working."""
    try:
        count = conn.execute(
            f"SELECT COUNT(*) as c FROM {FTS_TABLE}"
        ).fetchone()["c"]
    except Exception:
        return 0

    # Quick smoke tests
    tests = [
        ("genis", 1),        # typo → Genesis
        ("covenent", 1),     # typo → covenant
        ("gene", 1),         # prefix → Genesis
        ("יהוה", 1),         # Hebrew
        ("λόγος", 1),        # Greek
    ]
    passed = 0
    for q, expected_min in tests:
        try:
            row = conn.execute(
                f"SELECT COUNT(*) as c FROM {FTS_TABLE} WHERE {FTS_TABLE} MATCH ?",
                (q,),
            ).fetchone()
            actual = row["c"]
            if actual >= expected_min:
                passed += 1
            else:
                print(f"  ⚠ '{q}': expected ≥{expected_min}, got {actual}")
        except Exception as e:
            print(f"  ✗ '{q}': error — {e}")

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Build trigram FTS5 index for typo-tolerant scripture search"
    )
    parser.add_argument("--reset", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    args = parser.parse_args()

    print("=" * 60)
    print("  Trigram FTS5 Search Index Builder")
    print("=" * 60)

    conn = get_db()
    start = time.time()

    print("\n--- Building index...", flush=True)
    indexed, skipped = build_fts_index(conn, reset=args.reset, dry_run=args.dry_run)

    elapsed = time.time() - start
    print(f"\n  Indexed: {indexed} new")
    print(f"  Skipped: {skipped}")
    print(f"  Elapsed: {elapsed:.1f}s")

    if not args.dry_run:
        print("\n--- Verification ---", flush=True)
        count = verify(conn)
        print(f"  Total rows in {FTS_TABLE}: {count}")

        if count > 0:
            print("\n--- Demo: Typo-Tolerant Search ---")
            demos = [
                "genis",
                "covenent",
                "gene",
                "יהוה",
                "λόγος",
                "brith",
            ]
            for q in demos:
                try:
                    rows = conn.execute(
                        f"""
                        SELECT f.verse_id, substr(f.search_text, 1, 80) as snippet
                        FROM {FTS_TABLE} f
                        WHERE {FTS_TABLE} MATCH ?
                        ORDER BY rank
                        LIMIT 2
                        """,
                        (q,),
                    ).fetchall()
                    if rows:
                        print(f"\n  '{q}':")
                        for r in rows:
                            print(f"    {r['verse_id']:20s} {r['snippet']}")
                    else:
                        print(f"\n  '{q}': (no results)")
                except Exception as e:
                    print(f"\n  '{q}': error — {e}")

        # Mark as available
        conn.execute("""
            INSERT OR REPLACE INTO ui_preferences (pref_key, pref_value)
            VALUES ('fts_available', 'true')
        """)
        conn.commit()

    conn.close()
    print(f"\n  Done.")


if __name__ == "__main__":
    main()
