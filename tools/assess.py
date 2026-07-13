#!/usr/bin/env python3
"""
MCP Tool: scripture_assess — Adaptive scripture knowledge assessment.

Usage:
  python3 tools/assess.py '{"action": "start", "target_layer": "pshat"}'
  python3 tools/assess.py '{"action": "answer", "correct": true}'
  python3 tools/assess.py '{"action": "progress"}'
  python3 tools/assess.py '{"action": "diagnostic"}'
  python3 tools/assess.py '{"action": "diagnostic_answer", "correct": true}'
  python3 tools/assess.py '{"action": "diagnostic_report"}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.api.assessment import (
    get_diagnostic_report,
    get_progress,
    start_assessment,
    start_diagnostic,
    submit_answer,
    submit_diagnostic_answer,
)
from lib.db import get_db


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    action = args.get("action", "start")
    conn = get_db()

    if action == "start":
        result = start_assessment(
            conn,
            user_id=args.get("user_id", "default"),
            target_layer=args.get("target_layer"),
            max_items=args.get("max_items", 20),
        )
    elif action == "answer":
        result = submit_answer(
            conn,
            user_id=args.get("user_id", "default"),
            correct=args.get("correct", False),
        )
    elif action == "progress":
        result = get_progress(
            conn,
            user_id=args.get("user_id", "default"),
        )
    elif action == "diagnostic":
        result = start_diagnostic(
            conn,
            user_id=args.get("user_id", "default"),
            max_items=args.get("max_items", 30),
        )
    elif action == "diagnostic_answer":
        result = submit_diagnostic_answer(
            conn,
            user_id=args.get("user_id", "default"),
            correct=args.get("correct", False),
        )
    elif action == "diagnostic_report":
        result = get_diagnostic_report(
            conn,
            user_id=args.get("user_id", "default"),
        )
    else:
        result = {"error": f"Unknown action: {action}"}

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Human-readable summary
    if result.get("ok") and "question" in result:
        q = result["question"]
        mode = result.get("mode", "assessment")
        print(f"\n📝 {mode.upper()} Q{result['item_number']}: {q['question']}", file=sys.stderr)
        if q.get("options"):
            for i, opt in enumerate(q["options"]):
                print(f"   {chr(65+i)}. {opt}", file=sys.stderr)
        if "mastery" in result:
            print(f"\n📊 Mastery: {result['mastery']['overall']:.0%}", file=sys.stderr)
    elif result.get("session_status") == "completed":
        print(f"\n✅ {result.get('mode', 'Assessment').upper()} complete!", file=sys.stderr)
        print(f"   Answered: {result.get('total_answered')} items", file=sys.stderr)
        if "mastery" in result:
            print(f"   Mastery: {result['mastery']['overall']:.0%}", file=sys.stderr)
            if result["mastery"].get("by_layer"):
                for layer, pct in result["mastery"]["by_layer"].items():
                    print(f"   {layer}: {pct:.0%}", file=sys.stderr)
        if result.get("known_count") is not None:
            print(f"   Known: {result['known_count']} items", file=sys.stderr)
            print(f"   Needs review: {result['unknown_count']} items", file=sys.stderr)
    elif result.get("has_diagnostic"):
        print("\n📊 Diagnostic Report:", file=sys.stderr)
        print(f"   Items assessed: {result.get('total_assessed', 0)}", file=sys.stderr)
        print(f"   Overall mastery: {result.get('overall_mastery', 0):.0%}", file=sys.stderr)
        if result.get("mastery_by_layer"):
            for layer, pct in result["mastery_by_layer"].items():
                print(f"   {layer}: {pct:.0%}", file=sys.stderr)


if __name__ == "__main__":
    main()
