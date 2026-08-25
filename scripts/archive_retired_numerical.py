#!/usr/bin/env python3
"""Archive or restore retired numerical connections (plan Track B3).

Moves rows whose connection type is in RETIRED_NUMERICAL_TYPES out of
`connections` into `archived_connections` (archive_reason =
'track_b3_retired_numerical'), so old noisy numerical matches stop appearing
in search/graph/chat while remaining fully restorable. Idempotent: a second
--apply finds zero rows and changes nothing.

The hermeneutic column has no counterpart in archived_connections, so it is
folded into metadata JSON before archiving — nothing is lost.

Usage:
    python3 scripts/archive_retired_numerical.py           # dry run (default)
    python3 scripts/archive_retired_numerical.py --apply   # archive rows
    python3 scripts/archive_retired_numerical.py --restore # undo an --apply
"""

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.controls.calibration import RETIRED_NUMERICAL_TYPES  # noqa: E402
from lib.db import DEFAULT_DB_PATH, get_db  # noqa: E402

ARCHIVE_REASON = "track_b3_retired_numerical"


def count_pending(conn) -> int:
    placeholders = ",".join("?" for _ in RETIRED_NUMERICAL_TYPES)
    return conn.execute(
        f"SELECT COUNT(*) FROM connections WHERE type IN ({placeholders})",
        tuple(RETIRED_NUMERICAL_TYPES),
    ).fetchone()[0]


def apply_archive(conn) -> int:
    total = count_pending(conn)
    if not total:
        print("Nothing to archive (already applied).")
        return 0
    placeholders = ",".join("?" for _ in RETIRED_NUMERICAL_TYPES)
    rows = conn.execute(
        f"SELECT id, source_verse, target_verse, layer, type, subtype, strength, "
        f"confidence, discovered_by, metadata, hermeneutic "
        f"FROM connections WHERE type IN ({placeholders})",
        tuple(RETIRED_NUMERICAL_TYPES),
    ).fetchall()
    with conn:
        for r in rows:
            meta = json.loads(r["metadata"] or "{}")
            if r["hermeneutic"]:
                meta["hermeneutic"] = r["hermeneutic"]
            conn.execute(
                "INSERT INTO archived_connections (source_verse, target_verse, "
                "layer, type, subtype, strength, confidence, discovered_by, "
                "metadata, archive_reason) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (r["source_verse"], r["target_verse"], r["layer"], r["type"],
                 r["subtype"], r["strength"], r["confidence"],
                 r["discovered_by"], json.dumps(meta), ARCHIVE_REASON),
            )
        conn.execute(
            f"DELETE FROM connections WHERE type IN ({placeholders})",
            tuple(RETIRED_NUMERICAL_TYPES),
        )
    print(f"Archived {len(rows):,d} retired-numerical connections.")
    return len(rows)


def restore(conn) -> int:
    rows = conn.execute(
        "SELECT id, source_verse, target_verse, layer, type, subtype, strength, "
        "confidence, discovered_by, metadata FROM archived_connections "
        "WHERE archive_reason = ?",
        (ARCHIVE_REASON,),
    ).fetchall()
    if not rows:
        print("Nothing to restore.")
        return 0
    with conn:
        for r in rows:
            meta = json.loads(r["metadata"] or "{}")
            hermeneutic = meta.pop("hermeneutic", None)
            conn.execute(
                "INSERT OR IGNORE INTO connections (source_verse, target_verse, "
                "layer, type, subtype, strength, confidence, discovered_by, "
                "metadata, hermeneutic) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (r["source_verse"], r["target_verse"], r["layer"], r["type"],
                 r["subtype"], r["strength"], r["confidence"],
                 r["discovered_by"], json.dumps(meta), hermeneutic),
            )
        conn.execute(
            "DELETE FROM archived_connections WHERE archive_reason = ?",
            (ARCHIVE_REASON,),
        )
    print(f"Restored {len(rows):,d} connections from archive.")
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="perform the archive")
    group.add_argument("--restore", action="store_true", help="undo --apply")
    args = parser.parse_args()

    conn = get_db(DEFAULT_DB_PATH)
    if args.apply:
        apply_archive(conn)
    elif args.restore:
        restore(conn)
    else:
        pending = count_pending(conn)
        already = conn.execute(
            "SELECT COUNT(*) FROM archived_connections WHERE archive_reason = ?",
            (ARCHIVE_REASON,),
        ).fetchone()[0]
        print(f"Dry run: {pending:,d} retired-numerical rows would be archived "
              f"({already:,d} already archived). Re-run with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
