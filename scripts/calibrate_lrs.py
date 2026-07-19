"""
Calibrate likelihood ratios empirically — validates DISCOVERY_LR and TYPE_LR values
against a held-out gold standard (TSK cross-references as ground truth).

Outputs a report showing which LRs are over/under-estimated and suggests corrected values.

Usage:
    python3 scripts/calibrate_lrs.py                    # Full calibration
    python3 scripts/calibrate_lrs.py --quick            # Sample only
    python3 scripts/calibrate_lrs.py --update           # Apply corrected values
"""

import argparse
import logging
import sys
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# TSK connections are treated as ground truth (high-precision scholarly cross-references)
GOLD_STANDARD = "tsk"


def get_db():
    from lib.db import get_db
    return get_db()


def compute_discovery_lrs(conn, quick=False):
    """Compute empirical LRs for each discovery method.
    
    For each discovery method, compare its precision against the gold standard (TSK).
    LR = P(connection is real | discovered_by=X) / P(connection is real | baseline)
    
    Since we use TSK as gold standard, a method's LR = precision_ratio / baseline_precision.
    """
    logger.info("Computing empirical DISCOVERY_LR values...")

    # Get total connections per discovery method
    total = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
    gold_total = conn.execute("SELECT COUNT(*) FROM connections WHERE discovered_by=?", (GOLD_STANDARD,)).fetchone()[0]
    
    rows = conn.execute("""
        SELECT discovered_by, COUNT(*) as cnt,
               AVG(strength) as avg_strength,
               AVG(confidence) as avg_confidence
        FROM connections
        GROUP BY discovered_by
        ORDER BY cnt DESC
    """).fetchall()

    if not rows:
        logger.warning("No connections found in database")
        return

    # Use TSK precision as baseline
    gold_row = [r for r in rows if r["discovered_by"] == GOLD_STANDARD]
    if not gold_row:
        logger.warning("No TSK connections found — can't establish gold standard baseline")
        return

    gold_density = gold_row[0]["cnt"] / max(gold_total, 1)

    print(f"\n{'Discovery Method':<25} {'Count':>8} {'Avg Strength':>14} {'LR (current)':>13} {'LR (empirical)':>15} {'Note':<20}")
    print("-" * 95)

    from lib.controls.calibration import DISCOVERY_LR

    for row in rows:
        method = row["discovered_by"]
        count = row["cnt"]
        avg_strength = round(row["avg_strength"], 2) if row["avg_strength"] else 0
        density = count / max(total, 1)
        
        # Empirical LR = density ratio relative to gold standard
        lr_empirical = round(density / max(gold_density, 0.001), 1) if gold_density > 0 else 1.0
        lr_current = DISCOVERY_LR.get(method, 1.2)
        
        note = ""
        diff_ratio = lr_empirical / max(lr_current, 0.01)
        if diff_ratio > 1.5:
            note = f"↑ UNDER (emp {lr_empirical:.1f}x)"
        elif diff_ratio < 0.5:
            note = f"↓ OVER (emp {lr_empirical:.1f}x)"
        else:
            note = "✓ OK"

        print(f"{method:<25} {count:>8} {avg_strength:>14} {lr_current:>13.1f}x {lr_empirical:>15.1f}x {note:<20}")

        if quick:
            break


