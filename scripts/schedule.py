"""
Pipeline scheduler — controls when generators and maintenance tasks run.

Reads schedule.yaml, tracks last-run times in last_run.json, and runs
any steps whose interval has elapsed.

Usage:
    python3 scripts/schedule.py                  # Run all due steps
    python3 scripts/schedule.py --status         # Show pipeline status
    python3 scripts/schedule.py --force          # Run all steps regardless
    python3 scripts/schedule.py --step <name>    # Run a specific step
    python3 scripts/schedule.py --revalidate-stale  # Find and flag stale connections
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SCHEDULE_FILE = Path(__file__).parent.parent / "schedule.yaml"
STATE_FILE = Path(__file__).parent.parent / "last_run.json"
PROJECT_ROOT = Path(__file__).parent.parent


def load_schedule():
    """Load pipeline schedule from YAML."""
    if not SCHEDULE_FILE.exists():
        logger.error("schedule.yaml not found at %s", SCHEDULE_FILE)
        return {"pipeline": [], "last_run": {}}
    try:
        import yaml
        with open(SCHEDULE_FILE) as f:
            return yaml.safe_load(f) or {"pipeline": [], "last_run": {}}
    except Exception as e:
        logger.error("Failed to load schedule: %s", e)
        return {"pipeline": [], "last_run": {}}


def load_state():
    """Load last-run timestamps from state file."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state):
    """Save last-run timestamps to state file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def is_step_due(step, last_runs, force=False):
    """Check if a pipeline step is due to run."""
    if force:
        return True
    name = step["name"]
    interval_days = step.get("interval_days", 0)

    if interval_days == 0:
        return False  # Manual-only step

    last_run = last_runs.get(name)
    if not last_run:
        return True  # Never run → due

    try:
        if isinstance(last_run, (int, float)):
            last_ts = last_run
        else:
            last_ts = datetime.fromisoformat(last_run).timestamp()
        elapsed_days = (time.time() - last_ts) / 86400
        return elapsed_days >= interval_days * 0.9  # 10% tolerance
    except (ValueError, TypeError):
        return True


def run_step(step, force=False):
    """Execute a single pipeline step."""
    name = step["name"]
    command = step.get("command", "")
    timeout = step.get("timeout_seconds", 300)
    depends_on = step.get("depends_on", [])
    tier = step.get("tier", "periodic")

    if not command:
        logger.warning("  [%s] no command defined, skipping", name)
        return False

    # Check dependencies
    for dep in depends_on:
        last_runs = load_state()
        if not last_runs.get(dep):
            logger.warning("  [%s] dependency '%s' has never run, skipping", name, dep)
            return False

    logger.info("  [%s] running (tier=%s, timeout=%ss)...", name, tier, timeout)

    t0 = time.time()
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = time.time() - t0

        if result.returncode == 0:
            logger.info("  [%s] completed in %.1fs", name, elapsed)
            if result.stdout:
                for line in result.stdout.strip().split("\n")[-5:]:
                    logger.info("    %s", line)
            return True
        else:
            logger.error("  [%s] failed (exit %d) after %.1fs", name, result.returncode, elapsed)
            if result.stderr:
                for line in result.stderr.strip().split("\n")[-10:]:
                    logger.error("    %s", line)
            return False

    except subprocess.TimeoutExpired:
        logger.error("  [%s] timed out after %ss", name, timeout)
        return False
    except Exception as e:
        logger.error("  [%s] error: %s", name, e)
        return False


def update_last_run(steps, results):
    """Update last-run timestamps for completed steps."""
    state = load_state()
    now = datetime.now(timezone.utc).isoformat()
    for step, success in zip(steps, results):
        if success:
            state[step["name"]] = now
    save_state(state)


def get_status():
    """Get pipeline status with staleness info."""
    schedule = load_schedule()
    last_runs = load_state()
    now = time.time()

    status = []
    for step in schedule.get("pipeline", []):
        name = step["name"]
        interval = step.get("interval_days", 0)
        last_run = last_runs.get(name)

        if last_run:
            if isinstance(last_run, (int, float)):
                last_ts = last_run
            else:
                last_ts = datetime.fromisoformat(last_run).timestamp()
            elapsed_days = (now - last_ts) / 86400
            due = elapsed_days >= interval * 0.9 if interval > 0 else False
        else:
            elapsed_days = None
            due = True

        status.append({
            "name": name,
            "interval_days": interval,
            "last_run": last_run,
            "days_since_last_run": round(elapsed_days, 1) if elapsed_days is not None else None,
            "due": due,
            "tier": step.get("tier", "periodic"),
        })

    return status


def revalidate_stale():
    """Find connections past their half-life and flag them for revalidation."""
    from lib.db import get_db
    from lib.controls.temporal import needs_revalidation as is_stale

    conn = get_db()

    # Count stale connections
    total = conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]

    # Check a sample for staleness
    rows = conn.execute("""
        SELECT id, discovered_by, created_at, confidence
        FROM connections
        WHERE quality_version < 1
        ORDER BY RANDOM() LIMIT 1000
    """).fetchall()

    stale_count = 0
    for row in rows:
        try:
            if is_stale(row["confidence"], row["discovered_by"], row["created_at"]):
                stale_count += 1
                conn.execute(
                    "UPDATE connections SET quality_version = -1 WHERE id = ?",
                    (row["id"],),
                )
        except Exception:
            pass

    conn.commit()

    # Layer distribution
    layer_stats = conn.execute("""
        SELECT layer, COUNT(*) as cnt,
               SUM(CASE WHEN quality_version < 0 THEN 1 ELSE 0 END) as stale
        FROM connections
        GROUP BY layer ORDER BY cnt DESC LIMIT 10
    """).fetchall()

    conn.close()

    return {
        "total_connections": total,
        "sampled": len(rows),
        "stale_in_sample": stale_count,
        "stale_pct": round(stale_count / max(len(rows), 1) * 100, 1),
        "estimated_stale_total": round(total * stale_count / max(len(rows), 1)),
        "layer_stats": [dict(r) for r in layer_stats],
    }


def main():
    parser = argparse.ArgumentParser(description="ScriptureEngine Pipeline Scheduler")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--force", action="store_true", help="Run all steps regardless of schedule")
    parser.add_argument("--step", type=str, help="Run a specific pipeline step by name")
    parser.add_argument("--revalidate-stale", action="store_true", help="Find and flag stale connections")
    args = parser.parse_args()

    if args.status:
        status = get_status()
        print(f"\n{'Step':<35} {'Interval':>10} {'Last Run':<22} {'Days Ago':>10} {'Due':>6} {'Tier':<12}")
        print("-" * 95)
        for s in status:
            last = s["last_run"][:16] if s["last_run"] else "-"
            days = str(s["days_since_last_run"]) if s["days_since_last_run"] is not None else "-"
            due = "✅" if s["due"] else " "
            print(f"{s['name']:<35} {str(s['interval_days'])+'d':>10} {last:<22} {days:>10} {due:>6} {s['tier']:<12}")
        print()
        return

    if args.revalidate_stale:
        logger.info("Revalidating stale connections...")
        result = revalidate_stale()
        logger.info("Sampled %d connections, %d stale (%.1f%%). Estimated %d total stale.",
                     result["sampled"], result["stale_in_sample"],
                     result["stale_pct"], result["estimated_stale_total"])
        for ls in result["layer_stats"]:
            if ls["stale"] > 0:
                logger.info("  %s: %d/%d stale", ls["layer"], ls["stale"], ls["cnt"])
        return

    # Load schedule
    schedule = load_schedule()
    pipeline = schedule.get("pipeline", [])

    if not pipeline:
        logger.warning("No pipeline steps defined in schedule.yaml")
        return

    # Filter to runnable steps
    if args.step:
        steps = [s for s in pipeline if s["name"] == args.step]
        if not steps:
            logger.error("Step '%s' not found in schedule.yaml", args.step)
            sys.exit(1)
    else:
        steps = [s for s in pipeline if is_step_due(s, load_state(), force=args.force)]
        if not steps:
            logger.info("No steps due. Use --force to run all.")
            return

    logger.info("Pipeline starting: %d steps to run", len(steps))

    # Execute steps in order (respecting schedule.yaml order)
    results = []
    for step in steps:
        success = run_step(step, force=args.force)
        results.append(success)

    # Update last-run timestamps
    update_last_run(steps, results)

    # Summary
    succeeded = sum(1 for r in results if r)
    failed = sum(1 for r in results if not r)
    logger.info("Pipeline complete: %d succeeded, %d failed", succeeded, failed)


if __name__ == "__main__":
    main()
