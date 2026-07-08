#!/usr/bin/env python3
"""Hybrid Hebrew alignment: ivrit-ai ASR + MMS CTC forced alignment.

Combines two alignment methods positionally (both align to the same audio):
- ivrit-ai (faster-whisper): good Hebrew recognition, captures Sephardi pronunciation
- MMS forced aligner: CTC-based word boundaries, physically precise

Strategy: Match words by sequential position (not by spelling, since Sephardi
pronunciation differs from standard Bible text). For each MMS word position,
take the ivrit-ai word identity + MMS boundary.

Usage:
    LD_LIBRARY_PATH=/tmp/cublas-fix:$LD_LIBRARY_PATH .venv/bin/python3 scripts/align_hebrew_hybrid.py --chapter gen_1
    .venv/bin/python3 scripts/align_hebrew_hybrid.py --chapter gen_1 --compare
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent.parent
AUDIO_DIR = BASE / "data" / "audio" / "raw" / "genesis_chapters"
ALIGN_OUT = BASE / "data" / "audio" / "alignments"
DB_PATH = BASE / "data" / "processed" / "scripture.db"
SYSTEM_PYTHON = "/usr/bin/python3"
VENV_PYTHON = str(BASE / ".venv" / "bin" / "python3")


def strip_norm(w):
    w = w.strip()
    w = w.replace("/", "")
    w = re.sub(r"[\u0591-\u05AF\u05BD\u05BF\u05C0\u05C3\u05C6]", "", w)
    w = w.strip(".,;:!?()[]\"' ")
    w = w.replace("ך", "כ").replace("ם", "מ").replace("ן", "נ").replace("ף", "פ").replace("ץ", "צ")
    w = re.sub(r"[^א-ת]", "", w)
    return w


def consonants(w):
    return "".join(c for c in w if c in "אבגדהוזחטיכלמנסעפצקרשת")


def word_similarity(a, b):
    """Score 0-1 how similar two normalized Hebrew words are.
    
    Uses set overlap (Jaccard-like) to handle prefix differences:
    e.g., 'בראשית' vs 'ראשית' should score high (same root).
    Also checks if one is a substring of the other.
    """
    if not a or not b:
        return 0
    if a == b:
        return 1.0
    
    ca = consonants(a)
    cb = consonants(b)
    
    if not ca or not cb:
        return 0
    
    # Substring check: one word is contained in the other
    if ca in cb or cb in ca:
        return 0.9
    
    # Set overlap (Jaccard)
    set_a = set(ca)
    set_b = set(cb)
    if not set_a or not set_b:
        return 0
    
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    jaccard = intersection / union if union > 0 else 0
    
    # Also check sequential overlap for longer matches
    # Count matching consecutive pairs
    max_len = max(len(ca), len(cb))
    if max_len == 0:
        return 0
    
    # Sliding window: count positions where chars match
    # by trying different offsets
    best_seq = 0
    shorter, longer = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
    for offset in range(len(longer) - len(shorter) + 1):
        matches = sum(1 for i in range(len(shorter)) if shorter[i] == longer[offset + i])
        best_seq = max(best_seq, matches)
    
    seq_score = best_seq / max_len
    
    # Combine: prefer jaccard, but boost with sequential match
    return max(jaccard, seq_score * 0.9)


# ── Step runners ──

def load_ivrit_alignment(wav_path, output_json, use_cache=True):
    if use_cache and os.path.exists(output_json):
        print(f"  Using cached: {output_json}")
        with open(output_json) as f:
            return json.load(f)["words"]

    print(f"  Running faster-whisper (CUDA)...")
    env = os.environ.copy()
    cublas_dir = "/tmp/cublas-fix"
    if os.path.isdir(cublas_dir):
        env["LD_LIBRARY_PATH"] = f"{cublas_dir}:" + env.get("LD_LIBRARY_PATH", "")

    code = f"""
import sys, json
sys.path.insert(0, '{BASE}')
from faster_whisper import WhisperModel
model = WhisperModel("ivrit-ai/whisper-large-v3-ct2", device="cuda", compute_type="float16")
segments, info = model.transcribe(
    "{wav_path}",
    language="he",
    word_timestamps=True,
    beam_size=5,
    vad_filter=True,
    vad_parameters=dict(min_silence_duration_ms=500),
)
words = []
for seg in segments:
    if seg.words:
        for w in seg.words:
            words.append({{
                "word": w.word.strip().strip(".,;:!?"),
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "confidence": round(w.probability, 3) if w.probability else 1.0,
            }})
