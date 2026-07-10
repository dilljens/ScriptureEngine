#!/usr/bin/env python3
"""Generate vulgate_variant connections from textual_variants table.

Two passes:
  1. Systematic: For every verse with a Vulgate text, create a connection
     to a book-level hub verse (hub-and-spoke per book).
  2. Curated: Apply hand-curated significant variant connections from JSON.

Usage:  python3 scripts/generate_vulgate_connections.py
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db, add_connection
from collections import defaultdict


def _batch_insert(conn, batch):
    if not batch:
        return
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run_systematic(conn):
    """Create vulgate_variant connections for all Vulgate verses.
    
    Per-book hub-and-spoke: first verse in a book with a Vulgate variant
    becomes the hub; all other variant verses in that book connect to it.
    """
    print("  Generating systematic vulgate_variant connections...", flush=True)
    
    # Delete existing systematic connections
    conn.execute("""
        DELETE FROM connections 
        WHERE type = 'vulgate_variant' AND discovered_by = 'algorithm'
    """)
    conn.commit()

    # Get all verses with Vulgate variants, grouped by book
    var_rows = conn.execute("""
        SELECT tv.verse_id, v.book_id, tv.text
        FROM textual_variants tv
        JOIN verses v ON v.id = tv.verse_id
        WHERE tv.tradition = 'vulgate'
          AND v.text_english != ''
        ORDER BY tv.verse_id
    """).fetchall()

    print(f"    Found {len(var_rows)} verses with Vulgate text", flush=True)

    # Group by book
    book_verses = defaultdict(list)
    for r in var_rows:
        book_verses[r['book_id']].append((r['verse_id'], r['text']))

    total = 0
    # Also create: within-book connections (hub-and-spoke)
    # and across-book connections (connect hubs)
    book_hubs = {}

    for book_id, verses in sorted(book_verses.items()):
        if len(verses) < 2:
            continue

        hub_verse = verses[0][0]
        book_hubs[book_id] = hub_verse

        # Connect all other verses in this book to the hub
        batch = []
        for verse_id, lat_text in verses[1:]:
            text_snippet = (lat_text or '')[:80]
            batch.append((
                hub_verse, verse_id, "textual",
                "vulgate_variant", f"book_{book_id}",
                0.5, 0.6, "algorithm",
                '{"vulgate": "' + text_snippet.replace('"', "'") + '", '
                '"book": "' + book_id + '", "variant_type": "systematic"}'
            ))
            total += 1

        _batch_insert(conn, batch)

    # Connect book hubs to each other
    hub_list = sorted(book_hubs.items())
    batch = []
    for i in range(len(hub_list)):
        for j in range(i + 1, len(hub_list)):
            batch.append((
                hub_list[i][1], hub_list[j][1], "textual",
                "vulgate_variant", "inter_book",
                0.4, 0.5, "algorithm",
                '{"books": ["' + hub_list[i][0] + '", "' + hub_list[j][0] + '"], '
                '"variant_type": "hub_link"}'
            ))
            total += 1
    _batch_insert(conn, batch)

    print(f"    Systematic connections: {total}")
    return total


def apply_curated(conn):
    """Apply hand-curated vulgate_variant judgments."""
    print("  Applying curated vulgate_variant connections...", flush=True)

    filepath = 'data/llm_connections/vulgate_variant_curated.json'
    if not os.path.exists(filepath):
        print(f"    No curated file found at {filepath}")
        return 0

    with open(filepath) as f:
        judgments = json.load(f)

    count = 0
    for j in judgments:
        try:
            add_connection(conn,
                source_verse=j['source_verse'],
                target_verse=j['target_verse'],
                layer=j['layer'],
                type_name=j['type'],
                subtype=j.get('subtype', ''),
                strength=j.get('strength', 0.7),
                confidence=j.get('confidence', 0.75),
                discovered_by='llm',
                metadata=j.get('metadata', {}))
            count += 1
        except Exception as e:
            print(f"    Error: {e}")

    conn.commit()
    print(f"    Curated connections: {count}")
    return count


def main():
    print("=" * 60)
    print("  VULGATE VARIANT CONNECTION GENERATOR")
    print("=" * 60)

    conn = get_db()

    sys_total = run_systematic(conn)
    cur_total = apply_curated(conn)

    total = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE type = 'vulgate_variant'"
    ).fetchone()[0]

    print(f"\n  Total vulgate_variant connections: {total:,}")
    print(f"    Systematic: {sys_total:,}")
    print(f"    Curated: {cur_total}")
    print(f"  Done.")

    conn.close()


if __name__ == "__main__":
    main()
