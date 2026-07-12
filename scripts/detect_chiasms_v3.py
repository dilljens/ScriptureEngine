#!/usr/bin/env python3
"""Chiastic detection v3 — optimized for BoM thematic chiasms.

Key insight: BoM chiasms (like Alma 36) are thematic/conceptual, not lexical.
Neural embeddings capture this but produce high similarities everywhere.
Solution: use LOCAL CONTRAST — compare mirror pairs against the LOCAL
backdrop of ADJACENT verses (not all pairs), which is more sensitive.

Also: batch-encode ALL verses in a book at once for speed.
"""

import sys, os, re, math, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from collections import Counter
from statistics import median
from lib.db import get_db
import sqlite3

_model = None
def get_model():
    global _model
    if _model is None:
        print("  Loading model...", flush=True)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def compute_similarity_matrix_embeddings(verses):
    """Batch compute neural embedding similarity matrix."""
    texts = [v["text"][:512] for v in verses]
    model = get_model()
    embs = model.encode(texts, show_progress_bar=False)
    
    n = len(embs)
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        ei = embs[i]
        ni = math.sqrt(sum(x*x for x in ei))
        if ni == 0: continue
        for j in range(i + 1, n):
            ej = embs[j]
            nj = math.sqrt(sum(x*x for x in ej))
            if nj == 0: continue
            s = sum(a*b for a,b in zip(ei, ej)) / (ni * nj)
            matrix[i][j] = s
            matrix[j][i] = s
    return matrix

def detect_chiasms(verses, min_window=3, max_window=15):
    """Detect chiasms using local-contrast scoring.
    
    Score for each mirror pair = pair_similarity - avg_similarity_of_adjacent_verses
    This highlights pairs that stand out from their local context.
    """
    if len(verses) < 7: return []
    
    n = len(verses)
    matrix = compute_similarity_matrix_embeddings(verses)
    
    # Compute local baseline for each verse: avg similarity to its 3 nearest neighbors
    local_baseline = []
    for i in range(n):
        neighbors = []
        for d in range(1, 4):
            if i - d >= 0: neighbors.append(matrix[i][i-d])
            if i + d < n: neighbors.append(matrix[i][i+d])
        local_baseline.append(sum(neighbors)/len(neighbors) if neighbors else 0)
    
    candidates = []
    
    for window in range(min_window, min(max_window + 1, n // 2)):
        for pivot in range(window, n - window):
            pair_scores = []
            pair_contrasts = []
            
            for d in range(1, window + 1):
                left = pivot - d
                right = pivot + d
                if left < 0 or right >= n: break
                
                sim = matrix[left][right]
                
                # Local contrast: how much does this pair stand out?
                # compared to avg similarity of left with its local neighbors
                local_avg = (local_baseline[left] + local_baseline[right]) / 2
                contrast = sim - local_avg
                
                pair_scores.append(sim)
                pair_contrasts.append(contrast)
            
            if not pair_scores:
                continue
            
            # Chiasm score: avg contrast of mirror pairs
            # (how much do the mirror pairs stand out from local context?)
            avg_contrast = sum(pair_contrasts) / len(pair_contrasts)
            avg_sim = sum(pair_scores) / len(pair_scores)
            
            if avg_contrast > 0.02:  # At least slightly above local baseline
                pairs = []
                for d in range(1, window + 1):
                    left = pivot - d
                    right = pivot + d
                    if left >= 0 and right < n:
                        pairs.append({
                            "left": verses[left]["id"],
                            "right": verses[right]["id"],
                            "similarity": round(matrix[left][right], 3),
                            "contrast": round(pair_contrasts[d-1], 3),
                        })
                
                candidates.append({
                    "pivot": verses[pivot]["id"],
                    "start": verses[pivot - window]["id"],
                    "end": verses[pivot + window]["id"],
                    "window": window,
                    "score": round(avg_contrast, 4),
                    "avg_similarity": round(avg_sim, 4),
                    "pairs": pairs,
                    "matched_pairs": len(pairs),
                })
    
    # Z-score on contrast scores
    if not candidates: return []
    scores = [c["score"] for c in candidates]
    med = median(scores)
    abs_devs = [abs(s - med) for s in scores]
    mad = median(abs_devs) if abs_devs else 0.001
    if mad == 0: mad = 0.001
    
    for c in candidates:
        c["z_score"] = round(0.6745 * (c["score"] - med) / mad, 2)
    
    results = [c for c in candidates if c["z_score"] >= 2.0]
    results.sort(key=lambda r: -r["z_score"])
    return results


def main():
    t0 = time.time()
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    focus_books = {
        "bom": ["1ne", "2ne", "alma", "mosiah", "hel", "3ne"],
    }
    
    all_candidates = []
    for work_id, book_ids in focus_books.items():
        print(f"\nScanning {work_id}...", flush=True)
        for bid in book_ids:
            t1 = time.time()
            verses = conn.execute(
                """SELECT id, text_english FROM verses 
                   WHERE book_id=? AND text_english IS NOT NULL 
                   ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)""",
                (bid,)
            ).fetchall()
            vlist = [{"id": v["id"], "text": v["text_english"]} for v in verses]
            if len(vlist) < 15:
                continue
            
            candidates = detect_chiasms(vlist)
            elapsed = time.time() - t1
            for c in candidates:
                c["book"] = bid
                c["work"] = work_id
            all_candidates.extend(candidates)
            print(f"  {bid}: {len(candidates)} candidates ({elapsed:.0f}s)", flush=True)
            
            # Check for Alma 36 immediately
            if bid == "alma":
                alma36 = [c for c in candidates if any("36" in str(p) for p in [c.get("start",""), c.get("end",""), c.get("pivot","")])]
                if alma36:
                    print(f"    ✅ Alma 36 candidates: {len(alma36)}")
                    for c in alma36[:3]:
                        print(f"      {c['start']} → {c['end']} z={c['z_score']} pivot={c['pivot']}")
                        for p in c['pairs'][:4]:
                            print(f"        {p['left']} ↔ {p['right']} (sim={p['similarity']}, ctr={p['contrast']})")
    
    all_candidates.sort(key=lambda r: -r["z_score"])
    
    print(f"\n{'='*60}")
    print(f"Total: {len(all_candidates)} candidates in {time.time()-t0:.0f}s")
    
    # Top 20
    print(f"\nTop candidates:")
    for c in all_candidates[:20]:
        print(f"  {c['work']}.{c['book']}: {c['start']} → {c['end']} z={c['z_score']} (pairs={c['matched_pairs']})")
    
    # Store
    conn.execute("PRAGMA foreign_keys=OFF")
    stored = 0
    for c in all_candidates:
        if c["z_score"] < 2.5:
            continue
        ref = f"v3_{c['work']}.{c['book']} {c['start']}--{c['end']}"
        existing = conn.execute(
            "SELECT id FROM known_chiasms WHERE reference=? AND scholar='algorithm_v3'",
            (ref,)
        ).fetchone()
        if existing:
            continue
        
        conn.execute(
            """INSERT OR IGNORE INTO known_chiasms 
               (book_id, start_verse, end_verse, pivot_verse, chiasm_type, scholar, 
                confidence, discovered_by, notes, reference)
               VALUES (?, ?, ?, ?, 'neural_contrast', 'algorithm_v3', 
                       ?, 'algorithm', ?, ?)""",
            (c["book"], c["start"], c["end"], c["pivot"],
             min(c["z_score"] / 5.0, 1.0),
             json.dumps(c),
             ref)
        )
        stored += 1
    
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()
    
    print(f"\nStored {stored} new chiasms")


if __name__ == "__main__":
    main()
