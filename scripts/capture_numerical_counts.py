#!/usr/bin/env python3
"""Capture pre-migration connection counts for plan Track B3.

Writes docs/plans/b3-numerical-premigration-counts.json with per-type row
counts for every numerical-layer connection (retired AND retained), so the
post-migration graph regression has an exact baseline. Read-only.

Usage:
    python3 scripts/capture_numerical_counts.py            # write artifact
    python3 scripts/capture_numerical_counts.py --stdout   # print only
"""

import argparse
import datetime
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.controls.calibration import (  # noqa: E402
    RETIRED_NUMERICAL_TYPES,
    RETAINED_NUMERICAL_TYPES,
)
from lib.db import DEFAULT_DB_PATH, get_db  # noqa: E402

ARTIFACT = BASE_DIR / "docs" / "plans" / "b3-numerical-premigration-counts.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true", help="print table only")
    args = parser.parse_args()

    conn = get_db(DEFAULT_DB_PATH)
    types = sorted(RETIRED_NUMERICAL_TYPES | RETAINED_NUMERICAL_TYPES)
    counts = {}
    for t in types:
        counts[t] = conn.execute(
            "SELECT COUNT(*) FROM connections WHERE type = ?", (t,)
        ).fetchone()[0]
    layer_total = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE layer = 'numerical'"
    ).fetchone()[0]

    report = {
        "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "database": str(DEFAULT_DB_PATH),
        "retired_types": sorted(RETIRED_NUMERICAL_TYPES),
        "retained_types": sorted(RETAINED_NUMERICAL_TYPES),
        "counts_by_type": counts,
        "retired_total": sum(counts.get(t, 0) for t in RETIRED_NUMERICAL_TYPES),
        "numerical_layer_total": layer_total,
        # Types present in the layer but outside both lists (informational)
        "other_numerical_types": {
            row[0]: row[1]
            for row in conn.execute(
                "SELECT type, COUNT(*) FROM connections WHERE layer = 'numerical' "
                "GROUP BY type"
            ).fetchall()
            if row[0] not in types
        },
    }

    table = "\n".join(
        f"  {t:32s} {report['counts_by_type'].get(t, 0):>9,d}"
        + ("   [RETIRED]" if t in RETIRED_NUMERICAL_TYPES else "")
        for t in types
    )
    print(f"Numerical connection counts ({report['numerical_layer_total']:,d} total):\n{table}")
    print(f"  {'RETIRED TOTAL':32s} {report['retired_total']:>9,d}")

    if not args.stdout:
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nArtifact written: {ARTIFACT.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
