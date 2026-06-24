"""Hapax/dislegomenon generator — rare word connections.

Connects verses that share a word appearing only 1x (hapax) or 2x (dislegomenon)
across the canon. Two verses sharing a hapax legomenon is a strong linguistic signal
— it often indicates direct literary dependence or a shared source.

Also connects verses sharing the same lemma that appears in very few verses
(2-5 range) — these are "rare lemma" connections distinct from the existing
same_lemma generator which uses a higher threshold.
"""

from collections import defaultdict
from lib.db import add_connection


def run(conn, book_ids=None):
    """Connect verses sharing hapax legomena, dislegomena, and rare lemmas.
    
    1. Hapax: lemma appears in exactly 1 verse → connect those verses (actually
       can't connect 1-verse lemmas since there's only one verse).
    2. Dislegomenon: lemma appears in exactly 2 verses → connect those 2 verses.
    3. Rare (2-5 verses): connect verses sharing very rare lemmas.
    
    Returns count of connections created.
    """
    count = 0
    batch = []
    
    # Find lemmas grouped by their occurrence count
    # Using per-canon (not per-book) frequency
    lemma_freq = conn.execute("""
        SELECT lemma, COUNT(DISTINCT verse_id) as freq
        FROM gematria
        WHERE lemma IS NOT NULL AND lemma != ''
        GROUP BY lemma
        HAVING freq BETWEEN 2 AND 5
        ORDER BY freq
    """).fetchall()
    
    processed = 0
    
    for r in lemma_freq:
        lemma = r["lemma"]
        freq = r["freq"]
        
        # Get the actual verses
        verses = conn.execute("""
            SELECT DISTINCT verse_id FROM gematria
            WHERE lemma = ?
            ORDER BY verse_id
        """, (lemma,)).fetchall()
        
        verse_ids = [v["verse_id"] for v in verses]
        
        if len(verse_ids) < 2:
            continue
        
        # Map frequency to connection type
        if freq == 2:
            conn_type = "dislegomenon"
            strength = 0.7
        elif freq <= 5:
            conn_type = "repetition_pattern"
            strength = 0.5
        else:
            continue
        
        # Connect all pairs of verses sharing this rare lemma
        for i in range(len(verse_ids)):
            for j in range(i + 1, len(verse_ids)):
                batch.append((
                    verse_ids[i], verse_ids[j], "frequency",
                    conn_type, lemma, strength, 0.6, "algorithm",
                    f'{{"lemma": "{lemma}", "verse_count": {freq}}}'
                ))
                count += 1
                
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
        
        processed += 1
        if processed % 500 == 0:
            print(f"    {processed} rare lemmas processed...", flush=True)
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Hapax/dislegomenon: {count} connections from {processed} rare lemmas")
    return count


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
