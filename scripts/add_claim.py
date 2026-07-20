#!/usr/bin/env python3
"""
Add a new scholarly claim to the truth evaluation database.

Usage:
  python3 scripts/add_claim.py '{
    "scholar": "Hugh Nibley",
    "claim": "The temple is the axis mundi — the center of the world",
    "verses": ["ezek.38.12", "gen.2.8"],
    "topic": "temple_microcosm",
    "level": "L2_CONTEXTUAL"
  }'
  python3 scripts/add_claim.py --list-topics
"""

import json
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


def main():
    if "--list-topics" in sys.argv:
        from lib.api.truth_data import SCHOLARLY_CLAIMS
        print("Existing topics:")
        for topic, claims in SCHOLARLY_CLAIMS.items():
            scholars = set(c["scholar"] for c in claims)
            print(f"  {topic}: {len(claims)} claims from {', '.join(scholars)}")
        return
    
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/add_claim.py '<json>'")
        print("       python3 scripts/add_claim.py --list-topics")
        sys.exit(1)
    
    data = json.loads(sys.argv[1])
    
    # Auto-classify level if not provided
    if "level" not in data:
        from scripts.truth_tag_claims import classify_claim_level
        data["level"] = classify_claim_level(
            data.get("claim", ""), data.get("verses", []), data.get("scholar", "")
        )
        print(f"Auto-classified level: {data['level']}")
    
    # Show what would be added
    topic = data.get("topic", "uncategorized")
    print(f"Would add to topic '{topic}':")
    print(f"  Scholar: {data.get('scholar', '?')}")
    print(f"  Level:   {data.get('level', '?')}")
    print(f"  Claim:   {data.get('claim', '?')[:80]}...")
    print(f"  Verses:  {data.get('verses', [])}")
    
    print()
    print("To actually add, edit lib/api/truth_data.py manually or")
    print("use the --update flag once implemented.")


if __name__ == "__main__":
    main()
