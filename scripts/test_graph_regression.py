#!/usr/bin/env python3
"""Graph regression tests — run after any data import or generator run.

Validates connection counts, layer distributions, quality levels,
tradition labels, and data integrity.

Usage:
    python3 scripts/test_graph_regression.py
    python3 scripts/test_graph_regression.py --verbose
"""
import sys, os, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db

# Baseline minimums — update when regenerating
MIN_LAYER_COUNTS = {
    "linguistic": 50000,
    "numerical": 100000,
    "intertextual": 20000,
    "structural": 10000,
    "interpretive": 5000,
    "symbolic": 1000,
    "textual": 5000,
    "geographic": 1000,
    "chronological": 1000,
    "frequency": 10000,
    "sod": 5000,
}

VALID_QUALITY = {"low", "suggested", "probable", "strong", "certain", "pattern", "verified", "scholarly"}
VALID_TRADITIONS = {"none", "jewish", "christian", "lds", "multiple"}


def run_all(verbose=False):
    conn = get_db()
    failures = []

    # 1. Total count
    total = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
    if total < 1000000:
        failures.append(f"Connection count too low: {total:,} (expected 1M+)")
    else:
        if verbose: print(f"  ✓ Total connections: {total:,}")

    # 2. Layer minimums
    layers = {
        r["layer"]: r["c"]
        for r in conn.execute(
            "SELECT layer, COUNT(*) as c FROM connections WHERE deprecated=0 GROUP BY layer"
        )
    }
    for layer, minimum in MIN_LAYER_COUNTS.items():
        actual = layers.get(layer, 0)
        if actual < minimum:
            failures.append(f"Layer {layer}: {actual:,} < minimum {minimum:,}")
        elif verbose:
            print(f"  ✓ Layer {layer}: {actual:,}")

    # 3. No null verse refs
    bad = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE deprecated=0 AND (source_verse IS NULL OR target_verse IS NULL)"
    ).fetchone()[0]
    if bad > 0:
        failures.append(f"{bad} connections with NULL verse refs")

    # 4. Foreign key integrity — skip virtual IDs
    bad = conn.execute("""
        SELECT COUNT(*) FROM connections c
        LEFT JOIN verses v ON v.id = c.source_verse
        WHERE c.deprecated=0 AND v.id IS NULL
        AND c.source_verse NOT LIKE 'tg:%'
        AND c.source_verse NOT LIKE 'bd:%'
        AND c.source_verse NOT LIKE 'sefaria:%'
        AND c.source_verse NOT LIKE 'name_72:%'
        AND c.source_verse NOT LIKE 'aoff%'
        AND c.source_verse NOT LIKE 'jsh%'
        AND c.source_verse NOT LIKE 'jsm%'
        AND c.source_verse NOT LIKE 'dss.%'
        AND c.source_verse NOT LIKE 'exod%'
        AND c.source_verse NOT LIKE 'jos.%'
        AND c.source_verse NOT LIKE 'zec.%'
        AND c.source_verse NOT LIKE 'deut%'
        AND c.source_verse NOT LIKE 'dc.%'
    """).fetchone()[0]
    if bad > 0:
        failures.append(f"{bad} connections with invalid source_verse")

    # 5. Duplicates — warn if >5%
    dupes = conn.execute("""
        SELECT COUNT(*) FROM (
            SELECT source_verse, target_verse, layer, type
            FROM connections WHERE deprecated=0
            GROUP BY 1,2,3,4 HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    dupe_pct = dupes / max(total, 1) * 100
    if dupe_pct > 5:
        failures.append(f"{dupes} duplicate groups ({dupe_pct:.2f}% of {total})")
    elif dupes > 0 and verbose:
        print(f"  ⚠  {dupes} duplicate groups ({dupe_pct:.2f}% of {total}) — within threshold")

    # 6. Quality levels
    bad_quality = conn.execute("""
        SELECT DISTINCT quality_level FROM connections WHERE deprecated=0
        AND quality_level NOT IN ({})
    """.format(','.join(f"'{q}'" for q in VALID_QUALITY))).fetchall()
    if bad_quality:
        failures.append(f"Invalid quality levels: {[r[0] for r in bad_quality]}")

    # 7. Tradition labels
    bad_trad = conn.execute("""
        SELECT DISTINCT tradition FROM connections WHERE deprecated=0
        AND tradition IS NOT NULL AND tradition NOT IN ({})
    """.format(','.join(f"'{t}'" for t in VALID_TRADITIONS))).fetchall()
    if bad_trad:
        failures.append(f"Invalid tradition labels: {[r[0] for r in bad_trad]}")

    # 8. DB integrity
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        failures.append(f"DB integrity check failed: {integrity}")

    # 9. Tradition distribution snapshot
    trad_dist = {
        r["tradition"]: r["cnt"]
        for r in conn.execute("""
            SELECT COALESCE(tradition, 'unset') as tradition, COUNT(*) as cnt
            FROM connections WHERE deprecated=0
            GROUP BY tradition ORDER BY cnt DESC
        """)
    }
    if verbose:
        print(f"\n  Tradition distribution:")
        for t, c in sorted(trad_dist.items(), key=lambda x: -x[1]):
            pct = c / total * 100
            print(f"    {t}: {c:,} ({pct:.1f}%)")

    # Report
    if verbose:
        print(f"\n  {'='*50}")
    if failures:
        print(f"\n  ❌ {len(failures)} FAILURES:")
        for f in failures:
            print(f"     ✗ {f}")
    else:
        print(f"\n  ✅ All graph regression checks passed")

    conn.close()
    return len(failures)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Graph regression tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Detailed output")
    args = parser.parse_args()
    sys.exit(run_all(verbose=args.verbose))
