#!/usr/bin/env python3
"""Consolidation pipeline CLI — 5-stage periodic maintenance of the graph.

  Stage 1 Inspect     — merge candidates, contradictions, stale connections
  Stage 2 Resolve     — resolve contradictions (explicit beats algorithmic)
  Stage 3 Merge       — coalesce duplicate entity_links rows
  Stage 4 Generalize  — audit frequent (layer, type) rules (report only)
  Stage 5 Forget      — archive stale low-confidence connections

Usage:
  python3 scripts/consolidate.py --dry-run     # report only, no writes (default)
  python3 scripts/consolidate.py --apply       # run and write (idempotent)
  python3 scripts/consolidate.py --apply --json
  python3 scripts/consolidate.py --db /path/to.db
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.controls.consolidation import consolidate
from lib.db import get_db


def _print_human(report):
    s = report["summary"]
    mode = "DRY-RUN (no writes)" if report["dry_run"] else "APPLY"
    print("=" * 60)
    print(f"  Consolidation Report — {mode}")
    print("=" * 60)
    print(f"  Stage 1 Inspect:    {s['merge_candidates']} merge candidates, "
          f"{s['contradictions']} contradictions, {s['stale']} stale")
    print(f"  Stage 2 Resolve:    {s['resolved']} contradictions resolved")
    print(f"  Stage 3 Merge:      {s['merged']} entities merged")
    print(f"  Stage 4 Generalize: {s['generalized_rules']} frequent (layer,type) rules (audit)")
    print(f"  Stage 5 Forget:     {s['archived']} connections archived")
    print(f"  Total actions:      {s['total_actions']}")
    print("=" * 60)

    stage1 = report["stages"]["1_inspect"]
    for c in stage1["merge_candidates"]:
        print(f"  [merge] {c['duplicate']} → {c['canonical']} "
              f"(sim={c['similarity']}, {c['entity_type']})")
    for c in report["stages"]["2_resolve"]["resolved"]:
        print(f"  [resolve] {c['source_verse']}→{c['target_verse']} "
              f"{c['conflict_type']}: loser #{c['loser_id']} ({c['loser_discovered_by']}) "
              f"loses to #{c['winner_id']} ({c['winner_discovered_by']})")
    for m in report["stages"]["3_merge"]["merged"]:
        print(f"  [merged] {m['duplicate']} into {m['canonical']}")
    for a in report["stages"]["5_forget"]["archived"]:
        print(f"  [archived] #{a['id']} {a['source_verse']}→{a['target_verse']} "
              f"({a['layer']}/{a['type']}, conf={a['confidence']})")
    for r in report["stages"]["4_generalize"]["rules"]:
        print(f"  [rule] {r['layer']}/{r['type']} × {r['frequency']}")


def main():
    parser = argparse.ArgumentParser(description="5-stage graph consolidation pipeline")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Report only — no writes (default)")
    group.add_argument("--apply", action="store_true", help="Run the pipeline and write changes")
    parser.add_argument("--json", action="store_true", help="Emit the full report as JSON")
    parser.add_argument("--db", default=None, help="Override database path")
    args = parser.parse_args()

    dry_run = not args.apply
    conn = get_db(args.db)
    try:
        report = consolidate(conn, dry_run=dry_run)
    finally:
        conn.close()

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
