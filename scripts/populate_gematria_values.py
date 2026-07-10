#!/usr/bin/env python3
"""Populate new kabbalistic gematria value columns in the gematria table."""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db
from lib.gematria import compute_milui, compute_kellali, compute_kidmi, compute_boneh, extract_consonants

conn = get_db()

# Ensure columns exist
for col in ['value_milui', 'value_kellali', 'value_kidmi', 'value_boneh']:
    try:
        conn.execute(f'ALTER TABLE gematria ADD COLUMN {col} INTEGER DEFAULT 0')
    except Exception:
        pass

rows = conn.execute("SELECT id, word_hebrew FROM gematria WHERE word_hebrew IS NOT NULL AND word_hebrew != ''").fetchall()
t0 = time.time()
batch = []
total = 0

for r in rows:
    try:
        cons = extract_consonants(r["word_hebrew"])
        if not cons:
            continue
        milui = compute_milui(cons)
        kellali = compute_kellali(cons)
        kidmi = compute_kidmi(cons)
        boneh = compute_boneh(cons)
        batch.append((milui, kellali, kidmi, boneh, r["id"]))
        total += 1
        if len(batch) >= 2000:
            conn.executemany(
                "UPDATE gematria SET value_milui=?, value_kellali=?, value_kidmi=?, value_boneh=? WHERE id=?",
                batch
            )
            conn.commit()
            batch = []
        if total % 20000 == 0:
            print(f"  {total} rows processed ({time.time()-t0:.0f}s)", flush=True)
    except Exception:
        pass

if batch:
    conn.executemany(
        "UPDATE gematria SET value_milui=?, value_kellali=?, value_kidmi=?, value_boneh=? WHERE id=?",
        batch
    )
    conn.commit()

conn.close()
print(f"Done: {total} rows, {time.time()-t0:.0f}s")
