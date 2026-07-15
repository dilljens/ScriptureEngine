#!/usr/bin/env python3
"""Save session context to SESSION.md for recovery across context loss.

Captures current git state, active plan, and todo items.
Run before any significant action or when /clear might be imminent.

Usage:
    python3 scripts/save_session.py                    # Save to SESSION.md
    python3 scripts/save_session.py --file path.md     # Custom path
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parent.parent


def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, cwd=BASE).strip()
    except Exception:
        return None


def read_todos():
    """Read active todo items from progress.md and task_plan.md."""
    todos = []

    # From progress.md — look for [ ] items
    progress_path = BASE / ".opencode" / "plans" / "progress.md"
    if progress_path.exists():
        with open(progress_path) as f:
            for line in f:
                m = re.search(r'-\s*\[\s*\]\s*(.+)', line)
                if m:
                    todos.append(m.group(1).strip())

    # From task_plan.md — look for [ ] items
    plan_path = BASE / ".opencode" / "plans" / "task_plan.md"
    if plan_path.exists():
        with open(plan_path) as f:
            in_track = False
            for line in f:
                m = re.search(r'-\s*\[\s*\]\s*(.+)', line)
                if m:
                    text = m.group(1).strip()
                    if len(text) > 10:  # Skip short markers
                        todos.append(text)

    return todos if todos else ["(none captured)"]


def save_session(output_path):
    """Write session context markdown file."""
    branch = sh("git rev-parse --abbrev-ref HEAD") or "(unknown)"
    last_commit = sh("git log --oneline -1") or "(unknown)"
    last_commit_full = sh("git log -1 --format=%s") or ""
    status = sh("git status --short") or ""
    modified = [line for line in status.split("\n") if line.strip()] if status else []

    todos = read_todos()

    # Read current plan phase if available
    current_plan = ""
    plan_dir = BASE / ".opencode" / "plans"
    if plan_dir.exists():
        plans = sorted(plan_dir.glob("*.md"))
        if plans:
            current_plan = f"Active plans: " + ", ".join(p.stem for p in plans)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hostname = sh("hostname") or ""

    content = f"""# Session Context

**Last saved:** {now}
**Host:** {hostname}
**Branch:** {branch}
**Last commit:** {last_commit}

## Current plan
{current_plan or "No plans found"}

## Active todos
"""

    for t in todos[:15]:
        content += f"- [ ] {t}\n"

    if modified:
        content += f"\n## Modified files ({len(modified)})\n"
        for m in modified[:20]:
            content += f"- {m}\n"

    content += f"""
## Recovery notes
- Read `SESSION.md` to restore context
- Check `.opencode/plans/` for the current plan
- Run `git status` to see pending changes
- Current work: {last_commit_full[:80] if last_commit_full else "(none)"}
"""

    with open(output_path, "w") as f:
        f.write(content)

    print(f"Session saved to {output_path}")
    print(f"  Branch: {branch}")
    print(f"  Todos: {len(todos)}")
    print(f"  Modified: {len(modified)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save session context")
    parser.add_argument("--file", default=str(BASE / "SESSION.md"), help="Output path")
    args = parser.parse_args()
    save_session(args.file)
