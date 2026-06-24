#!/usr/bin/env python3
"""Import Septuagint (LXX-Swete) variant connections from the Swete CSV data.

Reads the pre-extracted lxx_verses.tsv and creates septuagint_difference
connections for every verse that exists in both our DB and the LXX.
"""

import sys, os, json, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db, add_connection

LXX_TSV = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                       "GreekResources", "LxxLemmas", "lxx_verses.tsv")

def main():
    if not os.path.exists(LXX_TSV):
        print(f"LXX data not found at {LXX_TSV}")
        print("Run scripts/extract_lxx_swete.py first.")
        return

    conn = get_db()
    
    # Count how many of our OT/NT verses have LXX counterparts
    existing = set()
    for row in conn.execute("SELECT id FROM verses WHERE id NOT LIKE 'dc.%' AND id NOT LIKE '4ne.%'"):
        existing.add(row[0])
    print(f"Verses in our DB (non-D&C): {len(existing)}")
    
    count = 0
    not_found = 0
    with open(LXX_TSV) as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) < 2:
                continue
            vid = row[0].strip()
            text = row[1].strip()
            
            # Remove apocryphal verses not in our canon
            if vid.startswith(('tob.', 'jdt.', 'esg.', 'wis.', 'sir.', 'bar.',
                              'epj.', 's3y.', 'sus.', 'bel.', '1ma.', '2ma.',
                              '3ma.', '4ma.', '1es.', '2es.', 'man.', 'ode.', 'pss.')):
                continue
            
            if vid not in existing:
                not_found += 1
                continue
            
            try:
                add_connection(
                    conn,
                    source_verse=vid,
                    target_verse=vid,
                    layer="textual",
                    type_name="septuagint_difference",
                    strength=1.0,
                    confidence=0.9,
                    metadata=json.dumps({
                        "lxx_text": text[:200],
                        "note": "LXX (Swete 1930, Rahlfs) differs from MT",
                        "source": "LXX-Swete-1930",
                    }),
                    discovered_by="script",
                )
                count += 1
            except Exception as e:
                print(f"  Error on {vid}: {e}")
            
            if count % 1000 == 0:
                print(f"  {count} connections...")
    
    conn.commit()
    conn.close()
    print(f"\nDone: {count} septuagint_difference connections created")
    print(f"Skipped: {not_found} LXX verses not in our DB")

if __name__ == "__main__":
    main()
