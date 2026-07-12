#!/usr/bin/env python3
"""Neural chiastic detection using Sentence-BERT embeddings.

McGovern et al. (NAACL 2025) approach with proper neural embeddings.

Uses sentence-transformers for semantic similarity at verse level.
Focuses on BoM first, then OT/NT.

Key improvements over v1:
- Real neural embeddings (all-MiniLM-L6-v2, 384-dim)
- Semantic cosine similarity, not just TF-IDF word overlap
- Proper contrast scoring: avg_mirror_pairs - avg_non_pairs
- Modified Z-score for significance (MAD-based)
- Captures thematic/conceptual chiasms (like Alma 36)
"""

import sys, os, re, math, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from collections import Counter
from statistics import median
from lib.db import get_db
import sqlite3

# ── Embedding model (loaded once) ──

_model = None
def get_model():
    global _model
    if _model is None:
        print("  Loading embedding model...", flush=True)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        print(f"  Model loaded (dim={_model.get_sentence_embedding_dimension()})", flush=True)
    return _model

# ── Chiastic Detection ──

def compute_similarity_matrix(verses):
    """Compute semantic similarity matrix using neural embeddings."""
    texts = [v["text"][:512] for v in verses]  # Truncate to 512 chars for efficiency
    model = get_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    
    n = len(embeddings)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ei = embeddings[i]
        norm_i = math.sqrt(sum(x*x for x in ei))
        if norm_i == 0: continue
        for j in range(i + 1, n):
            ej = embeddings[j]
            norm_j = math.sqrt(sum(x*x for x in ej))
            if norm_j == 0: continue
            dot = sum(a*b for a, b in zip(ei, ej))
            sim = dot / (norm_i * norm_j)
            matrix[i][j] = sim
            matrix[j][i] = sim
    return matrix

