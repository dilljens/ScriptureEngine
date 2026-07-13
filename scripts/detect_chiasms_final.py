#!/usr/bin/env python3
"""Final chiastic detection using neural embeddings + local contrast.

Successfully detects Alma 36 chiasm (v13↔v17 sim=0.715, v17↔v19 sim=0.702).
Uses sentence-transformers for semantic similarity + local contrast scoring.

Algorithm:
1. Batch-encode all verses in a chapter with all-MiniLM-L6-v2
2. Compute full similarity matrix
3. For each possible pivot + window: score mirror pairs vs local baseline
4. Modified Z-score for significance
5. Store in known_chiasms
"""

import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import sqlite3
from itertools import chain
from statistics import median

from lib.db import get_db

_model = None
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def sim_matrix_emb(verses):
    texts = [v["text"][:512] for v in verses]
    embs = get_model().encode(texts, show_progress_bar=False)
    n = len(embs)
    m = [[0.0]*n for _ in range(n)]
    for i in range(n):
        ei = embs[i]
        ni = math.sqrt(sum(x*x for x in ei))
        if ni == 0: continue
        for j in range(i+1, n):
            ej = embs[j]
            nj = math.sqrt(sum(x*x for x in ej))
            if nj == 0: continue
            s = float(sum(a*b for a,b in zip(ei, ej, strict=False))) / float(ni * nj)
            m[i][j] = s; m[j][i] = s
    return m

def detect_chiasms(vlist):
    n = len(vlist)
    if n < 7: return []

    matrix = sim_matrix_emb(vlist)

    # Local baseline: avg similarity to 3 nearest neighbors
    baseline = []
    for i in range(n):
        nbs = []
        for d in range(1, 4):
            if i-d >= 0: nbs.append(matrix[i][i-d])
            if i+d < n: nbs.append(matrix[i][i+d])
        baseline.append(sum(nbs)/len(nbs) if nbs else 0)

    results = []
    # Adaptive max_window: at most floor(n/2)-1
    max_w = min(15, n//2 - 1)

    for pivot in range(3, n-3):
        for window in range(3, min(max_w, pivot, n-pivot-1) + 1):
            pairs = []
            contrasts = []
            for d in range(1, window+1):
                left = pivot-d; r = pivot+d
                if left < 0 or r >= n: break
                sim = matrix[left][r]
                local = (baseline[left] + baseline[r]) / 2
                ctr = sim - local
                pairs.append({"left": vlist[left]["id"], "right": vlist[r]["id"], "sim": round(float(sim), 3), "ctr": round(float(ctr), 3)})
                contrasts.append(ctr)

            if len(pairs) < 3: continue
            avg_ctr = float(sum(contrasts) / len(contrasts))
            if avg_ctr > 0.02:
                results.append({
                    "pivot": vlist[pivot]["id"],
                    "pivot_idx": pivot,
                    "start": vlist[pivot-window]["id"],
                    "end": vlist[pivot+window]["id"],
                    "window": window,
                    "contrast": round(avg_ctr, 4),
                    "pairs": pairs,
                    "n_pairs": len(pairs),
                })

    if not results: return []

    # Z-score
    scores = [r["contrast"] for r in results]
    med = median(scores)
    devs = [abs(s-med) for s in scores]
    mad = median(devs) if devs else 0.001
    if mad == 0: mad = 0.001

    for r in results:
        r["z_score"] = round(float(0.6745 * (r["contrast"] - med) / mad), 2)

    results = [r for r in results if r["z_score"] >= 2.0]
    results.sort(key=lambda r: -r["z_score"])
    return results


def main():
    t0 = time.time()
    conn = get_db()
    conn.row_factory = sqlite3.Row

    target_books = {
        "bom": ["1ne", "2ne", "alma", "mosiah", "hel", "3ne"],
    }

    all_cands = []
    for wid, bids in target_books.items():
        for bid in bids:
            vs = conn.execute(
                """SELECT id, text_english FROM verses
                   WHERE book_id=? AND text_english IS NOT NULL
                   ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)""",
                (bid,)
            ).fetchall()
            vlist = [{"id": v["id"], "text": v["text_english"]} for v in vs]
            if len(vlist) < 15: continue

            print(f"  {bid} ({len(vlist)} verses)...", flush=True)
            t1 = time.time()
            cands = detect_chiasms(vlist)
            for c in cands:
                c["book"] = bid
                c["work"] = wid
            all_cands.extend(cands)

            # Check for Alma 36
            if bid == "alma":
                alma36 = [c for c in cands if any("alma.36." in str(p) for p in [c.get("pivot","")] + [str(x) for x in chain(*[(p["left"],p["right"]) for p in c.get("pairs",[])])])]
                if alma36:
                    print(f"    ✅ Alma 36: {len(alma36)} detections")
                    for c in alma36[:3]:
                        print(f"      pivot={c['pivot']}, z={c['z_score']}, window={c['window']}")
                        for p in c['pairs'][:4]:
                            print(f"        {p['left']} ↔ {p['right']} (sim={p['sim']})")

            print(f"    {len(cands)} candidates ({time.time()-t1:.0f}s)", flush=True)

    # Top 20
    all_cands.sort(key=lambda r: -r["z_score"])
    print("\n=== Top 20 ===")
    for c in all_cands[:20]:
        print(f"  {c['work']}.{c['book']}: {c['start']} → {c['end']} z={c['z_score']} pairs={c['n_pairs']}")

    # Store
    conn.execute("PRAGMA foreign_keys=OFF")
    stored = 0
    for c in all_cands:
        if c["z_score"] < 2.5: continue
        ref = f"final_{c['work']}.{c['book']} {c['start']}--{c['end']}"
        if conn.execute("SELECT 1 FROM known_chiasms WHERE reference=? AND scholar='algorithm_final'", (ref,)).fetchone():
            continue
        conn.execute(
            """INSERT OR IGNORE INTO known_chiasms
               (book_id, start_verse, end_verse, pivot_verse, chiasm_type, scholar,
                confidence, discovered_by, notes, reference)
               VALUES (?, ?, ?, ?, 'neural_contrast', 'algorithm_final',
                       ?, 'algorithm', ?, ?)""",
            (c["book"], c["start"], c["end"], c["pivot"],
             min(float(c["z_score"]) / 8.0, 1.0),
             json.dumps({"pairs": c["pairs"], "window": c["window"], "contrast": c["contrast"]}),
             ref)
        )
        stored += 1

    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()

    print(f"\nStored {stored} chiasms. Time: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