def compute_type_lrs(conn, quick=False):
    """Compute empirical LRs for connection types."""
    logger.info("Computing empirical TYPE_LR values...")

    rows = conn.execute("""
        SELECT c.type, 
               COUNT(*) as cnt,
               AVG(c.strength) as avg_strength,
               AVG(CASE WHEN c.discovered_by = ? THEN 1.0 ELSE 0.0 END) as gold_ratio
        FROM connections c
        GROUP BY c.type
        ORDER BY cnt DESC
    """, (GOLD_STANDARD,)).fetchall()

    if not rows:
        return

    # Baseline: overall ratio of TSK connections
    gold_total = conn.execute("SELECT COUNT(*) FROM connections WHERE discovered_by=?", (GOLD_STANDARD,)).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
    baseline_gold_ratio = gold_total / max(total, 1)

    print(f"\n{'Type':<30} {'Count':>8} {'Avg Str':>8} {'Gold%':>8} {'LR (cur)':>10} {'LR (emp)':>10} {'Note':<15}")
    print("-" * 89)

    from lib.controls.calibration import TYPE_LR

    for row in rows[:30] if quick else rows:
        ctype = row["type"]
        count = row["cnt"]
        avg_str = round(row["avg_strength"], 2) if row["avg_strength"] else 0
        gold_ratio = row["gold_ratio"] or 0

        lr_empirical = round(gold_ratio / max(baseline_gold_ratio, 0.001), 1) if baseline_gold_ratio > 0 else 1.0
        lr_current = TYPE_LR.get(ctype, 1.5)

        note = ""
        diff = lr_empirical / max(lr_current, 0.01)
        if diff > 1.5:
            note = "↑ UNDER"
        elif diff < 0.5:
            note = "↓ OVER"
        else:
            note = "✓ OK"

        print(f"{ctype:<30} {count:>8} {avg_str:>8} {gold_ratio:>7.1%} {lr_current:>10.1f}x {lr_empirical:>10.1f}x {note:<15}")


def generate_suggested_values(conn):
    """Generate corrected LR values as Python dicts for copy-paste."""
    from lib.controls.calibration import DISCOVERY_LR, TYPE_LR

    total = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]
    gold_total = conn.execute("SELECT COUNT(*) FROM connections WHERE discovered_by=?", (GOLD_STANDARD,)).fetchone()[0]
    baseline_gold_ratio = gold_total / max(total, 1)

    # Discovery LRs
    rows = conn.execute("""
        SELECT discovered_by, COUNT(*) as cnt
        FROM connections
        GROUP BY discovered_by
        ORDER BY cnt DESC
    """).fetchall()

    print("\n# Suggested DISCOVERY_LR values (empirically calibrated):")
    print("DISCOVERY_LR = {")
    for row in rows:
        method = row["discovered_by"]
        density = row["cnt"] / max(total, 1)
        lr_emp = round(density / max(baseline_gold_ratio, 0.001), 1)
        current = DISCOVERY_LR.get(method, 1.2)
        if lr_emp != current:
            print(f'    "{method}": {lr_emp:.1f},  # was {current:.1f}')
        else:
            print(f'    "{method}": {lr_emp:.1f},')
    print("}")

    # Type LRs (top 30)
    type_rows = conn.execute("""
        SELECT c.type, COUNT(*) as cnt,
               AVG(CASE WHEN c.discovered_by = ? THEN 1.0 ELSE 0.0 END) as gold_ratio
        FROM connections c
        GROUP BY c.type
        HAVING cnt > 100
        ORDER BY cnt DESC
    """, (GOLD_STANDARD,)).fetchall()

    print("\n# Suggested TYPE_LR values (empirically calibrated, top types):")
    print("TYPE_LR = {")
    for row in type_rows:
        ctype = row["type"]
        gold_ratio = row["gold_ratio"] or 0
        lr_emp = round(gold_ratio / max(baseline_gold_ratio, 0.001), 1)
        current = TYPE_LR.get(ctype, 1.5)
        if lr_emp != current:
            print(f'    "{ctype}": {lr_emp:.1f},  # was {current:.1f}')
        else:
            print(f'    "{ctype}": {lr_emp:.1f},')
    print("}")


def main():
    parser = argparse.ArgumentParser(description="Calibrate likelihood ratios empirically")
    parser.add_argument("--quick", action="store_true", help="Sample only (top results)")
    parser.add_argument("--update", action="store_true", help="Apply corrected values to calibration.py")
    args = parser.parse_args()

    conn = get_db()

    compute_discovery_lrs(conn, quick=args.quick)
    compute_type_lrs(conn, quick=args.quick)
    
    print("\n" + "=" * 60)
    print("RECOMMENDED UPDATES")
    print("=" * 60)
    generate_suggested_values(conn)

    if args.update:
        logger.info("Auto-update not yet implemented — copy the suggested values manually")
        logger.info("Target: lib/controls/calibration.py DISCOVERY_LR and TYPE_LR dicts")

    conn.close()


if __name__ == "__main__":
    main()
