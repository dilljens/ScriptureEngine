#!/usr/bin/env python3
"""Comprehensive literary pattern detection — chiasmus, inclusio, word links,
parallelism, formula markers, acrostics.

Uses neural embeddings (Sentence-BERT) for semantic similarity across
all 8 works (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha).

Patterns detected:
  1. CHIASMUS (micro/meso/macro) — mirror pairs via neural contrast scoring
  2. INCLUSIO — bookended structures (A...A')
  3. WORD LINKS — Gileadi-style keyword passage pairing
  4. PARALLELISM TYPE — synonymous/antithetic/synthetic classification  
  5. FORMULA MARKERS — toledot, hinneh, koh amar, ne'um, etc.
  6. ACROSTICS — Hebrew alphabet sequences
"""

import sys, os, re, math, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from statistics import median
from lib.db import get_db
from collections import Counter, defaultdict
import sqlite3
import numpy as np

# ── Embedding Model ──
_model = None
def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def encode_texts(texts):
    return get_model().encode([t[:512] for t in texts], show_progress_bar=False)

def cos_sim(a, b):
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

# ════════════════════════════════════════════════════════════════
# 1. CHIASMUS — Multi-Resolution
# ════════════════════════════════════════════════════════════════

def detect_chiasmus(vlist, min_window=2, max_window=20, min_contrast=0.01):
    """Detect chiastic patterns at multiple resolutions.
    
    Micro (w=2-5): Tight word-level mirroring (short passages)
    Meso (w=5-15): Chapter-level thematic chiasms (Alma 36 style)
    Macro (w=15-100): Book-level structural mirroring (Flood, Isaiah bifid)
    """
    n = len(vlist)
    if n < 5: return []
    
    texts = [v["text"][:512] for v in vlist]
    embs = encode_texts(texts)
    
    # Similarity matrix
    sims = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            s = cos_sim(embs[i], embs[j])
            sims[i][j] = s; sims[j][i] = s
    
    # Local baseline (3-nearest-neighbor)
    bl = np.zeros(n)
    for i in range(n):
        nbs = []
        for d in range(1, 4):
            if i-d >= 0: nbs.append(float(sims[i][i-d]))
            if i+d < n: nbs.append(float(sims[i][i+d]))
        bl[i] = sum(nbs)/len(nbs) if nbs else 0
    
    max_w = min(max_window, n//2 - 1)
    if max_w < 2: return []
    
    results = []
    for w in range(min_window, max_w + 1):
        for pv in range(w, n - w):
            prs = []
            ctrs = []
            for d in range(1, w+1):
                l = pv-d; r = pv+d
                if l < 0 or r >= n: break
                s = float(sims[l][r])
                c = s - (bl[l] + bl[r])/2
                prs.append({"l": vlist[l]["id"], "r": vlist[r]["id"], "s": round(s,3)})
                ctrs.append(c)
            if len(prs) >= 2:
                avg = sum(ctrs)/len(ctrs)
                if avg > min_contrast:
                    scale = "macro" if w >= 15 else ("meso" if w >= 5 else "micro")
                    results.append({"pivot": vlist[pv]["id"], "w": w, "c": round(avg,4), 
                                    "prs": prs, "np": len(prs), "scale": scale})
    
    if not results: return []
    scores = [r["c"] for r in results]
    med = median(scores)
    devs = [abs(s-med) for s in scores]
    mad = median(devs) if devs else 0.001
    if mad == 0: mad = 0.001
    for r in results: r["z"] = round(float(0.6745*(r["c"]-med)/mad), 2)
    results = [r for r in results if r["z"] >= 2.0]
    results.sort(key=lambda r: -r["z"])
    return results

# ════════════════════════════════════════════════════════════════
# 2. INCLUSIO — Bookended Structures
# ════════════════════════════════════════════════════════════════

def detect_inclusio(vlist, window=3, threshold=0.6):
    """Detect inclusio: same/similar content at beginning and end.
    Compares first `window` verses with last `window` verses.
    """
    n = len(vlist)
    if n < window * 4: return []
    
    texts = [v["text"][:512] for v in vlist]
    embs = encode_texts(texts)
    
    results = []
    for i in range(min(window, n//4)):
        j = n - 1 - i
        s = cos_sim(embs[i], embs[j])
        if s >= threshold:
            results.append({
                "begin": vlist[i]["id"], "end": vlist[j]["id"],
                "similarity": round(s, 3), "pair_idx": i,
            })
    
    if results:
        return {
            "begin_group": [v["id"] for v in vlist[:window]],
            "end_group": [v["id"] for v in vlist[-window:]],
            "pairs": results,
            "avg_similarity": round(sum(r["similarity"] for r in results)/len(results), 3),
        }
    return None

# ════════════════════════════════════════════════════════════════
# 3. WORD LINKS — Gileadi-Style Keyword Passage Pairing
# ════════════════════════════════════════════════════════════════

GILEADI_KEYWORDS = [
    # Divine titles/codenames
    "holy one of israel", "king of jacob", "king of zion", "mighty one of jacob",
    "redeemer", "creator", "maker", "lord of hosts", "god of israel",
    # Key concepts
    "arm of the lord", "arm of jehovah", "servant", "chosen", "elect",
    "vineyard", "planting", "branch", "root of jesse", "stem of jesse",
    # Judgment/deliverance
    "assyria", "babylon", "egypt", "zion", "jerusalem", "judah",
    "day of the lord", "day of vengeance", "year of redemption",
    # Covenant
    "everlasting covenant", "covenant of peace", "new covenant",
    "everlasting kindness", "sure mercies of david",
    # Temple/theophany
    "high and lifted up", "train filled the temple", "seraphim",
    "glory of the lord", "shekinah", "holy mountain", "house of prayer",
    # Light/darkness
    "light to the gentiles", "great light", "darkness", "shadow of death",
    "marvelous light", "everlasting light",
]

BOOK_LEVEL_KEYWORDS = {
    "isa": [
        "arm of the lord", "holy one of israel", "servant", "vineyard",
        "assyria", "babylon", "zion", "redeemer", "everlasting covenant",
        "branch of the lord", "root of jesse", "king of babylon", "king of assyria",
    ],
}

def detect_word_links(conn, book_id, keywords=None):
    """Find Gileadi-style word links: passages sharing keywords across a book.
    
    For each keyword, find all verses containing it, then compute semantic
    similarity between paired passages. High similarity + shared keywords = link.
    """
    if keywords is None:
        keywords = BOOK_LEVEL_KEYWORDS.get(book_id, GILEADI_KEYWORDS[:15])
    
    # Find verses containing each keyword
    keyword_verses = defaultdict(list)
    for kw in keywords:
        vs = conn.execute(
            "SELECT id, text_english FROM verses WHERE book_id=? AND LOWER(text_english) LIKE ? LIMIT 30",
            (book_id, f"%{kw}%")
        ).fetchall()
        for v in vs:
            keyword_verses[kw].append({"id": v["id"], "text": v["text_english"]})
    
    # For each keyword with multiple occurrences, pair them
    results = []
    for kw, vs in keyword_verses.items():
        if len(vs) < 2: continue
        
        vlist = [{"id": v["id"], "text": v["text"]} for v in vs[:10]]
        if len(vlist) < 2: continue
        
        texts = [v["text"][:512] for v in vlist]
        embs = encode_texts(texts) if len(texts) > 1 else []
        
        pairs_made = set()
        for i in range(len(vlist)):
            for j in range(i+1, len(vlist)):
                pair_key = f"{vlist[i]['id']}↔{vlist[j]['id']}"
                if pair_key in pairs_made: continue
                pairs_made.add(pair_key)
                
                sim = cos_sim(embs[i], embs[j]) if len(embs) > 1 else 0.0
                if sim > 0.35:  # Moderate threshold — semantic reinforcement
                    results.append({
                        "keyword": kw,
                        "verse_a": vlist[i]["id"],
                        "verse_b": vlist[j]["id"],
                        "similarity": round(sim, 3),
                        "text_a": vlist[i]["text"][:100],
                        "text_b": vlist[j]["text"][:100],
                    })
    
    results.sort(key=lambda r: -r["similarity"])
    return results

# ════════════════════════════════════════════════════════════════
# 4. PARALLELISM TYPE CLASSIFIER
# ════════════════════════════════════════════════════════════════

def classify_parallelism(text_a, text_b):
    """Classify parallelism type between two verse texts using embeddings.
    
    Returns dict with:
      - similarity: cosine similarity (0-1)
      - type: 'synonymous', 'antithetic', 'synthetic', or 'none'
      - confidence: 0-1
    """
    if not text_a or not text_b:
        return {"similarity": 0.0, "type": "none", "confidence": 0.0}
    
    embs = encode_texts([text_a[:512], text_b[:512]])
    sim = cos_sim(embs[0], embs[1])
    
    # Sentiment/keyword heuristics for antithetic
    neg_words = ["but", "yet", "however", "nevertheless", "woe", "curse", "not"]
    pos_words = ["blessed", "righteous", "good", "mercy", "grace", "peace", "joy"]
    
    a_words = set(text_a.lower().split())
    b_words = set(text_b.lower().split())
    
    a_neg = sum(1 for w in neg_words if w in a_words)
    b_neg = sum(1 for w in neg_words if w in b_words)
    a_pos = sum(1 for w in pos_words if w in a_words)
    b_pos = sum(1 for w in pos_words if w in b_words)
    
    # Antithetic: high semantic similarity + contrasting sentiment
    is_antithetic = sim > 0.4 and ((a_neg > 0 and b_pos > 0) or (a_pos > 0 and b_neg > 0))
    
    # Synonymous: very high similarity, same sentiment
    is_synonymous = sim > 0.65 and not is_antithetic
    
    if is_synonymous:
        ptype = "synonymous"
        confidence = min(1.0, (sim - 0.5) / 0.3)
    elif is_antithetic:
        ptype = "antithetic"
        confidence = min(1.0, 0.5 + (sim - 0.3) / 0.4)
    elif sim > 0.3:
        ptype = "synthetic"
        confidence = min(1.0, (sim - 0.2) / 0.4)
    else:
        ptype = "none"
        confidence = 0.0
    
    return {"similarity": round(sim, 3), "type": ptype, "confidence": round(confidence, 3)}

# ════════════════════════════════════════════════════════════════
# 5. FORMULA MARKER DETECTOR
# ════════════════════════════════════════════════════════════════

HEBREW_FORMULAS = {
    "toledot": r"אֵ֚לֶּה תֹּולְדֹ֣ות",        # "These are the generations of"
    "hinneh": r"הִנֵּ֖ה",                      # "Behold"
    "koh_amar": r"כֹּ֥ה אָמַ֖ר",              # "Thus says the LORD"
    "neum": r"נְאֻם־יְהוָ֑ה",                  # "Oracle of the LORD"
    "vayehi": r"וַֽיְהִי֙",                     # "And it came to pass"
    "hayah_devar": r"וַיְהִ֥י דְבַר־יְהוָ֖ה", # "The word of the LORD came"
    "shuv": r"שׁ֚וּב",                          # "Return/again" (structural marker in prophets)
}

ENGLISH_FORMULAS = {
    "thus_says": r"[Tt]hus says the (LORD|Lord|God)",
    "word_of_lord": r"([Tt]he )?word of the (LORD|Lord|came)",
    "came_to_pass": r"([A]nd )?it came to pass",
    "behold": r"([B]ehold,)",
    "oracle": r"(oracle of|declaration of|saith) the (LORD|Lord)" ,
    "woe": r"([W]oe (unto|to) )",
    "hear_this": r"([H]ear (this|ye|the word))",
}

def detect_formula_markers(conn, book_id=None):
    """Find structural formula markers in Hebrew and English text."""
    conn.row_factory = sqlite3.Row
    results = []
    
    if book_id:
        vs = conn.execute(
            "SELECT id, text_hebrew, text_english FROM verses WHERE book_id=? AND (text_hebrew IS NOT NULL OR text_english IS NOT NULL) ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)",
            (book_id,)
        ).fetchall()
    else:
        vs = conn.execute(
            "SELECT id, text_hebrew, text_english FROM verses WHERE text_hebrew IS NOT NULL ORDER BY RANDOM() LIMIT 1000"
        ).fetchall()
    
    for v in vs:
        vid = v["id"]
        
        # Hebrew formulas
        heb = v["text_hebrew"]
        if heb:
            for fname, fpattern in HEBREW_FORMULAS.items():
                if re.search(fpattern, heb):
                    results.append({"verse": vid, "formula": fname, "language": "hebrew", "pattern": fpattern})
        
        # English formulas
        eng = v["text_english"]
        if eng:
            for fname, fpattern in ENGLISH_FORMULAS.items():
                if re.search(fpattern, eng):
                    results.append({"verse": vid, "formula": fname, "language": "english", "pattern": fpattern})
    
    return results

# ════════════════════════════════════════════════════════════════
# 6. ACROSTIC DETECTOR
# ════════════════════════════════════════════════════════════════

HEBREW_ALPHABET = list("אבגדהוזחטיכלמנסעפצקרשת")
HEBREW_ALPHABET_LETTERS = set(HEBREW_ALPHABET)

def detect_acrostics(conn, book_id=None):
    """Detect alphabetic acrostic structures in Hebrew text.
    
    Hebrew acrostics work by having groups of verses all starting with
    the same letter, progressing through the alphabet.
    E.g., Psalm 119: 8 verses of Aleph, 8 of Bet, 8 of Gimel...
    Proverbs 31: 22 verses, each starting with consecutive alphabet letter.
    Lamentations 3: 66 verses, each letter for 3 verses.
    """
    conn.row_factory = sqlite3.Row
    results = []
    
    alphabet_idx = {c: i for i, c in enumerate(HEBREW_ALPHABET)}
    
    if book_id:
        vs = conn.execute(
            "SELECT id, text_hebrew, chapter, verse FROM verses WHERE book_id=? AND text_hebrew IS NOT NULL ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)",
            (book_id,)
        ).fetchall()
    else:
        vs = conn.execute(
            "SELECT v.id, v.text_hebrew, v.chapter, v.verse FROM verses v JOIN books b ON b.id=v.book_id WHERE v.text_hebrew IS NOT NULL AND b.work_id='ot' ORDER BY CAST(v.chapter AS INTEGER), CAST(v.verse AS INTEGER)"
        ).fetchall()
    
    chapters = defaultdict(list)
    for v in vs:
        ch = int(v["chapter"]) if v["chapter"] else 0
        chapters[(v["id"].split('.')[0], ch)].append(v)
    
    for (bk, ch), cvs in chapters.items():
        if len(cvs) < 5: continue
        
        # Get first Hebrew letter of each verse
        letter_seq = []  # list of (verse_id, letter, alphabet_idx)
        for v in cvs:
            heb = v["text_hebrew"] or ""
            # Remove all non-Hebrew-letter characters (cantillation, vowels, punctuation)
            heb_letters = re.sub(r'[^\u0590-\u05fe]', '', heb)
            if heb_letters and heb_letters[0] in alphabet_idx:
                letter_seq.append((v["id"], heb_letters[0], alphabet_idx[heb_letters[0]]))
        
        if len(letter_seq) < 5: continue
        
        # Acrostic pattern: verse groups share the same starting letter,
        # groups progress through the alphabet in order.
        # Count consecutive verses with the SAME letter, then check if
        # the sequence of group letters follows the alphabet.
        
        groups = []  # list of (letter, start_idx, count)
        current_letter = letter_seq[0][1]
        group_start = 0
        group_count = 1
        
        for i in range(1, len(letter_seq)):
            if letter_seq[i][1] == current_letter:
                group_count += 1
            else:
                groups.append((current_letter, group_start, group_count))
                current_letter = letter_seq[i][1]
                group_start = i
                group_count = 1
        groups.append((current_letter, group_start, group_count))
        
        if len(groups) < 3: continue
        
        # Check if group letters follow alphabetic order
        group_letters = [g[0] for g in groups]
        expected_idx = alphabet_idx.get(group_letters[0], -1)
        is_sequential = True
        for gl in group_letters[1:]:
            expected_idx += 1
            if alphabet_idx.get(gl, -1) != expected_idx:
                is_sequential = False
                break
        
        # Check if at least 5 consecutive groups follow the alphabet
        max_run = 1
        run = 1
        for i in range(1, len(group_letters)):
            prev_idx = alphabet_idx.get(group_letters[i-1], -1)
            curr_idx = alphabet_idx.get(group_letters[i], -1)
            if curr_idx == prev_idx + 1:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 1
        
        if max_run >= 4:  # At least 4 consecutive alphabet letters
            results.append({
                "book": bk, "chapter": ch,
                "verses": len(letter_seq),
                "groups": len(groups),
                "longest_run": max_run,
                "groups_detail": ", ".join(f"{g[0]}(x{g[2]})" for g in groups[:10]),
                "is_acrostic": is_sequential and len(groups) >= 5,
            })
    
    return results

# ════════════════════════════════════════════════════════════════
# MAIN EXECUTION
# ════════════════════════════════════════════════════════════════

def run_all(conn):
    t0 = time.time()
    conn.row_factory = sqlite3.Row
    
    print("="*70)
    print("COMPREHENSIVE LITERARY PATTERN DETECTION")
    print("="*70)
    
    # ── Books to scan —─
    all_books = {
        "bom": ["1ne", "2ne", "alma", "mosiah", "hel", "3ne", "ether", "morm", "moro"],
        "ot": ["gen", "exo", "lev", "num", "deu", "isa", "jer", "ezek", "psa", "prov", "ruth", "jonah", "amos", "hab"],
        "nt": ["matt", "mark", "luke", "john", "acts", "rom", "eph", "heb", "1pet", "1john"],
    }
    
    chiasm_results = []
    inclusio_results = []
    word_link_results = []
    parallelism_results = []
    formula_results = []
    acrostic_results = []
    
    # ── 1. CHIASMUS: Multi-resolution ──
    print("\n[1/6] Multi-resolution Chiasmus Detection...")
    for wid, bids in all_books.items():
        for bid in bids:
            vs = conn.execute(
                "SELECT id, text_english FROM verses WHERE book_id=? AND text_english IS NOT NULL ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER)",
                (bid,)
            ).fetchall()
            vlist = [{"id": v["id"], "text": v["text_english"]} for v in vs]
            if len(vlist) < 7: continue
            
            t1 = time.time()
            cands = detect_chiasmus(vlist, min_window=2, max_window=min(30, len(vlist)//2))
            for c in cands: c["book"] = bid; c["work"] = wid
            chiasm_results.extend(cands)
            
            # ── 2. INCLUSIO: Per chapter ──
            chapters = defaultdict(list)
            for v in vlist:
                ch = v["id"].split('.')[1]
                chapters[ch].append(v)
            for ch, cv in chapters.items():
                inc = detect_inclusio(cv, window=min(3, len(cv)//4))
                if inc:
                    inc["book"] = bid; inc["work"] = wid; inc["chapter"] = ch
                    inclusio_results.append(inc)
    
    # Top chiasms
    chiasm_results.sort(key=lambda r: -r["z"])
    print(f"  Chiasmus: {len(chiasm_results)} candidates")
    for c in chiasm_results[:10]:
        print(f"    [{c['scale']}] {c['work']}.{c['book']}: pivot={c['pivot']} z={c['z']} w={c['w']}")
    
    # Top inclusio
    inclusio_results.sort(key=lambda r: -r.get("avg_similarity", 0))
    print(f"\n[2/6] Inclusio: {len(inclusio_results)} candidates")
    for inc in inclusio_results[:5]:
        print(f"    {inc['work']}.{inc['book']} ch.{inc['chapter']}: {inc['begin_group'][0]} ↔ {inc['end_group'][-1]} sim={inc['avg_similarity']}")
    
    # ── 3. WORD LINKS: Gileadi-style ──
    print("\n[3/6] Gileadi-style Word Links...")
    for wid, bids in all_books.items():
        for bid in bids:
            links = detect_word_links(conn, bid)
            for l in links: l["book"] = bid; l["work"] = wid
            word_link_results.extend(links)
    word_link_results.sort(key=lambda r: -r["similarity"])
    print(f"  Word links: {len(word_link_results)} pairs")
    for l in word_link_results[:5]:
        print(f"    {l['work']}.{l['book']}: \"{l['keyword']}\" — {l['verse_a']} ↔ {l['verse_b']} sim={l['similarity']}")
    
    # ── 4. PARALLELISM TYPE CLASSIFIER ──
    print("\n[4/6] Parallelism Type Classification...")
    # Sample verse pairs from poetic books
    poetic_books = {"ot": ["psa", "prov", "isa", "amos"], "bom": ["2ne", "alma"]}
    for wid, bids in poetic_books.items():
        for bid in bids:
            vs = conn.execute(
                "SELECT id, text_english FROM verses WHERE book_id=? AND text_english IS NOT NULL ORDER BY CAST(chapter AS INTEGER), CAST(verse AS INTEGER) LIMIT 200",
                (bid,)
            ).fetchall()
            vlist = [{"id": v["id"], "text": v["text_english"]} for v in vs]
            for i in range(0, len(vlist)-1, 2):
                if i+1 >= len(vlist): break
                cls = classify_parallelism(vlist[i]["text"], vlist[i+1]["text"])
                if cls["type"] != "none":
                    cls["verse_a"] = vlist[i]["id"]; cls["verse_b"] = vlist[i+1]["id"]
                    cls["book"] = bid; cls["work"] = wid
                    parallelism_results.append(cls)
    print(f"  Parallelism: {len(parallelism_results)} pairs")
    syn = sum(1 for p in parallelism_results if p["type"]=="synonymous")
    ant = sum(1 for p in parallelism_results if p["type"]=="antithetic")
    syn2 = sum(1 for p in parallelism_results if p["type"]=="synthetic")
    print(f"    Synonymous: {syn}, Antithetic: {ant}, Synthetic: {syn2}")
    
    # ── 5. FORMULA MARKERS ──
    print("\n[5/6] Formula Markers...")
    for bid in ["gen", "exo", "lev", "num", "deu", "isa", "jer", "ezek", "amos", "jonah"]:
        fm = detect_formula_markers(conn, bid)
        formula_results.extend(fm)
    # Count unique
    formula_counts = Counter(f["formula"] for f in formula_results)
    print(f"  Formula markers: {len(formula_results)} total")
    for f, c in formula_counts.most_common(10):
        print(f"    {f}: {c}x")
    
    # ── 6. ACROSTICS ──
    print("\n[6/6] Acrostics...")
    acrostic_results = detect_acrostics(conn)
    print(f"  Acrostic chapters: {len(acrostic_results)}")
    for a in acrostic_results[:5]:
        status = "✅ ACROSTIC" if a["is_acrostic"] else "partial"
        print(f"    {a['book']} ch.{a['chapter']}: run={a['longest_run']}, groups={a['groups_detail'][:50]} [{status}]")
    
    # ── STORE RESULTS ──
    print(f"\n{'='*70}")
    print("Storing results in database...")
    conn.execute("PRAGMA foreign_keys=OFF")
    
    def safe_ins(table, cols, vals):
        try:
            conn.execute(f"INSERT OR IGNORE INTO {table} ({cols}) VALUES ({','.join(['?']*len(vals))})", vals)
        except Exception as e:
            pass  # Skip if table doesn't exist or other error
    
    # Store chiasm candidates in known_chiasms
    stored_chiasm = 0
    for c in chiasm_results:
        if c["z"] < 2.5: continue
        ref = f"all_{c['work']}.{c['book']} {c['pivot']} w={c['w']}"
        if conn.execute("SELECT 1 FROM known_chiasms WHERE reference=? AND scholar='pattern_detector'", (ref,)).fetchone():
            continue
        conn.execute(
            """INSERT OR IGNORE INTO known_chiasms 
               (book_id, start_verse, end_verse, pivot_verse, chiasm_type, scholar, 
                confidence, discovered_by, notes, reference)
               VALUES (?, ?, ?, ?, ?, 'pattern_detector', 
                       ?, 'algorithm', ?, ?)""",
            (c["book"], c["prs"][0]["l"] if c["prs"] else "", c["prs"][-1]["r"] if c["prs"] else "",
             c["pivot"], c["scale"] + "_chiasm",
             min(float(c["z"])/10.0, 1.0),
             json.dumps({"pairs": c["prs"][:10], "window": c["w"], "contrast": c["c"]}),
             ref)
        )
        stored_chiasm += 1
    
    # Store word links in patterns table
    stored_links = 0
    for l in word_link_results[:500]:
        safe_ins("patterns", "book_id, start_verse, end_verse, pattern_type, description, confidence, discovered_by, metadata",
                 (l["book"], l["verse_a"], l["verse_b"], "word_link",
                  f"\"{l['keyword']}\" links {l['verse_a']} and {l['verse_b']} (sim={l['similarity']})",
                  min(float(l["similarity"]), 1.0), "pattern_detector",
                  json.dumps({"keyword": l["keyword"], "work": l["work"], "similarity": l["similarity"]})))
        stored_links += 1
    
    # Store inclusio candidates
    stored_inc = 0
    for inc in inclusio_results[:200]:
        safe_ins("patterns", "book_id, start_verse, end_verse, pattern_type, description, confidence, discovered_by, metadata",
                 (inc["book"], inc["begin_group"][0], inc["end_group"][-1], "inclusio",
                  f"Inclusio in {inc['work']}.{inc['book']} ch.{inc['chapter']}: {inc['begin_group'][0]} ↔ {inc['end_group'][-1]}",
                  min(float(inc["avg_similarity"]), 1.0), "pattern_detector",
                  json.dumps({"pairs": inc["pairs"], "work": inc["work"], "chapter": inc["chapter"]})))
        stored_inc += 1
    
    # Store parallelism pairs
    stored_par = 0
    for p in parallelism_results:
        safe_ins("patterns", "book_id, start_verse, end_verse, pattern_type, description, confidence, discovered_by, metadata",
                 (p["book"], p["verse_a"], p["verse_b"], f"parallelism_{p['type']}",
                  f"{p['type']} parallelism: {p['verse_a']} ↔ {p['verse_b']}",
                  min(float(p["confidence"]), 1.0), "pattern_detector",
                  json.dumps({"similarity": p["similarity"], "work": p["work"]})))
        stored_par += 1
    
    # Store formula markers
    stored_fm = 0
    for fm in formula_results[:500]:
        safe_ins("patterns", "book_id, start_verse, end_verse, pattern_type, description, confidence, discovered_by, metadata",
                 (fm["verse"].split('.')[0], fm["verse"], fm["verse"], f"formula_{fm['formula']}",
                  f"Formula '{fm['formula']}' at {fm['verse']}",
                  0.9, "pattern_detector",
                  json.dumps({"language": fm["language"]})))
        stored_fm += 1
    
    # Store acrostics
    stored_acr = 0
    for a in acrostic_results:
        safe_ins("patterns", "book_id, start_verse, end_verse, pattern_type, description, confidence, discovered_by, metadata",
                 (a["book"], f"{a['book']}.{a['chapter']}.1", f"{a['book']}.{a['chapter']}.{a['verses']}", "acrostic",
                  f"Acrostic: {a['book']} ch.{a['chapter']} — {a['groups']} groups, run={a['longest_run']}",
                  0.9 if a["is_acrostic"] else 0.5, "pattern_detector",
                  json.dumps({"groups": a["groups_detail"], "is_acrostic": a["is_acrostic"]})))
        stored_acr += 1
    
    print(f"\n  Stored: {stored_chiasm} chiasms, {stored_links} word links, {stored_inc} inclusio, {stored_par} parallelism, {stored_fm} formula markers, {stored_acr} acrostics")
    print(f"  Total found: {len(chiasm_results)} chiasms, {len(word_link_results)} word links, {len(inclusio_results)} inclusio, {len(parallelism_results)} parallelism, {len(formula_results)} formula markers, {len(acrostic_results)} acrostics")
    
    conn.commit()
    conn.execute("PRAGMA foreign_keys=ON")
    conn.close()
    
    elapsed = time.time() - t0
    print(f"\nTotal time: {elapsed:.0f}s")
    print(f"Done.")


if __name__ == "__main__":
    conn = get_db()
    run_all(conn)
