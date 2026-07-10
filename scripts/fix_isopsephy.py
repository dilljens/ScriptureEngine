#!/usr/bin/env python3
"""Fix 4: Generate Greek isopsephy connections — same pattern as Hebrew gematria."""
import sys, os, time
from collections import defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

def _batch_insert(conn, batch):
    if not batch:
        return
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()

conn = get_db()
conn.execute("PRAGMA journal_mode=DELETE")

# Delete existing Greek connections
conn.execute("DELETE FROM connections WHERE subtype LIKE 'isopsephy%' OR subtype LIKE 'greek_value%'")
conn.commit()

print("Generating Greek isopsephy connections...", flush=True)

# Find rare Greek gematria values (2-15 verses)
rows = conn.execute("""
    SELECT value_standard, verse_id
    FROM gematria_greek
    WHERE value_standard > 0
""").fetchall()

value_groups = defaultdict(set)
for r in rows:
    val = r[0]
    if 1 <= val <= 999:
        value_groups[val].add(r[1])

batch = []
count = 0
processed = 0

for val, verses in value_groups.items():
    size = len(verses)
    if size < 2 or size > 15:
        continue
    
    processed += 1
    verse_list = sorted(verses)
    strength = min(0.8, 0.3 + 0.05 * (15 - size))
    
    for i in range(len(verse_list)):
        for j in range(i + 1, len(verse_list)):
            batch.append((
                verse_list[i], verse_list[j], "numerical",
                "same_gematria_standard", f"isopsephy_{val}",
                strength, 0.6, "algorithm",
                f'{{"value": {val}, "system": "isopsephy", "verse_count": {size}, "nodata": true}}'
            ))
            count += 1
            if len(batch) >= 200:
                _batch_insert(conn, batch)
                batch = []

if batch:
    _batch_insert(conn, batch)

print(f"  Greek isopsephy: {count} connections from {processed} value groups")
print(f"  Done.")
conn.close()
