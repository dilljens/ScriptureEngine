#!/usr/bin/env python3
"""Incremental passage guide update — only recalculates verses whose connections changed.

Run this instead of precompute_guides.py for faster updates.
Usage:
  python3 scripts/update_guides.py                    # update all (same as full build)
  python3 scripts/update_guides.py --since "2026-01-01"  # only verses updated since date
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import argparse

from lib.db import get_db


def get_changed_verses(conn, since=None):
    """Get IDs of verses whose connections have changed."""
    if since:
        # Get verses with connections created/updated after `since`
        rows = conn.execute("""
            SELECT DISTINCT c.source_verse as vid
            FROM connections c
            WHERE c.created_at >= ?
            UNION
            SELECT DISTINCT v.id as vid
            FROM verses v
            WHERE v.created_at >= ?
        """, (since, since)).fetchall()
    else:
        # All verses
        rows = conn.execute("SELECT id as vid FROM verses").fetchall()
    return [r["vid"] for r in rows]


def update_verse_guide(conn, vid):
    """Recalculate the passage guide for a single verse."""
    conns = conn.execute("""
        SELECT c.layer, c.type, c.subtype, c.strength, c.confidence,
               c.quality_level, c.p_value,
               c.target_verse, c.discovered_by,
               v.text_english as target_text,
               b.title as target_book
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
        ORDER BY c.strength DESC, c.layer
    """, (vid,)).fetchall()

    if not conns:
        return False  # No connections to cache

    by_layer = {}
    qualities = {}

    for c in conns:
        r = dict(c)
        layer = r["layer"]
        if layer not in by_layer:
            by_layer[layer] = []

        by_layer[layer].append({
            "type": r["type"],
            "subtype": r.get("subtype", ""),
            "strength": r["strength"],
            "confidence": r["confidence"],
            "quality": r.get("quality_level", "suggested"),
            "target": r["target_verse"],
            "target_book": r.get("target_book", ""),
            "discovered_by": r.get("discovered_by", "algorithm"),
        })

        ql = r.get("quality_level") or "suggested"
        qualities[ql] = qualities.get(ql, 0) + 1

    # Gematria summary
    gem = conn.execute("""
        SELECT COALESCE(SUM(value_standard), 0) as total_std,
               COUNT(*) as word_count
        FROM gematria WHERE verse_id = ?
    """, (vid,)).fetchone()

    grk = conn.execute("""
        SELECT COALESCE(SUM(value_standard), 0) as total,
               COUNT(*) as word_count
        FROM gematria_greek WHERE verse_id = ?
    """, (vid,)).fetchone()

    text_row = conn.execute(
        "SELECT text_english, text_hebrew, text_greek FROM verses WHERE id = ?",
        (vid,)
    ).fetchone()

    connections_json = json.dumps(by_layer)
    gematria_json = None
    if gem["total_std"] or grk["total"]:
        gematria_json = json.dumps({
            "total_standard": gem["total_std"],
            "hebrew_words": gem["word_count"],
            "greek_words": grk["word_count"],
            "greek_total": grk["total"],
        })

    quality_json = json.dumps(qualities)
    layer_count = len(by_layer)
    total_connections = len(conns)

    conn.execute("""
        INSERT OR REPLACE INTO passage_guides
            (verse_id, text_english, text_hebrew, text_greek,
             connections_json, gematria_json, quality_summary,
             layer_count, total_connections, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        vid,
        (text_row["text_english"] or "") if text_row else "",
        (text_row["text_hebrew"] or "") if text_row else "",
        (text_row["text_greek"] or "") if text_row else "",
        connections_json,
        gematria_json or "null",
        quality_json,
        layer_count,
        total_connections,
    ))
    return True


def main():
    parser = argparse.ArgumentParser(description="Incremental passage guide update")
    parser.add_argument("--since", type=str, default="",
                        help="Only update verses changed since this date (ISO format)")
    parser.add_argument("--verbose", action="store_true", help="Show each verse")
    args = parser.parse_args()

    conn = get_db()

    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS passage_guides (
            verse_id TEXT PRIMARY KEY REFERENCES verses(id),
            text_english TEXT, text_hebrew TEXT, text_greek TEXT,
            connections_json TEXT, gematria_json TEXT,
            quality_summary TEXT, layer_count INTEGER,
            total_connections INTEGER,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    since = args.since if args.since else None
    verse_ids = get_changed_verses(conn, since)
    total = len(verse_ids)

    if since:
        print(f"Incrementally updating {total} verses changed since {since}...")
    else:
        print(f"Full update: {total} verses...")

    updated = 0
    for i, vid in enumerate(verse_ids):
        if update_verse_guide(conn, vid):
            updated += 1

        if (i + 1) % 1000 == 0:
            conn.commit()
            print(f"  {i+1}/{total}...", flush=True)

    conn.commit()
    print(f"\nComplete: {updated} passage guides updated")

    count = conn.execute("SELECT COUNT(*) FROM passage_guides").fetchone()[0]
    print(f"Total passage guides in table: {count}")


if __name__ == "__main__":
    main()
