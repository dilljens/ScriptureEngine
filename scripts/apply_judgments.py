#!/usr/bin/env python3
"""Apply agent-driven judgment files to the connections database.

Usage:
  python3 scripts/apply_judgments.py data/agent_connections/prophetic_fulfillment_judgments.json
  python3 scripts/apply_judgments.py data/agent_connections/*.json
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db


def apply_judgment_file(conn, filepath):
    """Read a judgment JSON file and insert all connections into the DB."""
    with open(filepath) as f:
        judgments = json.load(f)

    if not isinstance(judgments, list):
        print(f"  ERROR: {filepath} — expected JSON array, got {type(judgments).__name__}")
        return 0

    count = 0
    batch = []
    for j in judgments:
        source = j.get("source_verse", "")
        target = j.get("target_verse", "")
        layer = j.get("layer", "intertextual")
        conn_type = j.get("type", "")
        subtype = j.get("subtype", "")
        strength = j.get("strength", 0.5)
        confidence = j.get("confidence", 0.5)
        metadata = j.get("metadata", {})

        if not source or not target or not conn_type:
            continue

        batch.append((
            source, target, layer, conn_type, subtype,
            strength, confidence, "llm", json.dumps(metadata)
        ))
        count += 1

        if len(batch) >= 100:
            _batch_insert(conn, batch)
            batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  {filepath}: {count} connections applied")
    return count


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype,
             strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else []
    if not files:
        # Default: apply all files in data/agent_connections/
        files = sorted(glob.glob("data/agent_connections/*.json"))

    if not files:
        print("Usage: python3 scripts/apply_judgments.py <file1.json> [file2.json ...]")
        print("   or: python3 scripts/apply_judgments.py  (applies all data/agent_connections/*.json)")
        sys.exit(1)

    conn = get_db()
    total = 0
    for fp in files:
        if os.path.isfile(fp):
            total += apply_judgment_file(conn, fp)
        else:
            print(f"  Skipping {fp} — not found")

    conn.close()
    print(f"\n  Total: {total} connections applied")


if __name__ == "__main__":
    main()