with open("{output_json}", "w", encoding="utf-8") as f:
    json.dump({{"words": words, "total": len(words)}}, f, ensure_ascii=False, indent=2)
print(f"Done: {{len(words)}} words")
"""
    result = subprocess.run([SYSTEM_PYTHON, "-c", code], capture_output=True, text=True, env=env, timeout=600)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:300]}")
        return []
    print(f"  {result.stdout.strip()}")
    with open(output_json) as f:
        return json.load(f)["words"]


def load_mms_alignment(wav_path, bible_text):
    text_path = os.path.splitext(wav_path)[0] + "_mms_text.txt"
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(bible_text)

    print(f"  Running MMS ({len(bible_text.split())} words)...")
    cmd = [
        VENV_PYTHON, "-m", "ctc_forced_aligner.align",
        "--audio_path", wav_path,
        "--text_path", text_path,
        "--language", "heb",
        "--romanize",
        "--star_frequency", "edges",
        "--merge_threshold", "0.02",
        "--compute_dtype", "float16",
        "--window_size", "60",
        "--context_size", "5",
    ]
    env = os.environ.copy()
    cublas_dir = "/tmp/cublas-fix"
    if os.path.isdir(cublas_dir):
        env["LD_LIBRARY_PATH"] = f"{cublas_dir}:" + env.get("LD_LIBRARY_PATH", "")

    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd="/tmp")
    if result.returncode != 0:
        print(f"  MMS error: {result.stderr[:200]}")
        return []

    mms_json = os.path.splitext(wav_path)[0] + ".json"
    if not os.path.exists(mms_json):
        print(f"  output not found: {mms_json}")
        return []

    with open(mms_json) as f:
        data = json.load(f)
    return data.get("segments", [])


# ── Timing correction (positional) ──

def fit_timing(iv_words, mms_words):
    """Fit MMS_time = slope * ivrit_time + intercept by positional matching.
    
    Both alignments are for the same audio in the same word order.
    Just pair word[i] of ivrit_body with word[i] of mms.
    """
    iv_body = [w for w in iv_words if w["start"] >= 10]
    if not iv_body or not mms_words:
        return 1.0, 0.0

    n = min(len(iv_body), len(mms_words))
    if n < 10:
        return 1.0, 0.0

    iv_t = [iv_body[i]["start"] for i in range(n)]
    ms_t = [mms_words[i]["start"] for i in range(n)]

    sum_x = sum(iv_t)
    sum_y = sum(ms_t)
    sum_xx = sum(x * x for x in iv_t)
    sum_xy = sum(x * y for x, y in zip(iv_t, ms_t))

    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-10:
        return 1.0, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    if slope < 0.1 or slope > 3.0:
        print(f"  WARNING bad slope={slope:.4f}, using mean offset")
        return 1.0, (sum_y - sum_x) / n

    return slope, intercept


def combine(iv_words, mms_words):
    """Combine ivrit-ai identities with MMS boundaries (positional match)."""
    iv_body = [w for w in iv_words if w["start"] >= 10]
    result = []

    for i, mw in enumerate(mms_words):
        if i < len(iv_body):
            iw = iv_body[i]
            result.append({
                "word": iw["word"],
                "start": round(mw["start"], 3),
                "end": round(mw["end"], 3),
                "confidence": round(iw["confidence"], 3),
                "source": "hybrid",
            })
        else:
            result.append({
                "word": mw.get("text", ""),
                "start": round(mw["start"], 3),
                "end": round(mw["end"], 3),
                "confidence": 0.5,
                "source": "mms",
            })

    for j in range(len(mms_words), len(iv_body)):
        iw = iv_body[j]
        result.append({
            "word": iw["word"],
            "start": round(iw["start"], 3),
            "end": round(iw["end"], 3),
            "confidence": round(iw["confidence"], 3),
            "source": "ivrit-only",
        })

    result.sort(key=lambda x: x["start"])
    return result


# ── Comparison ──

def gap_analysis(words):
    return [words[i+1]["start"] - words[i]["end"] for i in range(len(words)-1)]


def compare_alignment(iv_words, mms_words, hybrid_words, chapter):
    print(f"\n{'='*60}")
    print(f"QUALITY COMPARISON: {chapter}")
    print(f"{'='*60}")

    iv_body = [w for w in iv_words if w["start"] >= 10]

    # Stats table
    print(f"\n{'Metric':<30} {'Ivrit-ai':<15} {'MMS':<15} {'Hybrid':<15}")
    print("-" * 75)
    print(f"{'Word count':<30} {len(iv_body):<15} {len(mms_words):<15} {len(hybrid_words):<15}")

    for label, words in [("Ivrit-ai", iv_body), ("MMS", mms_words), ("Hybrid", hybrid_words)]:
        if not words:
            continue
        dur = words[-1]["end"] - words[0]["start"]
        avg_w = sum(w["end"] - w["start"] for w in words) / len(words)
        gaps = gap_analysis(words)
        avg_gap = sum(gaps)/len(gaps) if gaps else 0
        neg = sum(1 for g in gaps if g < 0)
        big = sum(1 for g in gaps if g > 0.05)
        tight = sum(1 for g in gaps if 0 <= g <= 0.05)
        print(f"\n{label}:")
        print(f"  Duration: {dur:.2f}s")
        print(f"  Avg word: {avg_w:.4f}s")
        print(f"  Avg gap: {avg_gap:.4f}s  overlaps={neg}  >50ms={big}  tight={tight}")

    # Boundary comparison on matched positions
    n = min(len(iv_body), len(mms_words))
    if n > 0:
        start_diff = [abs(iv_body[i]["start"] - mms_words[i]["start"]) for i in range(n)]
        end_diff = [abs(iv_body[i]["end"] - mms_words[i]["end"]) for i in range(n)]
        print(f"\nBoundary comparison ({n} matched positions):")
        print(f"  Mean start diff: {sum(start_diff)/n:.4f}s (max: {max(start_diff):.4f}s)")
        print(f"  Mean end diff: {sum(end_diff)/n:.4f}s (max: {max(end_diff):.4f}s)")

    # Detailed per-word timing for gen.1.1 (for manual inspection)
    print(f"\n--- gen.1.1 detailed boundary comparison ---")
    print(f"{'#':<4} {'Word':<10} {'Ivrit_start':<12} {'Ivrit_end':<12} {'MMS_start':<12} {'MMS_end':<12} {'Diff_start':<10} {'Diff_end':<10}")
    print("-" * 85)
    for i in range(min(7, n)):
        iw = iv_body[i]
        mw = mms_words[i]
        iv_s = iw["start"]
        iv_e = iw["end"]
        ms_s = mw["start"]
        ms_e = mw["end"]
        ds = abs(iv_s - ms_s)
        de = abs(iv_e - ms_e)
        print(f'{i:<4} {iw["word"]:<10} {iv_s:<12.3f} {iv_e:<12.3f} {ms_s:<12.3f} {ms_e:<12.3f} {ds:<10.3f} {de:<.3f}')


def match_to_verses(words, book, chapter):
    conn = sqlite3.connect(str(DB_PATH))
    verses = conn.execute(
        "SELECT id, verse, text_hebrew FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
        (book, chapter)
    ).fetchall()
    conn.close()

    ref = []
    for vid, vn, txt in verses:
        for w in txt.split():
            # Remove / separators to get full word
            full_word = w.replace("/", "")
            nw = strip_norm(full_word)
            if nw:
                ref.append({"vid": vid, "vnum": vn, "word": nw})

    result = defaultdict(list)
    ref_i = 0
    unmatched = 0

    for cw in words:
        cw_norm = strip_norm(cw["word"])
        if not cw_norm:
            unmatched += 1
            continue
        # Match by position
        if ref_i < len(ref) and word_similarity(cw_norm, ref[ref_i]["word"]) >= 0.5:
            result[ref[ref_i]["vid"]].append(cw)
            ref_i += 1
        else:
            # Try next few ref words
            found = False
            for ri in range(ref_i, min(ref_i + 3, len(ref))):
                if word_similarity(cw_norm, ref[ri]["word"]) >= 0.5:
                    result[ref[ri]["vid"]].append(cw)
                    ref_i = ri + 1
                    found = True
                    break
            if not found:
                unmatched += 1

    return dict(result), unmatched


def save_verse_files(words, book, chapter, suffix):
    vm, unmatched = match_to_verses(words, book, chapter)
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT id FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
        (book, chapter)
    ).fetchall()
    conn.close()

    ALIGN_OUT.mkdir(parents=True, exist_ok=True)
    saved = 0
    for (vid,) in rows:
        wds = vm.get(vid, [])
        if not wds:
            continue
        wds.sort(key=lambda x: x["start"])
        data = {
            "ref": vid,
            "duration": round(wds[-1]["end"] - wds[0]["start"], 3),
            "word_count": len(wds),
            "words": wds,
        }
        with open(ALIGN_OUT / f"{vid}_{suffix}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        saved += 1
    print(f"  Saved {saved} verse files ({suffix}), {unmatched} unmatched")
    return vm


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Hybrid Hebrew alignment")
    parser.add_argument("--chapter", default="gen_1")
    parser.add_argument("--skip-asr", action="store_true")
    parser.add_argument("--skip-mms", action="store_true")
    parser.add_argument("--compare", action="store_true")
    args = parser.parse_args()

    ch = args.chapter
    book, chs = ch.split("_")
    cn = int(chs)
    wav_path = str(AUDIO_DIR / f"{ch}.wav")

    if not os.path.exists(wav_path):
        print(f"Not found: {wav_path}")
        return

    print(f"{'='*60}")
    print(f"HYBRID: {ch}")
    print(f"{'='*60}")

    # 1. Ivrit-ai
    iv_cache = f"/tmp/{ch}_ivrit_vad.json"
    mms_cache = f"/tmp/{ch}_mms.json"

    if args.skip_asr and os.path.exists(iv_cache):
        print("\n[1/4] Loading cached ivrit-ai...")
        with open(iv_cache) as f:
            iv_words = json.load(f)["words"]
    else:
        print("\n[1/4] Running ivrit-ai...")
        t0 = time.time()
        iv_words = load_ivrit_alignment(wav_path, iv_cache, use_cache=args.skip_asr)
        print(f"  {len(iv_words)} words in {time.time()-t0:.1f}s")

    if not iv_words:
        return

    # 2. MMS
    if args.skip_mms and os.path.exists(mms_cache):
        print("\n[2/4] Loading cached MMS...")
        with open(mms_cache) as f:
            mms_words = json.load(f)
    else:
        print("\n[2/4] Running MMS...")
        conn = sqlite3.connect(str(DB_PATH))
        verses = conn.execute(
            "SELECT text_hebrew FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
            (book, cn)
        ).fetchall()
        conn.close()
        bible_text = " ".join([v[0].replace("/", "") for v in verses])

        t0 = time.time()
        mms_words = load_mms_alignment(wav_path, bible_text)
        print(f"  {len(mms_words)} words in {time.time()-t0:.1f}s")
        if mms_words:
            with open(mms_cache, "w") as f:
                json.dump(mms_words, f, ensure_ascii=False, indent=2)

    if not mms_words:
        print("  MMS failed, using ivrit-ai only")
        hybrid = [{"word": w["word"], "start": w["start"], "end": w["end"],
                    "confidence": w["confidence"], "source": "ivrit-ai"} for w in iv_words]
    else:
        # 3. Timing correction
        print("\n[3/4] Fitting timing correction...")
        slope, intercept = fit_timing(iv_words, mms_words)
        if slope != 1.0 or intercept != 0.0:
            print(f"  MMS = {slope:.4f} × ivrit + ({intercept:.4f})")
        else:
            print(f"  Identity")

        # 4. Combine
        print("\n[4/4] Combining...")
        hybrid = combine(iv_words, mms_words)
        sources = defaultdict(int)
        for w in hybrid:
            sources[w.get("source", "?")] += 1
        for s, n in sources.items():
            print(f"  {s}: {n}")

    # Save
    out = ALIGN_OUT / f"{ch}_hybrid.json"
    ALIGN_OUT.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(hybrid, f, ensure_ascii=False, indent=2)
    print(f"\n  Saved: {out}")

    # Verse files
    print(f"\n  Saving verse alignments...")
    save_verse_files(hybrid, book, cn, "hybrid")

    # Comparison report
    if args.compare and mms_words:
        iv_body = [w for w in iv_words if w["start"] >= 10]
        compare_alignment(iv_body, mms_words, hybrid, ch)

    print(f"\n{'='*60}")
    print(f"DONE: {ch} — {len(hybrid)} words")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
