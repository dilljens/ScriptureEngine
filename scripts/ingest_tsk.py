#!/usr/bin/env python3
"""Phase A: Ingest Treasury of Scripture Knowledge (TSK) cross-references.

340K human-curated cross-references from openbible.info.
Uses batch inserts for performance.
"""
import sys, os, csv, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

BOOK_MAP = {
    '1sam':'1sam','2sam':'2sam','1kgs':'1kgs','2kgs':'2kgs',
    '1chr':'1chr','2chr':'2chr','1cor':'1cor','2cor':'2cor',
    '1thes':'1thes','2thes':'2thes','1tim':'1tim','2tim':'2tim',
    '1pet':'1pet','2pet':'2pet','1john':'1john','2john':'2john','3john':'3john',
    'ps':'psa','psa':'psa','psalms':'psa',
}

def norm(v):
    p = v.strip().split('.')
    if len(p) < 3:
        return None
    b = BOOK_MAP.get(p[0].lower(), p[0].lower())
    try:
        return f"{b}.{int(p[1])}.{int(p[2])}"
    except:
        return None

def type_and_conf(votes):
    if votes >= 8:
        return 'direct_quotation', min(0.95, 0.7 + votes / 200)
    elif votes >= 4:
        return 'allusion', min(0.7, 0.5 + votes / 50)
    else:
        return 'echo', min(0.5, 0.35 + votes / 30)

def run():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=DELETE")
    
    tsk_file = '/tmp/cross_references.txt'
    if not os.path.exists(tsk_file):
        print("TSK file not found at /tmp/cross_references.txt")
        return
    
    # Clear existing TSK connections
    conn.execute("DELETE FROM connections WHERE discovered_by='tsk'")
    conn.commit()
    
    # Pre-load valid verse IDs for fast lookup
    valid = set(r[0] for r in conn.execute("SELECT id FROM verses"))
    print(f"  {len(valid):,} valid verses in DB", flush=True)
    
    total = 0
    created = 0
    skipped_verse = 0
    batch = []
    
    with open(tsk_file, encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # skip header
        
        for row in reader:
            if len(row) < 3:
                continue
            from_v = norm(row[0])
            to_v = norm(row[1])
            try:
                votes = int(row[2])
            except:
                votes = 0
            
            if not from_v or not to_v or votes < 2:
                continue
            
            if from_v not in valid or to_v not in valid:
                skipped_verse += 1
                continue
            
            conn_type, confidence = type_and_conf(votes)
            strength = round(confidence * 0.9, 2)
            
            batch.append((
                from_v, to_v, 'intertextual', conn_type, 'tsk',
                strength, round(confidence, 2), 'tsk',
                json.dumps({'source':'tsk','votes':votes})
            ))
            created += 1
            
            if len(batch) >= 200:
                conn.executemany("""
                    INSERT OR IGNORE INTO connections
                        (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                batch = []
            
            total += 1
            if total % 100000 == 0:
                print(f"  {total} processed, {created} created", flush=True)
    
    if batch:
        conn.executemany("""
            INSERT OR IGNORE INTO connections
                (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    
    print(f"\nTSK done: {total} rows, {created} created, {skipped_verse} skipped (verse not in DB)")
    final = conn.execute("SELECT COUNT(*) FROM connections WHERE discovered_by='tsk'").fetchone()[0]
    print(f"Final TSK count: {final}")
    for r in conn.execute("SELECT type, COUNT(*) FROM connections WHERE discovered_by='tsk' GROUP BY type ORDER BY COUNT(*) DESC").fetchall():
        print(f"  {r[0]}: {r[1]:,}")
    conn.close()

if __name__ == "__main__":
    run()
