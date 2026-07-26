#!/usr/bin/env python3
"""
Pipeline scheduler — runs generators on a schedule.

Usage:
  python3 scripts/schedule.py                # Run all due pipeline steps
  python3 scripts/schedule.py --status       # Show pipeline status
  python3 scripts/schedule.py --list         # Show pipeline config
  python3 scripts/schedule.py --tier idle    # Run only idle-tier generators
  python3 scripts/schedule.py --name "Linguistic — Same Lemma"  # Run one generator
  python3 scripts/schedule.py --init         # Seed generator_meta (mark all as never run)

Config: schedule.yaml (top-level project dir)
Meta:   generator_meta table in the scripture DB
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

# ── Config ──────────────────────────────────────────────────────────────────

SCHEDULE_PATH = os.path.join(os.path.dirname(__file__), "..", "schedule.yaml")
DB_PATH = os.environ.get(
    "SCRIPTURE_DB",
    os.path.join(os.path.dirname(__file__), "..", "data", "processed", "scripture.db"),
)


def load_schedule(path=SCHEDULE_PATH):
    """Load the schedule config from YAML."""
    if not os.path.exists(path):
        print(f"Schedule file not found: {path}")
        print("Create schedule.yaml in the project root, or run with --init")
        sys.exit(1)
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("pipeline", [])


def get_db(path=DB_PATH):
    """Get a database connection."""
    import sqlite3

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ── Status helpers ──────────────────────────────────────────────────────────


def get_generator_meta(conn):
    """Load all generator_meta records into a dict keyed by name."""
    try:
        rows = conn.execute(
            "SELECT generator_name, last_run_at, source_hash, connection_count, duration_ms "
            "FROM generator_meta"
        ).fetchall()
        return {r["generator_name"]: dict(r) for r in rows}
    except Exception:
        return {}


def is_due(meta, interval_hours):
    """Check if a generator is due based on its last run time and interval.

    Args:
        meta: generator_meta dict or None (never run).
        interval_hours: Interval in hours. 0 = manual trigger only (never auto).

    Returns:
        True if due, False if not.
    """
    if interval_hours == 0:
        return False  # Manual trigger only
    if meta is None:
        return True  # Never run — always due
    last_run = meta.get("last_run_at")
    if not last_run:
        return True
    try:
        # Parse datetime string (format from datetime('now') is 'YYYY-MM-DD HH:MM:SS')
        last = datetime.strptime(last_run, "%Y-%m-%d %H:%M:%S")
        elapsed_h = (datetime.now() - last).total_seconds() / 3600
        return elapsed_h >= interval_hours
    except ValueError:
        return True  # Can't parse — run to be safe


def steps_due(conn, steps, tier_filter=None, name_filter=None):
    """For each pipeline step, determine which generators are due.

    Args:
        conn: DB connection.
        steps: List of pipeline step dicts from schedule.yaml.
        tier_filter: Optional tier name to filter steps.
        name_filter: Optional generator name to run exactly one.

    Returns:
        List of (step, [generator_name, ...]) tuples for due generators.
    """
    from generators import list_generators

    meta = get_generator_meta(conn)
    results = []

    for step in steps:
        step_name = step.get("name", "?")
        tier = step.get("tier")
        interval = step.get("interval_hours", 24)
        gen_filter = step.get("generators", ["auto"])

        if tier_filter and tier != tier_filter:
            continue

        # Resolve which generators this step covers
        if name_filter:
            # Running exactly one named generator
            candidates = [name_filter]
        elif gen_filter == ["all"]:
            candidates = [g["name"] for g in list_generators(automatic_only=True)]
        elif gen_filter == ["auto"]:
            candidates = [
                g["name"] for g in list_generators(tier=tier, automatic_only=True)
            ]
        else:
            candidates = gen_filter

        # Filter to due generators
        due = []
        for name in candidates:
            if name_filter:
                # Always run when explicitly named
                due.append(name)
            elif is_due(meta.get(name), interval):
                due.append(name)

        if due:
            results.append((step, due))

    return results


# ── CLI commands ────────────────────────────────────────────────────────────


def cmd_status(conn, steps):
    """Show pipeline status — which generators ran when."""
    from generators import list_generators

    meta = get_generator_meta(conn)
    all_gens = {g["name"]: g for g in list_generators()}

    print(f"{'Generator':45s} {'Tier':14s} {'Last Run':22s} {'Status':12s}")
    print("-" * 93)

    for gen_name, gen_info in sorted(all_gens.items()):
        gmeta = meta.get(gen_name)
        tier = gen_info.get("tier", "?")
        auto = gen_info.get("automatic", False)
        last = gmeta["last_run_at"] if gmeta else "— never run —"

        if gmeta:
            status = "ok" if gmeta.get("connection_count", 0) > 0 else "zero"
        else:
            status = "never"

        print(f"{gen_name:45s} {tier:14s} {last:22s} {status:12s}")

    # Summary by tier
    print()
    print("Tier distribution (actual runs):")
    for tier in ("lightweight", "idle", "periodic"):
        tier_gens = [n for n, g in all_gens.items() if g.get("tier") == tier]
        never = sum(1 for n in tier_gens if n not in meta or meta[n].get("last_run_at", "").startswith("1970"))
        ran = len(tier_gens) - never
        print(f"  {tier:14s}: {ran} ran, {never} never — {len(tier_gens)} total")


def cmd_list(steps):
    """Show the pipeline config."""
    print(f"{'Step':20s} {'Tier':14s} {'Interval':10s} {'Generators':20s} {'Description':40s}")
    print("-" * 110)
    for step in steps:
        name = step.get("name", "?")
        tier = step.get("tier") or "all"
        interval = f"{step.get('interval_hours', 0)}h"
        gens = ", ".join(step.get("generators", []))
        desc = step.get("description", "")
        if interval == "0h":
            interval = "manual"
        print(f"{name:20s} {tier:14s} {interval:10s} {gens:20s} {desc:40s}")


def cmd_run(conn, steps, tier_filter=None, name_filter=None, incremental=True):
    """Run due generators."""
    from generators import run_generator

    due = steps_due(conn, steps, tier_filter, name_filter)
    total_due = sum(len(gens) for _, gens in due)

    if total_due == 0:
        if name_filter:
            print(f"No generator '{name_filter}' found")
        else:
            msg = f"tier '{tier_filter}'" if tier_filter else "any tier"
            print(f"No generators due for {msg}. Use --status to check, --tier to force.")
        return

    # Preview
    print(f"Scheduled: {total_due} generator(s) due across {len(due)} step(s):")
    for step, gen_names in due:
        step_name = step.get("name", "?")
        print(f"  [{step_name}] {', '.join(gen_names[:5])}{'...' if len(gen_names) > 5 else ''}")
    print()

    total_connections = 0
    total_time = 0.0
    errors = []

    for step, gen_names in due:
        step_name = step.get("name", "?")
        print(f"── Step: {step_name} ──")
        for name in gen_names:
            t0 = time.time()
            result = run_generator(conn, name)
            elapsed = time.time() - t0

            if "error" in result:
                errors.append((name, result["error"]))
                print(f"  ✗ {name:50s} ERROR: {result['error']}")
            else:
                count = result.get("connections", 0)
                total_connections += count
                total_time += elapsed
                print(f"  ✓ {name:50s} {count:6d} connections  ({elapsed:.1f}s)")
        print()

    print(f"── Summary ──")
    print(f"  Total connections created: {total_connections}")
    print(f"  Total time:                {total_time:.1f}s")
    print(f"  Errors:                    {len(errors)}")
    for name, err in errors:
        print(f"    ✗ {name}: {err}")


def cmd_init(conn):
    """Seed generator_meta entries (mark all as 'never run')."""
    from generators import list_generators

    gens = list_generators()
    count = 0
    for g in gens:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO generator_meta (generator_name, last_run_at, source_hash, connection_count, duration_ms) "
                "VALUES (?, '1970-01-01 00:00:00', '', 0, 0)",
                (g["name"],),
            )
            count += 1
        except Exception:
            pass
    conn.commit()
    print(f"Seeded {count} generator_meta entries (all marked as never run)")


# ── Entry point ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Pipeline scheduler for scripture generators")
    parser.add_argument(
        "--status", action="store_true", help="Show pipeline status (last run times)"
    )
    parser.add_argument("--list", action="store_true", help="Show pipeline config")
    parser.add_argument("--tier", choices=["lightweight", "idle", "periodic"], help="Run only this tier")
    parser.add_argument("--name", type=str, help="Run exactly one generator by name")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Seed generator_meta table (mark all as never run)",
    )
    parser.add_argument(
        "--no-incremental",
        action="store_false",
        dest="incremental",
        help="Disable incremental mode (ignore source hash, force re-run)",
    )
    args = parser.parse_args()

    steps = load_schedule()
    conn = get_db()

    if args.init:
        cmd_init(conn)
    elif args.status:
        cmd_status(conn, steps)
    elif args.list:
        cmd_list(steps)
    elif args.name:
        # Running one named generator — run it directly, don't iterate steps
        from generators import run_generator
        t0 = time.time()
        result = run_generator(conn, args.name)
        elapsed = time.time() - t0
        if "error" in result:
            print(f"✗ {args.name}: {result['error']}")
        else:
            print(f"✓ {args.name}: {result.get('connections', 0)} connections in {elapsed:.1f}s")
    elif args.tier:
        cmd_run(conn, steps, tier_filter=args.tier, incremental=args.incremental)
    else:
        cmd_run(conn, steps, incremental=args.incremental)

    conn.close()


if __name__ == "__main__":
    main()
