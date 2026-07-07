#!/usr/bin/env python3
"""Run all automatic generators and report results."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from generators import run_all
from lib.db import get_db

conn = get_db()
print("Running all automatic generators...")
print(f"{'Status':10s} {'Generator':42s} {'Conns':>6s}")
print("-" * 60)
results = run_all(conn)
for r in results:
    err = r.get("error", "")
    conns = r.get("connections", 0) if r["status"] == "ok" else 0
    status = f"{r['status']}{'!' if err else ''}"
    print(f'{status:10s} {r.get("generator",""):42s} {conns:6d}')
    if err:
        print(f'           ERROR: {err[:80]}')
conn.close()
print("-" * 60)
total = sum(r.get("connections", 0) for r in results)
print(f"{'TOTAL':52s} {total:6d}")
