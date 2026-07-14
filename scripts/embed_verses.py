#!/usr/bin/env python3
"""Generate transformer-based embedding vectors for all verses using fastembed.

Enables cross-lingual semantic search: "find verses about covenant" will
return verses containing ברית, διαθήκη, and "covenant" correctly ranked
because the multilingual model understands them as the same concept.

Uses paraphrase-multilingual-MiniLM-L12-v2 (384-dim, 50+ languages including
Hebrew, Greek, English, Arabic) via fastembed/ONNX — no GPU needed.

Usage:
  .venv/bin/python3 scripts/embed_verses.py               # Embed all 70K verses
  .venv/bin/python3 scripts/embed_verses.py --reset       # Rebuild from scratch
  .venv/bin/python3 scripts/embed_verses.py --book gen    # Just Genesis
"""

import argparse
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db_vec

# Embedding model config
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_DIM = 384
BATCH_SIZE = 32


def build_verse_text(row):
    """Build a searchable text representation from all available languages."""
    parts = []
    if row["text_hebrew"]:
        parts.append(f"hebrew: {row['text_hebrew']}")
    if row["text_greek"]:
        parts.append(f"greek: {row['text_greek']}")
    if row["text_english"]:
        parts.append(f"english: {row['text_english']}")
    return "\n".join(parts)


def embed_and_store(conn, model, reset=False, book_filter=None):
    """Embed all verses and store in sqlite-vec virtual table."""
    if reset:
        conn.execute("DROP TABLE IF EXISTS vec_verses")

    # Create vector table with proper dimension
    conn.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_verses USING vec0(
            verse_id TEXT PRIMARY KEY,
            embedding float[{MODEL_DIM}] distance_metric=cosine
        )
    """)
    conn.commit()

    # Get all verses
    query = """
        SELECT id, book_id, chapter, verse, text_english, text_hebrew, text_greek
        FROM verses
        WHERE text_english != '' OR text_hebrew != '' OR text_greek != ''
    """
    params = []
    if book_filter:
        query += " AND book_id = ?"
        params.append(book_filter)
    query += " ORDER BY id"

    rows = conn.execute(query, params).fetchall()
    total_verses = len(rows)
    print(f"  Verses to embed: {total_verses}")

    # Already embedded check
    try:
        already = set(r["verse_id"] for r in conn.execute("SELECT verse_id FROM vec_verses").fetchall())
    except Exception:
        already = set()
    print(f"  Already embedded: {len(already)}")

    to_embed = [r for r in rows if r["id"] not in already]
    if not to_embed:
        print("  All verses already embedded.")
        return 0, len(already)

    print(f"  New to embed: {len(to_embed)}")

    # Generate embeddings in batches
    embedded = 0
    for i in range(0, len(to_embed), BATCH_SIZE):
        batch = to_embed[i:i + BATCH_SIZE]
        texts = [build_verse_text(r) for r in batch]

        # Generate embeddings via fastembed
        embeddings = list(model.embed(texts))

        # Insert into sqlite-vec
        insert_batch = []
        for (r, emb) in zip(batch, embeddings):
            vec_bytes = struct.pack(f'{len(emb)}f', *emb)
            insert_batch.append((r["id"], vec_bytes))

        conn.executemany(
            "INSERT INTO vec_verses (verse_id, embedding) VALUES (?, ?)",
            insert_batch
        )
        conn.commit()
        embedded += len(batch)

        if (i // BATCH_SIZE) % 10 == 0:
            print(f"  Progress: {embedded}/{len(to_embed)}", flush=True)

    return embedded, len(already)


def semantic_search(conn, model, query, limit=20):
    """Find verses by semantic similarity to a query string."""
    # Embed query using same model
    query_vec = list(model.embed([f"query: {query}"]))[0]
    vec_bytes = struct.pack(f'{len(query_vec)}f', *query_vec)

    # Search sqlite-vec
    rows = conn.execute("""
        SELECT verse_id, distance FROM vec_verses
        WHERE embedding MATCH ? AND k = ?
        ORDER BY distance
    """, (vec_bytes, limit * 2)).fetchall()  # Fetch extra for potential filtering

    results = []
    for r in rows:
        v = conn.execute("""
            SELECT v.id, v.text_english, v.text_hebrew, v.text_greek,
                   b.title as book_title, v.chapter, v.verse
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (r["verse_id"],)).fetchone()
        if v:
            results.append({
                "verse": r["verse_id"],
                "reference": f"{v['book_title']} {v['chapter']}:{v['verse']}",
                "text": (v["text_english"] or "")[:200],
                "text_hebrew": (v["text_hebrew"] or "")[:100],
                "text_greek": (v["text_greek"] or "")[:100],
                "similarity": round(1.0 - r["distance"], 4),
            })

    return results[:limit]


def main():
    parser = argparse.ArgumentParser(description="Embed verses using fastembed transformer model")
    parser.add_argument("--reset", action="store_true", help="Rebuild from scratch")
    parser.add_argument("--book", type=str, default="", help="Embed only one book (e.g., 'gen')")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  Embedding Verses — {MODEL_NAME}")
    print("=" * 60)

    # Load embedding model
    print("\n--- Loading model...", flush=True)
    from fastembed import TextEmbedding
    model = TextEmbedding(
        model_name=MODEL_NAME,
        max_length=512,
        cache_dir=str(Path.home() / ".cache" / "fastembed"),
    )
    print(f"  Model loaded: {MODEL_NAME}")

    conn = get_db_vec()

    print("\n--- Embedding verses...", flush=True)
    total, skipped = embed_and_store(conn, model, reset=args.reset, book_filter=args.book)
    print(f"  Embedded: {total} new verses")
    print(f"  Skipped: {skipped}")

    # Verify
    try:
        count = conn.execute("SELECT COUNT(*) as c FROM vec_verses").fetchone()["c"]
    except Exception:
        count = 0
    print(f"  Total vectors: {count}")

    # Demo search
    if count > 0:
        print("\n--- Demo: Semantic Search ---")
        demos = [
            "shepherd and sheep",
            "covenant of peace",
            "angel of the lord appearance",
            "יהוה רועי",  # "The Lord is my shepherd" in Hebrew
            "ἀγάπη",       # "love" in Greek
        ]
        for query in demos:
            results = semantic_search(conn, model, query, limit=3)
            print(f"\n  '{query}':")
            for r in results:
                eng = r["text"][:60]
                heb = f" עברית:{r['text_hebrew'][:40]}" if r["text_hebrew"] else ""
                print(f"    {r['similarity']:.4f} {r['reference']:30s} {eng}{heb}")

    # Update server cache
    conn.execute("""
        INSERT OR REPLACE INTO ui_preferences (pref_key, pref_value)
        VALUES ('vec_available', 'true')
    """)
    conn.commit()

    conn.close()
    print(f"\n  Done. Run the web server to use semantic search.")
    print(f"  Try: curl 'http://localhost:8002/api/v1/semantic-search?q=covenant'")


if __name__ == "__main__":
    main()
