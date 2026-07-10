#!/usr/bin/env python3
"""Build the lexicon table from gematria data — purely algorithmic."""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from collections import defaultdict
from lib.db import get_db
from lib.lexicon import init_lexicon_tables, _insert_lexicon_batch, normalize_lemma, extract_root

conn = get_db()
init_lexicon_tables(conn)

# Clear
conn.execute("DELETE FROM lexicon")
conn.execute("DELETE FROM word_collocations")
conn.commit()

t_start = time.time()

# Step 1: Extract all lemmas
t0 = time.time()
rows = conn.execute("""
    SELECT lemma, word_hebrew, word_english, morph, 
           COUNT(DISTINCT verse_id) as freq
    FROM gematria 
    WHERE lemma IS NOT NULL AND lemma != ''
    GROUP BY lemma 
    ORDER BY freq DESC
""").fetchall()
print(f"Queried {len(rows)} raw lemma-rows in {(time.time()-t0)*1000:.0f}ms")

# Step 2: Insert deduplicated by normalized lemma
t1 = time.time()
batch = []
total = 0
seen = set()
for r in rows:
    base = normalize_lemma(r["lemma"])
    if not base or base in seen:
        continue
    seen.add(base)
    hebrew = (r["word_hebrew"] or "").strip()
    root = extract_root(hebrew)
    morph = (r["morph"] or "").strip()
    freq = r["freq"]

    batch.append((
        base, hebrew, "", "", root, "", "",
        "algorithm", freq, "{}", "", morph,
        0, 0, "{}"
    ))
    total += 1
    if len(batch) >= 2000:
        _insert_lexicon_batch(conn, batch)
        batch = []
        print(f"  Inserted {total}...", flush=True)

if batch:
    _insert_lexicon_batch(conn, batch)

actual = conn.execute("SELECT COUNT(*) as c FROM lexicon").fetchone()["c"]
print(f"Inserted {actual} unique lemmas in {(time.time()-t1)*1000:.0f}ms")

# Step 3: Per-book frequency (simpler query without JOIN to lexicon)
t2 = time.time()
print("Computing per-book frequencies...", flush=True)
book_rows = conn.execute("""
    SELECT g.lemma, v.book_id, COUNT(*) as c
    FROM gematria g
    JOIN verses v ON v.id = g.verse_id
    WHERE g.lemma IS NOT NULL AND g.lemma != ''
    GROUP BY g.lemma, v.book_id
""").fetchall()

by_lemma = defaultdict(dict)
books_by = defaultdict(set)
for r in book_rows:
    base = normalize_lemma(r["lemma"])
    by_lemma[base][r["book_id"]] = r["c"]
    books_by[base].add(r["book_id"])

batch = []
for lemma, book_counts in by_lemma.items():
    freq_json = json.dumps(book_counts)
    books_str = ",".join(sorted(books_by[lemma]))
    batch.append((freq_json, books_str, lemma))
    if len(batch) >= 2000:
        conn.executemany(
            "UPDATE lexicon SET frequency_per_book = ?, books_list = ? WHERE lemma = ?",
            batch
        )
        batch = []

if batch:
    conn.executemany(
        "UPDATE lexicon SET frequency_per_book = ?, books_list = ? WHERE lemma = ?",
        batch
    )

print(f"Book frequencies done in {(time.time()-t2)*1000:.0f}ms")

# Step 4: Collocations (simplified — within-books only, min 5 co-occurrences)
t3 = time.time()
print("Building collocations...", flush=True)
colloc_rows = conn.execute("""
    SELECT g1.lemma as a, g2.lemma as b, v.book_id, COUNT(*) as c
    FROM gematria g1
    JOIN gematria g2 ON g2.verse_id = g1.verse_id AND g2.lemma < g1.lemma
    JOIN verses v ON v.id = g1.verse_id
    WHERE g1.lemma IS NOT NULL AND g1.lemma != ''
      AND g2.lemma IS NOT NULL AND g2.lemma != ''
    GROUP BY g1.lemma, g2.lemma, v.book_id
    HAVING c >= 5
    ORDER BY c DESC
""").fetchall()

cbatch = []
ccount = 0
for r in colloc_rows:
    wa = normalize_lemma(r["a"])
    wb = normalize_lemma(r["b"])
    if wa and wb and wa != wb:
        cbatch.append((wa, wb, r["book_id"], r["c"], 1.0))
        ccount += 1
        if len(cbatch) >= 2000:
            conn.executemany(
                "INSERT OR IGNORE INTO word_collocations (word_a, word_b, book_id, frequency, strength) VALUES (?, ?, ?, ?, ?)",
                cbatch
            )
            cbatch = []

if cbatch:
    conn.executemany(
        "INSERT OR IGNORE INTO word_collocations (word_a, word_b, book_id, frequency, strength) VALUES (?, ?, ?, ?, ?)",
        cbatch
    )

print(f"Collocations: {ccount} pairs in {(time.time()-t3)*1000:.0f}ms")

conn.commit()
elapsed = time.time() - t_start
print(f"\n=== Lexicon built in {elapsed:.1f}s ===")
print(f"  Lemmas: {actual}")
print(f"  Collocations: {ccount}")
