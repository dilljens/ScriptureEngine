#!/usr/bin/env python3
"""Fix lexicon search: add hebrew_plain for niqqud-stripped search,
and populate word_english via frequency analysis from verse text.

Two fixes:
  1. Hebrew niqqud: strip combining marks, store in hebrew_plain column
  2. English search: for each lemma, find most correlated English word
     from verses where it appears (TF-IDF style frequency analysis)
"""

import sys, os, re, json, unicodedata
from collections import Counter, defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db


def strip_hebrew_marks(text):
    """Remove niqqud and cantillation marks from Hebrew text."""
    if not text:
        return ""
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith("M") or cat == "Cf":
            continue
        if "\u05d0" <= ch <= "\u05ea" or ch.isalpha() or ch.isspace():
            result.append(ch)
    return "".join(result)


def run():
    conn = get_db()
    
    # ── Fix 1: Add hebrew_plain column and populate ──
    print("Fix 1: Adding hebrew_plain column...", flush=True)
    
    # Check if column exists
    cols = [r[1] for r in conn.execute("PRAGMA table_info(lexicon)").fetchall()]
    if 'hebrew_plain' not in cols:
        conn.execute("ALTER TABLE lexicon ADD COLUMN hebrew_plain TEXT DEFAULT ''")
        print("  Created hebrew_plain column")
    
    # Populate hebrew_plain for all entries
    rows = conn.execute("SELECT lemma, hebrew FROM lexicon WHERE hebrew != ''").fetchall()
    updated = 0
    for r in rows:
        plain = strip_hebrew_marks(r[1])
        if plain:
            conn.execute("UPDATE lexicon SET hebrew_plain = ? WHERE lemma = ?", (plain, r[0]))
            updated += 1
    conn.commit()
    print(f"  Populated hebrew_plain for {updated} entries")
    
    # ── Fix 2: Populate word_english via frequency analysis ──
    print("\nFix 2: Building English glosses from verse text...", flush=True)
    
    # Step 1: For each lemma, get all English words from verses where it appears
    # Use the lemma→verse mapping
    lemma_verse_words = defaultdict(Counter)
    total_lemma_verse_pairs = 0
    
    rows = conn.execute("""
        SELECT g.lemma, g.verse_id
        FROM gematria g
        WHERE g.lemma IS NOT NULL AND g.lemma != ''
          AND g.lemma NOT LIKE '%/%'  -- Skip prefixed lemmas
    """).fetchall()
    
    print(f"  Processing {len(rows)} lemma-verse pairs...", flush=True)
    
    # Group by lemma, collect verse IDs
    lemma_verses = defaultdict(set)
    for r in rows:
        lemma_verses[r[0]].add(r[1])
    
    # Compute background word frequencies across ALL English verses
    print("  Computing background word frequencies...", flush=True)
    background = Counter()
    all_verses = conn.execute("SELECT text_english FROM verses WHERE text_english != ''").fetchall()
    for v in all_verses:
        words = re.findall(r"[a-zA-Z']+", (v[0] or '').lower())
        background.update(w for w in words if len(w) > 2)
    
    total_background = sum(background.values())
    
    # Process each lemma — find most distinctive English word using TF-IDF
    stop_words = {'the', 'and', 'of', 'to', 'in', 'that', 'he', 'shall',
                  'unto', 'for', 'his', 'is', 'it', 'with', 'my', 'not',
                  'be', 'him', 'from', 'they', 'all', 'are', 'as', 'you',
                  'were', 'them', 'been', 'their', 'will', 'when', 'who',
                  'than', 'upon', 'into', 'thy', 'thou', 'hath', 'thee',
                  'there', 'have', 'your', 'which', 'this', 'were',
                  'her', 'she', 'its', 'then', 'out', 'was', 'said', 'had',
                  'an', 'no', 'we', 'but', 'every', 'may', 'so', 'can',
                  'now', 'went', 'after', 'come', 'did', 'also', 'let',
                  'yet', 'even', 'any', 'nor', 'any'}
    
    lemma_gloss = {}
    processed = 0
    stop_word_set = set(stop_words)
    
    for lemma, verses in lemma_verses.items():
        if len(verses) < 3:
            continue  # Skip very rare lemmas
        
        verse_ids = list(verses)
        placeholders = ",".join("?" for _ in verse_ids)
        
        eng_rows = conn.execute(f"""
            SELECT text_english FROM verses
            WHERE id IN ({placeholders})
        """, verse_ids).fetchall()
        
        # Count words in lemma's verses
        lemma_word_count = Counter()
        for er in eng_rows:
            text = er[0] or ''
            words = re.findall(r"[a-zA-Z']+", text.lower())
            lemma_word_count.update(w for w in words if len(w) > 2 and w not in stop_word_set)
        
        if not lemma_word_count:
            continue
        
        # Use PMI (Pointwise Mutual Information) weighted by frequency:
        # score = log(observed / expected) * observed 
        # This rewards words that are both frequent AND distinctive,
        # without the rare-word bias of pure TF-IDF.
        lemma_total = sum(lemma_word_count.values())
        if lemma_total == 0:
            continue
        
        scored = []
        for word, count in lemma_word_count.items():
            expected = (background.get(word, 1) / total_background) * lemma_total
            if expected <= 0:
                continue
            # Observed / expected ratio (how over-represented is this word?)
            ratio = count / expected
            # Score = ratio * count (balance distinctiveness with frequency)
            score = ratio * count
            scored.append((score, count, word))
        
        if not scored:
            continue
        
        scored.sort(reverse=True)
        best = scored[0]
        
        gloss = best[2]  # Lowercase word
        
        # Capitalize proper nouns
        proper_nouns = {'lord', 'god', 'king', 'moses', 'david', 'solomon',
                       'jesus', 'christ', 'israel', 'egypt', 'jerusalem',
                       'zion', 'babylon', 'sinai', 'zion', 'sabbath',
                       'passover', 'tabernacle', 'temple', 'altar',
                       'covenant', 'ark', 'mercy', 'cherub', 'prophet',
                       'priest', 'levite', 'pharaoh', 'hebrew'}
        if gloss in proper_nouns:
            gloss = gloss.upper() if gloss in ('lord', 'god') else gloss.capitalize()
        elif len(gloss) > 2:
            gloss = gloss.capitalize()
        
        lemma_gloss[lemma] = (gloss, best[1], len(verses))
        processed += 1
        
        if processed % 500 == 0:
            print(f"    {processed} lemmas processed...", flush=True)
        processed += 1
        
        if processed % 500 == 0:
            print(f"    {processed} lemmas processed...", flush=True)
    
    # Step 2: Write glosses to gematria.word_english
    # We'll store the primary gloss in a new table rather than 
    # updating 305K rows. Create a lemma_to_english table.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lemma_gloss (
            lemma TEXT PRIMARY KEY,
            english_gloss TEXT DEFAULT '',
            frequency INTEGER DEFAULT 0,
            verse_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("DELETE FROM lemma_gloss")
    
    glosses = [(l, g, f, vc) for l, (g, f, vc) in lemma_gloss.items()]
    
    batch = []
    for lemma, gloss, freq, vc in glosses:
        if gloss:
            batch.append((lemma, gloss, freq, vc))
            if len(batch) >= 200:
                conn.executemany("""
                    INSERT OR IGNORE INTO lemma_gloss (lemma, english_gloss, frequency, verse_count)
                    VALUES (?, ?, ?, ?)
                """, batch)
                batch = []
    if batch:
        conn.executemany("""
            INSERT OR IGNORE INTO lemma_gloss (lemma, english_gloss, frequency, verse_count)
            VALUES (?, ?, ?, ?)
        """, batch)
    
    conn.commit()
    
    # Show some results
    print(f"\n  Created lemma_gloss table with {len(glosses)} entries")
    
    # Sample a few
    print("\n  Sample glosses:")
    for lemma in ['3068', '430', '1697', '7225', '1289']:
        row = conn.execute("SELECT english_gloss, frequency FROM lemma_gloss WHERE lemma=?", (lemma,)).fetchone()
        if row:
            print(f"    {lemma}: {row[0]} (freq={row[1]})")
    
    # ── Fix 2b: Modify search_lexicon to use lemma_gloss ──
    # Already done in lib/lexicon/__init__.py
    
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    run()
