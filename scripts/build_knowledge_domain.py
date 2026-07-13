#!/usr/bin/env python3
"""C1: Build the knowledge domain from quality-filtered connections.

Populates the knowledge_items table with connections that meet
raw quality_level thresholds. Uses a simple SQL WHERE filter
instead of computed star ratings.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.connections.pardes import get_pardes_level_for_type
from lib.db import SCHEMA_SQL, get_db

BLOOM_MAP = {
    "p'shat": "remember",
    "remez": "understand",
    "drash": "analyze",
    "sod": "evaluate",
}

QUALITY_LEVELS = ("verified", "strong", "probable", "scholarly", "suggested")


def ensure_table(conn):
    """Create the knowledge_items table if it doesn't exist."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def build_domain():
    conn = get_db()
    ensure_table(conn)

    # Clear existing
    conn.execute("DELETE FROM knowledge_prerequisites")
    conn.execute("DELETE FROM knowledge_items")
    conn.commit()

    # Build from raw quality_level filter — fast, all in SQL
    placeholders = ",".join("?" for _ in QUALITY_LEVELS)
    total_all = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]

    rows = conn.execute(f"""
        SELECT source_verse, type, target_verse, quality_level,
               layer, confidence, discovered_by, metadata
        FROM connections
        WHERE quality_level IN ({placeholders})
        ORDER BY source_verse
    """, QUALITY_LEVELS).fetchall()

    total_candidates = len(rows)
    BATCH_SIZE = 2000
    batch = []
    inserted = 0
    pardes_counts = {}
    type_counts = {}
    layer_counts = {}
    quality_counts = {}

    for rd in rows:
        conn_type = rd["type"]
        quality_level = rd["quality_level"]
        pardes = get_pardes_level_for_type(conn_type)
        difficulty = round(1.0 - rd["confidence"], 3) if rd["confidence"] else 0.5
        bloom = BLOOM_MAP.get(pardes, "remember")

        meta = rd["metadata"]
        if isinstance(meta, dict):
            meta = json.dumps(meta)
        elif not isinstance(meta, str):
            meta = "{}"

        star_rating = {"pattern": 1, "suggested": 2, "probable": 3,
                       "strong": 4, "verified": 5, "scholarly": 5}.get(quality_level, 2)

        batch.append((
            rd["source_verse"],
            conn_type,
            rd["target_verse"],
            quality_level,
            star_rating,
            pardes,
            rd["layer"],
            difficulty,
            bloom,
            meta,
        ))

        pardes_counts[pardes] = pardes_counts.get(pardes, 0) + 1
        type_counts[conn_type] = type_counts.get(conn_type, 0) + 1
        layer_counts[rd["layer"]] = layer_counts.get(rd["layer"], 0) + 1
        quality_counts[quality_level] = quality_counts.get(quality_level, 0) + 1

        if len(batch) >= BATCH_SIZE:
            conn.executemany("""
                INSERT OR IGNORE INTO knowledge_items
                    (verse_id, connection_type, target_verse,
                     quality_level, star_rating, pa_r_de_s_level,
                     layer, difficulty, bloom_level, item_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            inserted += len(batch)
            batch = []

    if batch:
        conn.executemany("""
            INSERT OR IGNORE INTO knowledge_items
                (verse_id, connection_type, target_verse,
                 quality_level, star_rating, pa_r_de_s_level,
                 layer, difficulty, bloom_level, item_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        inserted += len(batch)

    # Summary
    qual_str = ", ".join(f"{k}={v}" for k, v in sorted(quality_counts.items(), key=lambda x: -x[1]))
    layers_str = ", ".join(f"{k}={v}" for k, v in sorted(layer_counts.items(), key=lambda x: -x[1]))
    types_str = ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))
    pardes_str = ", ".join(f"{k}={v}" for k, v in sorted(pardes_counts.items(), key=lambda x: -x[1]))

    print(f"Domain built: {inserted:,} items from {total_candidates:,} candidates ({total_all:,} total)")
    print(f"  Quality: {qual_str}")
    print(f"  Layers:  {layers_str}")
    print(f"  PaRDeS:  {pardes_str}")
    print(f"  Types:   {types_str}")

    conn.close()
    return inserted


if __name__ == "__main__":
    build_domain()
