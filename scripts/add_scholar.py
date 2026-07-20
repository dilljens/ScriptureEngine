#!/usr/bin/env python3
"""
Add or update a scholar in the credibility database.

Usage:
  python3 scripts/add_scholar.py '{"name": "Hugh Nibley", "weight": 0.8, "credentials": "Professor, BYU", "peer_reviewed": true}'
  python3 scripts/add_scholar.py --list
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


def main():
    if "--list" in sys.argv:
        from lib.api.truth_scholars import list_scholars
        scholars = list_scholars()
        print(f"{'Name':30s} {'Weight':8s} {'Peer Rev':10s} {'Controversy':12s}")
        print("-" * 70)
        for s in scholars:
            print(f"{s['name']:30s} {s['weight']:<8.2f} {str(s['peer_reviewed']):10s} {s['controversy_level']:12s}")
        return
    
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/add_scholar.py '<json>'")
        print("       python3 scripts/add_scholar.py --list")
        sys.exit(1)
    
    data = json.loads(sys.argv[1])
    
    from lib.api.truth_scholars import add_scholar
    result = add_scholar(
        name=data["name"],
        credentials=data.get("credentials", ""),
        peer_reviewed=data.get("peer_reviewed", False),
        field=data.get("field", ""),
        controversy_level=data.get("controversy_level", "medium"),
        weight=data.get("weight", 0.5),
        notes=data.get("notes", ""),
    )
    
    print(f"Added/updated scholar: {data['name']} (weight: {result['weight']})")


if __name__ == "__main__":
    main()
