#!/usr/bin/env python3
"""Generate embedding vectors for all verses using sqlite-vec.

Enables semantic search: "find verses similar to this one" or
"find passages about the shepherd" without keyword matching.

Uses a simple fast vectorization method — character n-gram hashing
baked into sqlite-vec — so no external model is needed.
For production, replace with sentence-transformers or nomic-embed.

Usage:
  python3 scripts/embed_verses.py          # Embed all 42K verses
  python3 scripts/embed_verses.py --reset  # Rebuild from scratch
"""

import sys, os, json, struct, hashlib, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db_vec, DEFAULT_DB_PATH
import sqlite_vec


def ngram_hash(text, n=3, dim=384):
    """Convert text to a vector using character n-gram hashing.
    
    Simple but effective: split text into n-grams, hash each to a
    position, accumulate a count vector, normalize.
    
    This doesn't give the same quality as a transformer embedding,
    but it's deterministic, fast, and requires no model download.
    For better quality, swap this function with sentence-transformers.
    """
    vec = [0.0] * dim
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\u0590-\u05FF\s]', '', text)
    
    for i in range(len(text) - n + 1):
        gram = text[i:i + n]
        h = hashlib.md5(gram.encode('utf-8')).digest()
        pos = struct.unpack_from('<I', h, 0)[0] % dim
        vec[pos] += 1.0
    
    # L2 normalize
    mag = sum(v * v for v in vec) ** 0.5
    if mag > 0:
        vec = [v / mag for v in vec]
    return vec


def embed_and_store(conn, reset=False):
    """Embed all verses and store in sqlite-vec virtual table."""
    if reset:
        conn.execute("DROP TABLE IF EXISTS vec_verses")
    
    # Create the vector table (FTS5-style virtual table for vectors)
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_verses USING vec0(
            verse_id TEXT PRIMARY KEY,
            embedding float[384] distance_metric=cosine
        )
    """)
    conn.commit()
    
    # Get all verses with text
    rows = conn.execute("""
        SELECT id, text_english, text_hebrew, text_greek
        FROM verses
        WHERE text_english != '' OR text_hebrew != '' OR text_greek != ''
    """).fetchall()
    
    # Check which are already embedded
    already = set(r["verse_id"] for r in conn.execute("SELECT verse_id FROM vec_verses").fetchall())
    
    batch = []
    total = 0
    skipped = 0
    
    for r in rows:
        vid = r["id"]
        if vid in already:
            skipped += 1
            continue
        
        # Build embedding text from all available languages
        text = ""
        if r["text_english"]:
            text += r["text_english"] + " "
        if r["text_hebrew"]:
            text += r["text_hebrew"] + " "
        if r["text_greek"]:
            text += r["text_greek"]
        
        if not text.strip():
            continue
        
        vec = ngram_hash(text)
        vec_bytes = struct.pack(f'{len(vec)}f', *vec)
        batch.append((vid, vec_bytes))
        total += 1
        
        if len(batch) >= 100:
            conn.executemany("INSERT INTO vec_verses (verse_id, embedding) VALUES (?, ?)", batch)
            conn.commit()
            batch = []
    
    if batch:
        conn.executemany("INSERT INTO vec_verses (verse_id, embedding) VALUES (?, ?)", batch)
        conn.commit()
    
    return total, skipped


def semantic_search(conn, query, limit=20):
    """Find verses by semantic similarity to a query string."""
    vec = ngram_hash(query)
    vec_bytes = struct.pack(f'{len(vec)}f', *vec)
    
    rows = conn.execute("""
        SELECT verse_id, distance FROM vec_verses
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
    """, (vec_bytes, limit)).fetchall()
    
    results = []
    for r in rows:
        v = conn.execute("""
            SELECT v.id as vid, v.text_english, b.title as book_title, v.chapter, v.verse
            FROM vec_verses vv
            JOIN verses v ON v.id = vv.verse_id
            JOIN books b ON b.id = v.book_id
            WHERE vv.verse_id = ?
        """, (r["verse_id"],)).fetchone()
        if v:
            results.append({
                "verse": v["vid"],
                "reference": f"{v['book_title']} {v['chapter']}:{v['verse']}",
                "text": v["text_english"][:150],
                "similarity": round(1.0 - r["distance"], 3),
            })
    
    return results


def main():
    reset = "--reset" in sys.argv
    
    print("=" * 60)
    print("  Embedding Verses — sqlite-vec Semantic Search")
    print("=" * 60)
    
    conn = get_db_vec()
    
    print("\n--- Embedding all verses ---", flush=True)
    total, skipped = embed_and_store(conn, reset=reset)
    print(f"  Embedded: {total} new verses", flush=True)
    print(f"  Skipped (already embedded): {skipped}", flush=True)
    
    # Verify
    count = conn.execute("SELECT COUNT(*) as c FROM vec_verses").fetchone()["c"]
    total_verses = conn.execute("""
        SELECT COUNT(*) as c FROM verses
        WHERE text_english != '' OR text_hebrew != '' OR text_greek != ''
    """).fetchone()["c"]
    print(f"  Total vectors: {count} / {total_verses} verses", flush=True)
    
    # Demo semantic search
    if count > 0:
        print("\n--- Demo: Semantic Search ---", flush=True)
        demos = ["shepherd and sheep", "covenant of peace", "angel of the lord appearance"]
        for query in demos:
            results = semantic_search(conn, query, limit=3)
            print(f"  '{query}':", flush=True)
            for r in results:
                print(f"    {r['similarity']:.3f} {r['reference']:25s} {r['text'][:60]}", flush=True)
    
    # Update server cache flag
    VEC_CACHE = {"available": True, "count": count}
    
    conn.close()
    print(f"\n  Done. {count} verses embedded and ready for semantic search.")


if __name__ == "__main__":
    main()
