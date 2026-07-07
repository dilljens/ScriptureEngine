#!/usr/bin/env python3
"""Pre-compute passage guides — instant per-verse connection context.

Logos Pattern: Instead of querying connections live via JOINs,
pre-compute a JSON context for every verse once, stored in a
passage_guides table. The UI or API serves these with a single
indexed lookup — no joins, no live aggregation.
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

COMPUTED_TABLE = "passage_guides"
COMPUTED_SCHEMA = """
    CREATE TABLE IF NOT EXISTS passage_guides (
        verse_id TEXT PRIMARY KEY REFERENCES verses(id),
        text_english TEXT,
        text_hebrew TEXT,
        text_greek TEXT,
        connections_json TEXT,
        gematria_json TEXT,
        isopsephy_json TEXT,
        quality_summary TEXT,
        layer_count INTEGER,
        total_connections INTEGER,
        updated_at TEXT DEFAULT (datetime('now'))
    )
"""


def precompute_all(conn):
    """Build the passage_guides table with pre-joined connection data."""
    from lib.connections.pardes import get_pardes_level
    from lib.controls.calibration import get_quality_stars

    # Create table
    conn.execute(f"DROP TABLE IF EXISTS {COMPUTED_TABLE}")
    conn.executescript(COMPUTED_SCHEMA)
    conn.commit()

    # Get all verses
    verses = conn.execute("""
        SELECT id, text_english, text_hebrew, text_greek,
               book_id, chapter, verse
        FROM verses
    """).fetchall()

    batch = []
    count = 0
    total = len(verses)

    for row in verses:
        vid = row["id"]

        # Get connections for this verse
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
            continue

        # Group by layer for structured JSON
        by_layer = {}
        layer_counts = {}

        for c in conns:
            r = dict(c)
            layer = r["layer"]
            if layer not in by_layer:
                by_layer[layer] = []
                layer_counts[layer] = 0

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
            layer_counts[layer] += 1

        # Quality summary across all connections for this verse
        qualities = {}
        for c in conns:
            ql = c["quality_level"] or "suggested"
            qualities[ql] = qualities.get(ql, 0) + 1

        # Get gematria summary
        gem = conn.execute("""
            SELECT SUM(value_standard) as total_std,
                   COUNT(*) as word_count
            FROM gematria WHERE verse_id = ?
        """, (vid,)).fetchone()

        # Get Greek isopsephy summary
        grk = conn.execute("""
            SELECT SUM(value_standard) as total,
                   COUNT(*) as word_count
            FROM gematria_greek WHERE verse_id = ?
        """, (vid,)).fetchone()

        guide = {
            "verse_id": vid,
            "text_english": row["text_english"],
            "text_hebrew": row["text_hebrew"],
            "text_greek": row["text_greek"],
            "connections": by_layer,
            "gematria": {
                "total_standard": gem["total_std"] or 0,
                "hebrew_words": gem["word_count"] or 0,
                "greek_words": grk["word_count"] or 0,
                "greek_total": grk["total"] or 0,
            } if (gem["total_std"] or grk["total"]) else None,
            "quality_summary": qualities,
            "layer_count": len(by_layer),
            "total_connections": len(conns),
            "pardes": {},
        }

        # Add PaRDeS distribution
        for layer, items in by_layer.items():
            for item in items:
                lvl = get_pardes_level(layer, item["type"])
                if lvl not in guide["pardes"]:
                    guide["pardes"][lvl] = 0
                guide["pardes"][lvl] += 1

        connections_json = json.dumps(guide["connections"])
        gematria_json = json.dumps(guide["gematria"]) if guide["gematria"] else "null"
        quality_json = json.dumps(qualities)

        batch.append((
            vid, row["text_english"], row["text_hebrew"] or "",
            row["text_greek"] or "", connections_json, gematria_json,
            quality_json, guide["layer_count"], guide["total_connections"]
        ))

        count += 1
        if len(batch) >= 1000:
            _batch_insert(conn, batch)
            batch = []
            print(f"  {count}/{total} verses...", flush=True)

    if batch:
        _batch_insert(conn, batch)

    print(f"  Pre-computed {count} passage guides", flush=True)


def _batch_insert(conn, batch):
    conn.executemany(f"""
        INSERT INTO {COMPUTED_TABLE}
            (verse_id, text_english, text_hebrew, text_greek,
             connections_json, gematria_json, quality_summary,
             layer_count, total_connections)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def main():
    conn = get_db()
    print("=" * 60)
    print("  Pre-computing Passage Guides (Logos Pattern)")
    print("=" * 60)
    print()

    precompute_all(conn)

    count = conn.execute(f"SELECT COUNT(*) as c FROM {COMPUTED_TABLE}").fetchone()["c"]
    print(f"\n  {count} passage guides ready")
    print(f"  Query: SELECT * FROM passage_guides WHERE verse_id = ?")

    # Show sample
    sample = conn.execute("""
        SELECT verse_id, total_connections, layer_count
        FROM passage_guides WHERE total_connections > 0
        LIMIT 1
    """).fetchone()
    if sample:
        print(f"  Sample: {sample['verse_id']} — {sample['total_connections']} connections across {sample['layer_count']} layers")

    conn.close()


if __name__ == "__main__":
    main()
