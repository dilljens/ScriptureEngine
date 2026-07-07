#!/usr/bin/env python3
"""C1: Build the knowledge domain from high-quality connections.

Populates the knowledge_items table with connections that meet
minimum quality thresholds (star_rating >= 3 by default).

Uses the multi-signal calibration system rather than raw quality_level
column — catches many more types and layers.
"""

import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.db import get_db, SCHEMA_SQL
from lib.connections.pardes import get_pardes_level_for_type
from lib.controls.calibration import rate_connection_row

BLOOM_MAP = {
    "p'shat": "remember",
    "remez": "understand",
    "drash": "analyze",
    "sod": "evaluate",
}

MIN_STARS = 3


def ensure_table(conn):
    """Create the knowledge_items table if it doesn't exist."""
    conn.executescript(SCHEMA_SQL)
    conn.commit()


def build_domain(min_stars=MIN_STARS):
    conn = get_db()
    ensure_table(conn)

    # Clear existing
    conn.execute("DELETE FROM knowledge_prerequisites")
    conn.execute("DELETE FROM knowledge_items")
    conn.commit()

    total_all = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]

    # Process in batches — collect qualifying items, then bulk insert
    BATCH_SIZE = 5000
    offset = 0
    inserted = 0
    pardes_counts = {}
    type_counts = {}
    layer_counts = {}

    start_time = time.time()

    while True:
        rows = conn.execute(f"""
            SELECT source_verse, type, target_verse, quality_level,
                   layer, confidence, discovered_by, confirmation_count,
                   metadata
            FROM connections
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """).fetchall()

        if not rows:
            break

        batch = []
        for row in rows:
            rd = dict(row)
            try:
                signals = rate_connection_row(rd)
            except Exception:
                continue

            if signals["stars"] < min_stars:
                continue

            conn_type = rd["type"]
            quality_score = signals["overall_confidence"]
            star_rating = signals["stars"]
            pardes = get_pardes_level_for_type(conn_type)
            difficulty = round(1.0 - quality_score, 3)
            bloom = BLOOM_MAP.get(pardes, "remember")

            meta = rd.get("metadata", "{}")
            if isinstance(meta, dict):
                meta = json.dumps(meta)
            elif not isinstance(meta, str):
                meta = "{}"

            batch.append((
                rd["source_verse"],
                conn_type,
                rd["target_verse"],
                rd["quality_level"],
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

        offset += BATCH_SIZE
        pct = min(100, offset / total_all * 100)
        elapsed = time.time() - start_time
        rate = offset / elapsed if elapsed > 0 else 0
        print(f"\r  {offset:>8,}/{total_all:,} ({pct:.0f}%) | {inserted:,} items | {rate:,.0f} rows/s", end="", flush=True)

    print()
    elapsed = time.time() - start_time

    # Summary
    layers_str = ", ".join(f"{k}={v}" for k, v in sorted(layer_counts.items(), key=lambda x: -x[1]))
    types_str = ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items(), key=lambda x: -x[1]))
    pardes_str = ", ".join(f"{k}={v}" for k, v in sorted(pardes_counts.items(), key=lambda x: -x[1]))

    print(f"\nDomain built: {inserted:,} items from {total_all:,} total connections ({elapsed:.1f}s)")
    print(f"  Layers: {layers_str}")
    print(f"  PaRDeS: {pardes_str}")
    print(f"  Types:  {types_str}")
    print(f"  Threshold: star_rating >= {min_stars}")

    conn.close()
    return inserted


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build knowledge domain from connections")
    parser.add_argument("--min-stars", type=int, default=MIN_STARS, help="Minimum star rating")
    args = parser.parse_args()
    build_domain(min_stars=args.min_stars)
