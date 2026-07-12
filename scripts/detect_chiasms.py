#!/usr/bin/env python3
"""Verse-level chiastic detection using McGovern et al. (NAACL 2025) approach.

Uses verse-level units, multi-dimension similarity, and contrast scoring.
Focused on the Book of Mormon (known chiasms: Alma 36, 1 Ne, Mosiah, etc.).

Method:
1. For each book, slide a window of N verses (N = 10 to 30, odd)
2. Compute similarity matrix using lexical (TF-IDF) + structural features
3. Score chiasm: avg_mirror_pairs - avg_non_pairs (contrast score)
4. Modified Z-score for significance using MAD
5. Top candidates stored in known_chiasms
"""

import sys, os, re, math, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from collections import Counter
from statistics import median
from lib.db import get_db

# ── Text vectorization ──

def tokenize(text):
    if not text: return []
    return re.findall(r"[a-zA-Z']+", text.lower())

def get_lexical_vector(text):
    """TF-IDF-like word frequency vector."""
    tokens = tokenize(text)
    return Counter(tokens)

def get_structural_vector(text):
    """Structural features: length, sentence count, word count, avg word length."""
    if not text:
        return [0, 0, 0, 0]
    words = tokenize(text)
    sentences = len(re.findall(r'[.!?]+', text)) or 1
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
    return [len(text), len(words), sentences, avg_word_len]

def cosine_similarity(c1, c2):
    """Cosine similarity between two Counters."""
    if isinstance(c1, Counter):
        common = set(c1.keys()) & set(c2.keys())
        if not common: return 0.0
        dot = sum(c1[w] * c2[w] for w in common)
        mag1 = math.sqrt(sum(v * v for v in c1.values()))
        mag2 = math.sqrt(sum(v * v for v in c2.values()))
    else:
        # Structural vectors (lists)
        dot = sum(a * b for a, b in zip(c1, c2))
        mag1 = math.sqrt(sum(a * a for a in c1))
        mag2 = math.sqrt(sum(b * b for b in c2))
    if mag1 == 0 or mag2 == 0: return 0.0
    return dot / (mag1 * mag2)

# ── Chiastic Detection (McGovern scoring) ──

def compute_similarity_matrix(verses):
    """Compute full similarity matrix for a list of verses.
    
    Each verse is a dict with 'id' and 'text'.
    Similarity = 0.7 * lexical_cosine + 0.3 * structural_cosine
    """
    n = len(verses)
    lex_vecs = [get_lexical_vector(v["text"]) for v in verses]
    str_vecs = [get_structural_vector(v["text"]) for v in verses]
    
    matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            lex_sim = cosine_similarity(lex_vecs[i], lex_vecs[j])
            str_sim = cosine_similarity(str_vecs[i], str_vecs[j])
            matrix[i][j] = 0.7 * lex_sim + 0.3 * str_sim
            matrix[j][i] = matrix[i][j]
    return matrix

def detect_chiasms(verses, min_window=3, max_window=15, z_threshold=3.5):
    """Detect chiastic patterns using McGovern et al. contrast scoring.
    
    For each window of odd length 2*window+1 centered on a pivot verse:
      - Mirror pairs: (pivot-1, pivot+1), (pivot-2, pivot+2), ...
      - Non-pairs: any other off-diagonal within the window
      - Score = avg(mirror_pair_similarities) - avg(non_pair_similarities)
      - Significance via modified Z-score (MAD-based)
    
    Returns: list of {pivot, start, end, score, z_score, pairs}
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
                pair_scores.append(matrix[left][right])
                
                # Non-pair baseline: left vs all other right-side (non-matching)
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
            
            if score > 0:  # Only store positive scores initially
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
                    "pivot_idx": pivot,
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
    
    # Modified Z-score using MAD (per McGovern et al.)
    med = median(raw_scores)
    abs_devs = [abs(s - med) for s in raw_scores]
    mad = median(abs_devs) if abs_devs else 0.001
    if mad == 0:
        mad = 0.001
    
    for c in candidates:
        c["z_score"] = 0.6745 * (c["score"] - med) / mad
    
    # Filter by z_score threshold
    results = [c for c in candidates if c["z_score"] >= z_threshold]
    results.sort(key=lambda r: -r["z_score"])
    
    return results


def scan_book(conn, book_id, work_id):
    """Scan a single book for chiastic structures."""
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
    conn = get_db()
    conn.row_factory = sqlite3.Row
    
    # Focus on BoM books with known chiasms, plus OT/NT books
    book_focus = {
        "bom": ["1ne", "2ne", "jacob", "mosiah", "alma", "hel", "3ne", "morm", "ether"],
        "ot": ["gen", "exo", "lev", "num", "deu", "isa", "jer", "ezek", "psa", "prov"],
        "nt": ["matt", "mark", "luke", "john", "acts", "rom", "heb"],
    }
    
    all_candidates = []
    for work_id, book_ids in book_focus.items():
        print(f"Scanning {work_id}...", flush=True)
        for bid in book_ids:
            candidates = scan_book(conn, bid, work_id)
            if candidates:
                print(f"  {bid}: {len(candidates)} candidates", flush=True)
                all_candidates.extend(candidates)
    
    # Sort by z_score
    all_candidates.sort(key=lambda r: -r["z_score"])
    
    print(f"\n=== Results ===")
    print(f"Total candidates: {len(all_candidates)}")
    
    # Show top 30
    print(f"\nTop candidates:")
    for c in all_candidates[:30]:
        print(f"  {c['work']}.{c['book']}: {c['start']} → {c['end']}")
        print(f"    pivot={c['pivot']}, score={c['score']:.4f}, z={c['z_score']:.2f}, pairs={c['matched_pairs']}")
    
    # Store in known_chiasms
    conn.execute("PRAGMA foreign_keys=OFF")
    stored = 0
    for c in all_candidates:
        if c["z_score"] < 3.5:
            continue
        
        ref = f"{c['work']}.{c['book']} {c['start']}--{c['end']}"
        existing = conn.execute(
            "SELECT id FROM known_chiasms WHERE reference=? AND scholar='algorithm'",
            (ref,)
        ).fetchone()
        if existing:
            continue
        
        conn.execute(
            """INSERT OR IGNORE INTO known_chiasms 
               (book_id, start_verse, end_verse, pivot_verse, chiasm_type, scholar, 
                confidence, discovered_by, notes, reference)
               VALUES (?, ?, ?, ?, 'verse_contrast', 'algorithm', 
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
    
    # Check if Alma 36 was found
    alma36 = [c for c in all_candidates if c["book"] == "alma" and "alma.36" in str(c)]
    if alma36:
        print(f"\n✅ ALMA 36 FOUND! {len(alma36)} candidate(s)")
        for c in alma36[:3]:
            print(f"  Start: {c['start']}, End: {c['end']}, Pivot: {c['pivot']}")
            print(f"  Score: {c['score']:.4f}, Z: {c['z_score']:.2f}")
    else:
        print("\n❌ Alma 36 NOT found as a chiasm candidate")
    
    # Check 1 Nephi
    nephi1 = len([c for c in all_candidates if c["book"] == "1ne" and c["z_score"] >= 3.0])
    print(f"1 Nephi candidates (z>=3): {nephi1}")


if __name__ == "__main__":
    import sqlite3
    main()
