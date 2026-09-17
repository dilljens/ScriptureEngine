#!/usr/bin/env python3
"""Re-level existing word nodes by frequency tier (one-shot migration).

Node ids embed the seed rank (vocab_<letters>_<idx>), so the tier follows
without re-seeding: 0-49 L4, 50-149 L5, 150-299 L6, 300+ L7.
Mirrors wordTier() in frontend/src/lib/idle-game.js and tier_level() in
seed_hebrew_vocabulary.py. Idempotent — reruns change nothing.

Usage: python scripts/migrate_word_tiers.py [--db data/memorize.db] [--apply]
Default is dry-run (prints what WOULD change). Pass --apply to write.
"""
import argparse
import re
import sqlite3
import sys
from pathlib import Path


def tier_level(rank: int) -> int:
    if rank < 50:
        return 4
    if rank < 150:
        return 5
    if rank < 300:
        return 6
    return 7


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/memorize.db")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"DB not found: {db}")
        return 1
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT id, level FROM hebrew_nodes WHERE category='word'"
    ).fetchall()
    changes = []
    skipped = 0
    for nid, level in rows:
        m = re.search(r"_(\d+)$", nid or "")
        if not m:
            skipped += 1
            continue
        want = tier_level(int(m.group(1)))
        if want != level:
            changes.append((nid, level, want))
    print(f"word nodes: {len(rows)}, would re-level: {len(changes)}, no rank suffix: {skipped}")
    by_level: dict = {}
    for _, _, want in changes:
        by_level[want] = by_level.get(want, 0) + 1
    if by_level:
        print("  target levels:", dict(sorted(by_level.items())))
    if args.apply and changes:
        conn.executemany(
            "UPDATE hebrew_nodes SET level=? WHERE id=?",
            [(want, nid) for nid, _, want in changes],
        )
        conn.commit()
        print(f"  applied {len(changes)} updates")
    elif not args.apply:
        print("  dry-run (pass --apply to write)")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
