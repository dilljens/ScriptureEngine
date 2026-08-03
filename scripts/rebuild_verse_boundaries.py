#!/usr/bin/env python3
"""Re-derive verse boundaries from book-level transcription.

Problem: 92% of audio_timestamps verse spans are garbage (<1s) — the old
align_audio.py interpolated spans across the whole book MP3, producing broken
boundaries. WhisperX forced alignment failed because it was fed 0.1s audio
slices.

Fix: transcribe the book audio with faster-whisper (Hebrew, word timestamps),
then map the KNOWN verse text onto the transcript to find each verse's real
[start, end]. This is a boundary pass — word-level alignment happens after
(scripts/align_hebrew_whisperx.py) once boundaries are sane.

Matching handles ketiv/qere by normalizing to consonants (strip niqqud/cantillation,
map final forms, drop matres lectionis).

Usage:
    python3 scripts/rebuild_verse_boundaries.py --dry-run --book gen
    python3 scripts/rebuild_verse_boundaries.py --book gen --chapter 1
    python3 scripts/rebuild_verse_boundaries.py --book gen --all
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).parent.parent
RAW_AUDIO_DIR = BASE / "data" / "audio" / "raw"
NIKUD = re.compile(r"[\u0591-\u05C7]")
FINAL = str.maketrans({"ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})
MATRES = str.maketrans({"ה": "", "ו": "", "י": ""})  # for consonant-only fallback


def norm_cons(w: str, drop_matres: bool = False) -> str:
    """Normalize a Hebrew word to its consonantal skeleton for matching."""
    w = NIKUD.sub("", w or "")
    w = w.replace("/", "")
    w = w.translate(FINAL)
    if drop_matres:
        w = w.translate(MATRES)
    return w


def get_db():
    sys.path.insert(0, str(BASE))
    from lib.db import get_db
    return get_db()


def transcribe_book(audio_path: str, device: str = "cuda"):
    """Transcribe one book MP3 with faster-whisper, return word-level timeline.

    Uses faster-whisper-medium (cached, fast, plenty accurate for boundary
    detection). The ivrit large-v3-ct2 model's HF cache is incomplete on this
    machine (no model.bin — the load hangs). Medium gives word timestamps in
    ~38s per 8min of audio.
    """
    from faster_whisper import WhisperModel
    model = WhisperModel("medium", device=device, compute_type="float16")
    segments, info = model.transcribe(
        audio_path, language="he", word_timestamps=True,
        beam_size=5, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
    )
    words = []
    for seg in segments:
        if not seg.words:
            continue
        for w in seg.words:
            words.append({
                "text": w.word.strip().strip(".,;:!?"),
                "start": w.start,
                "end": w.end,
            })
    return words


def verse_to_words(verse_text: str):
    """The OSHB verse text → list of normalized word skeletons."""
    return [norm_cons(w) for w in verse_text.split() if w.strip()]


def assign_verse_boundaries(book_id: str, chapter: int, transcript: list, verses: list):
    """Match verse words onto transcript words, return {verse_id: (start, end)}.

    Dynamic-programming alignment: concatenate all verse words into one
    sequence, align it to the transcript words (allowing insertions/skips),
    then read off each verse's start (its first word's transcript time) and end
    (its last word's transcript time). This globally handles:
      - the reader's intro/prelude (transcript words before verse 1)
      - ketiv/qere and transcription differences (skipped transcript words)
      - repeated common words (את, כל) — resolved by global context

    Matching is on normalized consonant skeletons (drop_matres=True handles
    אלוהים/אלהים, השמיים/השמים, בראשית/בראשת, etc.).
    """
    # Build the verse-word sequence with verse boundaries
    vword_seq = []          # list of (verse_id, is_first, is_last)
    vword_keys = []         # normalized consonant keys, parallel to vword_seq
    for v in verses:
        vw = verse_to_words(v["text_hebrew"])
        if not vw:
            continue
        for i, w in enumerate(vw):
            vword_seq.append((v["id"], i == 0, i == len(vw) - 1))
            vword_keys.append(norm_cons(w, drop_matres=True))

    # Transcript word keys (normalized)
    tkeys = [norm_cons(w["text"], drop_matres=True) for w in transcript]

    # DP: LCS-style alignment (transcript words freely skippable)
    n, m = len(vword_seq), len(tkeys)
    if n == 0 or m == 0:
        return {}

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        vk = vword_keys[i - 1]
        for j in range(1, m + 1):
            if vk == tkeys[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    # Backtrack to find the matched verse-word → transcript-word pairs
    matched_vidx = []  # (verse_word_index_in_seq, transcript_index)
    i, j = n, m
    while i > 0 and j > 0:
        if vword_keys[i - 1] == tkeys[j - 1]:
            matched_vidx.append((i - 1, j - 1))
            i -= 1
            j -= 1
        elif dp[i - 1][j] >= dp[i][j - 1]:
            i -= 1
        else:
            j -= 1
    matched_vidx.reverse()

    # For each verse, find first and last matched transcript index
    verse_first_last = {}   # verse_id -> (first_t_idx, last_t_idx)
    for vi, tj in matched_vidx:
        vid, is_first, is_last = vword_seq[vi]
        if vid not in verse_first_last:
            verse_first_last[vid] = [tj, tj]
        else:
            verse_first_last[vid][0] = min(verse_first_last[vid][0], tj)
            verse_first_last[vid][1] = max(verse_first_last[vid][1], tj)

    result = {}
    for v in verses:
        fl = verse_first_last.get(v["id"])
        if not fl:
            result[v["id"]] = None
            continue
        fi, li = fl
        result[v["id"]] = (
            float(transcript[fi]["start"]),
            float(transcript[li]["end"]),
        )
    return result


def main():
    parser = argparse.ArgumentParser(description="Rebuild verse boundaries from transcription")
    parser.add_argument("--book", required=True, help="book id e.g. gen")
    parser.add_argument("--chapter", type=int, default=0, help="only this chapter (fast test)")
    parser.add_argument("--all", action="store_true", help="process every chapter")
    parser.add_argument("--dry-run", action="store_true", help="transcribe but don't write")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--chunk-secs", type=float, default=600.0,
                        help="transcribe the book in N-second chunks (keeps memory/GPU bounded)")
    parser.add_argument("--max-chunks", type=int, default=0,
                        help="stop after N chunks (test: 1 = first ~600s only)")
    parser.add_argument("--apply-boundaries", action="store_true",
                        help="after staging, write boundaries into audio_timestamps")
    parser.add_argument("--apply-only", action="store_true",
                        help="skip transcription; interpolate+apply existing stage table")
    args = parser.parse_args()

    conn = get_db()
    conn.row_factory = sqlite3.Row

    BOOK_AUDIO = {
        "gen": RAW_AUDIO_DIR / "01_Genesis.mp3",
        "exo": RAW_AUDIO_DIR / "02_Exodus.mp3",
    }
    if args.book not in BOOK_AUDIO:
        print(f"No raw audio wired for book '{args.book}'. Have: {list(BOOK_AUDIO)}")
        conn.close()
        return
    audio_file = BOOK_AUDIO[args.book]

    verses = conn.execute(
        "SELECT id, text_hebrew, chapter, verse FROM verses WHERE book_id=? ORDER BY chapter, verse",
        (args.book,)).fetchall()
    if args.chapter:
        verses = [v for v in verses if v["chapter"] == args.chapter]
    print(f"Book {args.book}: {len(verses)} verses to bound")

    if args.apply_only:
        conn.close()
        _apply_boundaries(args.book)
        return

    # Transcribe in chunks; each chunk is a contiguous time slice of the book.
    # We don't know chapter times yet, so transcribe the whole (bounded) span
    # in chunks and match ALL verses at the end.
    print(f"Transcribing {audio_file} in {args.chunk_secs:.0f}s chunks...")
    t0 = time.time()
    transcript = []
    chunk_start = 0.0
    from faster_whisper import WhisperModel
    model = WhisperModel("medium", device=args.device, compute_type="float16")
    tmp_wav = Path(tempfile.mkstemp(suffix=".wav")[1])
    chunk_idx = 0
    while True:
        if args.max_chunks and chunk_idx >= args.max_chunks:
            break
        sub = subprocess.run([
            "ffmpeg", "-y", "-ss", str(chunk_start), "-t", str(args.chunk_secs),
            "-i", str(audio_file), "-f", "wav", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1", str(tmp_wav),
        ], capture_output=True)
        if sub.returncode != 0 or not tmp_wav.exists() or tmp_wav.stat().st_size < 40000:
            break
        segs, _info = model.transcribe(
            str(tmp_wav), language="he", word_timestamps=True,
            beam_size=5, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        got = 0
        for seg in segs:
            for w in seg.words or []:
                transcript.append({
                    "text": w.word.strip().strip(".,;:!?"),
                    "start": chunk_start + w.start,
                    "end": chunk_start + w.end,
                })
                got += 1
        print(f"  chunk@{chunk_start:.0f}s: +{got} words ({time.time()-t0:.0f}s)")
        chunk_start += args.chunk_secs
        chunk_idx += 1
        if got == 0 and chunk_start > 300:  # stop early if a chunk is empty
            break
    print(f"  {len(transcript)} total words in {time.time()-t0:.0f}s")

    # Match verses onto the transcript
    spans = assign_verse_boundaries(args.book, 0, transcript, verses)
    matched = sum(1 for s in spans.values() if s)
    print(f"  matched {matched}/{len(spans)} verses")

    if args.dry_run:
        for vid, sp in list(spans.items())[:10]:
            print(f"  {vid}: {sp}")
        conn.close()
        return

    conn.execute("""
        CREATE TABLE IF NOT EXISTS verse_boundaries_stage (
            verse_id TEXT PRIMARY KEY, start_sec REAL, end_sec REAL)
    """)
    conn.execute("DELETE FROM verse_boundaries_stage")
    cur = conn.cursor()
    for vid, sp in spans.items():
        if sp:
            cur.execute(
                "INSERT OR REPLACE INTO verse_boundaries_stage VALUES (?,?,?)",
                (vid, round(sp[0], 2), round(sp[1], 2)))
    conn.commit()
    print(f"  staged {matched} verse boundaries (verse_boundaries_stage)")
    conn.close()

    if args.apply_boundaries:
        _apply_boundaries(args.book)


def _apply_boundaries(book: str):
    """Write verse_boundaries_stage into audio_timestamps, interpolating gaps.

    Verses the DP couldn't match get their spans evenly divided across the gap
    between the previous and next matched verse, so EVERY verse ends up with a
    usable (approximate) boundary for the downstream word aligner.
    """
    print("  applying boundaries to audio_timestamps (with interpolation)...")
    conn2 = get_db()
    conn2.execute("""
        UPDATE audio_timestamps
        SET start_sec = (SELECT start_sec FROM verse_boundaries_stage s WHERE s.verse_id = audio_timestamps.verse_id),
            end_sec   = (SELECT end_sec   FROM verse_boundaries_stage s WHERE s.verse_id = audio_timestamps.verse_id),
            created_at = datetime('now')
        WHERE verse_id IN (SELECT verse_id FROM verse_boundaries_stage)
    """)
    all_rows = conn2.execute(
        "SELECT id FROM verses WHERE book_id=? ORDER BY chapter, verse",
        (book,)).fetchall()
    seq = []
    for r in all_rows:
        s = conn2.execute(
            "SELECT start_sec, end_sec FROM verse_boundaries_stage WHERE verse_id=?",
            (r[0],)).fetchone()
        seq.append((r[0], s))
    i, n = 0, len(seq)
    while i < n:
        if seq[i][1]:
            i += 1
            continue
        j = i
        while j < n and not seq[j][1]:
            j += 1
        prev_s = seq[i - 1][1] if i > 0 else None
        next_s = seq[j][1] if j < n else None
        run_len = j - i
        if prev_s and next_s:
            gap = next_s[0] - prev_s[1]
            step = gap / (run_len + 1)
            for k in range(run_len):
                st = prev_s[1] + step * (k + 1)
                conn2.execute(
                    "INSERT OR REPLACE INTO verse_boundaries_stage VALUES (?,?,?)",
                    (seq[i + k][0], round(st, 2), round(st + max(1.0, step * 0.8), 2)))
        elif prev_s:
            st = prev_s[1]
            for k in range(run_len):
                conn2.execute(
                    "INSERT OR REPLACE INTO verse_boundaries_stage VALUES (?,?,?)",
                    (seq[i + k][0], round(st, 2), round(st + 3.0, 2)))
        i = j
    conn2.execute("""
        UPDATE audio_timestamps
        SET start_sec = (SELECT start_sec FROM verse_boundaries_stage s WHERE s.verse_id = audio_timestamps.verse_id),
            end_sec   = (SELECT end_sec   FROM verse_boundaries_stage s WHERE s.verse_id = audio_timestamps.verse_id),
            created_at = datetime('now')
        WHERE verse_id IN (SELECT verse_id FROM verse_boundaries_stage)
    """)
    conn2.commit()
    conn2.close()
    print("  ✓ audio_timestamps updated (matched + interpolated)")


if __name__ == "__main__":
    main()