def detect_chiasms(verses, min_window=3, max_window=15, z_threshold=2.5):
    """Detect chiastic patterns using neural embedding contrast scoring.
    
    For each window of odd length 2*window+1 centered on a pivot verse:
      - Score = avg(mirror_pairs) - avg(non_pairs)
      - Significance via modified Z-score (MAD-based)
    """
    if len(verses) < 7:
        return []
    
    n = len(verses)
    matrix = compute_similarity_matrix(verses)
    raw_scores = []
    candidates = []
    
    for window in range(min_window, min(max_window + 1, n // 2)):
        for pivot in range(window, n - window):
            pair_scores = []
            non_pair_scores = []
            
            for d in range(1, window + 1):
                left = pivot - d
                right = pivot + d
                if left < 0 or right >= n:
                    break
                s = matrix[left][right]
                pair_scores.append(s)
                
                # Non-pair baseline
                for dd in range(1, window + 1):
                    if dd != d:
                        rr = pivot + dd
                        if rr < n:
                            non_pair_scores.append(matrix[left][rr])
            
            if not pair_scores or not non_pair_scores:
                continue
            
            avg_pairs = sum(pair_scores) / len(pair_scores)
            avg_non = sum(non_pair_scores) / len(non_pair_scores)
            score = avg_pairs - avg_non
            raw_scores.append(score)
            
            if score > 0.01:
                pairs = []
                for d in range(1, window + 1):
                    left = pivot - d
                    right = pivot + d
                    if left >= 0 and right < n:
                        pairs.append({
                            "left": verses[left]["id"],
                            "right": verses[right]["id"],
                            "similarity": round(matrix[left][right], 3),
                        })
                
                candidates.append({
                    "pivot": verses[pivot]["id"],
                    "start": verses[pivot - window]["id"],
                    "end": verses[pivot + window]["id"],
                    "window": window,
                    "score": score,
                    "pairs": pairs,
                    "matched_pairs": len(pairs),
                })
    
    if not raw_scores:
        return []
    
    # Modified Z-score
    med = median(raw_scores)
    abs_devs = [abs(s - med) for s in raw_scores]
    mad = median(abs_devs) if abs_devs else 0.001
    if mad == 0: mad = 0.001
    
    for c in candidates:
        c["z_score"] = 0.6745 * (c["score"] - med) / mad
    
    results = [c for c in candidates if c["z_score"] >= z_threshold]
    results.sort(key=lambda r: -r["z_score"])
    return results


def scan_book(conn, book_id, work_id):
    """Scan a single book."""
    verses = conn.execute(
        """SELECT id, text_english FROM verses 
           WHERE book_id=? AND text_english IS NOT NULL 
           ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)""",
        (book_id,)
    ).fetchall()
    
    vlist = [{"id": v["id"], "text": v["text_english"]} for v in verses]
    if len(vlist) < 15:
        return []
    
    results = detect_chiasms(vlist)
    for r in results:
        r["book"] = book_id
        r["work"] = work_id
    return results


def main():
    t0 = time.time()
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    # Focus on books with known chiasms
    book_focus = {
        "bom": ["1ne", "2ne", "alma", "mosiah", "hel", "3ne", "ether"],
        "ot": ["gen", "exo", "isa", "psa"],
        "nt": ["matt", "luke", "john"],
    }
    
    all_candidates = []
    for work_id, book_ids in book_focus.items():
        print(f"\nScanning {work_id}...", flush=True)
        for bid in book_ids:
            t1 = time.time()
            candidates = scan_book(conn, bid, work_id)
            elapsed = time.time() - t1
            print(f"  {bid}: {len(candidates)} candidates ({elapsed:.1f}s)", flush=True)
            all_candidates.extend(candidates)
    
    all_candidates.sort(key=lambda r: -r["z_score"])
    
    print(f"\n{'='*60}")
    print(f"Total candidates: {len(all_candidates)}")
    print(f"Time: {time.time()-t0:.1f}s")
    print(f"{'='*60}")
    
    # Top 30
    print(f"\nTop candidates:")
    for c in all_candidates[:30]:
        print(f"  {c['work']}.{c['book']}: {c['start']} → {c['end']}")
        print(f"    pivot={c['pivot']}, z={c['z_score']:.2f}, pairs={c['matched_pairs']}")
        # Show first 3 pairs
        for p in c['pairs'][:3]:
            print(f"      {p['left']} ↔ {p['right']} (sim={p['similarity']})")
    
    # Check Alma 36 specifically
    alma36 = [c for c in all_candidates if c["book"] == "alma" and "36" in c.get("start","") and "36" in c.get("end","")]
    print(f"\n{'='*60}")
    if alma36:
        print(f"✅ ALMA 36 FOUND! {len(alma36)} candidate(s)")
        for c in alma36:
            print(f"  Start: {c['start']}, End: {c['end']}, Pivot: {c['pivot']}")
            print(f"  Z-score: {c['z_score']:.2f}, Pairs: {c['matched_pairs']}")
            for p in c['pairs']:
                print(f"    {p['left']} ↔ {p['right']} (sim={p['similarity']})")
    else:
        print(f"❌ Alma 36 NOT found")
        # Show what the best alma candidates are
        alma_cands = [c for c in all_candidates if c["book"] == "alma"][:5]
        if alma_cands:
            print(f"  Best Alma candidates instead:")
            for c in alma_cands:
                print(f"    {c['start']} → {c['end']} (z={c['z_score']:.2f})")
    
    # Store
    conn.execute("PRAGMA foreign_keys=OFF")
    stored = 0
    for c in all_candidates:
        if c["z_score"] < 3.0:
            continue
        ref = f"v2_{c['work']}.{c['book']} {c['start']}--{c['end']}"
        existing = conn.execute(
            "SELECT id FROM known_chiasms WHERE reference=? AND scholar='algorithm_v2'",
            (ref,)
        ).fetchone()
        if existing:
            continue
        
        conn.execute(
            """INSERT OR IGNORE INTO known_chiasms 
               (book_id, start_verse, end_verse, pivot_verse, chiasm_type, scholar, 
                confidence, discovered_by, notes, reference)
               VALUES (?, ?, ?, ?, 'neural_contrast', 'algorithm_v2', 
                       ?, 'algorithm', ?, ?)""",
            (c["book"], c["start"], c["end"], c["pivot"],
             min(c["z_score"] / 10.0, 1.0),
             json.dumps(c),
             ref)
        )
        stored += 1
    
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()
    
    print(f"\nStored {stored} new chiasms in known_chiasms")


if __name__ == "__main__":
    main()
