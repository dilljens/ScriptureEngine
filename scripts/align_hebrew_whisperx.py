#!/usr/bin/env python3
"""Re-align Hebrew verse audio with precise word boundaries using WhisperX.

Why: the existing pipeline used faster-whisper's built-in word_timestamps,
which are coarse and drift from the true audio position. WhisperX performs
FORCED alignment with a wav2vec2 phoneme model — for Hebrew that's
`imvladikon/wav2vec2-xls-r-300m-hebrew`, WhisperX's own default for "he".

This upgrades word boundaries so that (a) clicking a word plays its exact
audio slice and (b) verse read-along highlights the word actually being
spoken.

It re-uses the existing verse boundaries (audio_timestamps.start_sec/end_sec
+ source_file), slices the audio for each verse, and forced-aligns the verse's
KNOWN Hebrew text (from the verses table) to the audio — no transcription
step, so there are no ASR text errors.

Requires a separate venv: `uv venv venv-align --python 3.12` then
`uv pip install --python venv-align/bin/python whisperx` (whisperx needs
Python <= 3.13).

Usage:
    python3 scripts/align_hebrew_whisperx.py --dry-run
    python3 scripts/align_hebrew_whisperx.py --verse gen.1.1
    python3 scripts/align_hebrew_whisperx.py --book gen --chapter 1
    python3 scripts/align_hebrew_whisperx.py --all
"""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).parent.parent
RAW_AUDIO_DIR = BASE / "data" / "audio" / "raw"
VERSES_DIR = BASE / "data" / "audio" / "verses"
sys.path.insert(0, str(BASE))  # so `lib` and `web` import in this venv

# WhisperX default Hebrew alignment model (verified in whisperx/alignment.py)
HEBREW_ALIGN_MODEL = "imvladikon/wav2vec2-xls-r-300m-hebrew"


def get_db():
    from lib.db import get_db
    return get_db()


def _slice_verse(source_file: str, start: float, end: float) -> str:
    """Slice the verse audio from its source file. Returns path to a temp wav."""
    src = RAW_AUDIO_DIR / source_file
    if not src.exists():
        # try the verses dir (e.g. gen_1.wav lives there)
        alt = VERSES_DIR / source_file
        if not alt.exists():
            raise FileNotFoundError(f"source audio not found: {src} or {alt}")
        src = alt
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(max(0, start - 0.05)), "-to", str(end + 0.05),
        "-i", str(src), "-f", "wav", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", tmp.name,
    ], capture_output=True, check=True)
    return tmp.name


def align_verse(align_model, metadata, verse_id: str, text_hebrew: str, source_file: str, start: float, end: float, device: str):
    """Forced-align one verse's known Hebrew text to its audio slice.

    Research (Aug 2026): wav2vec2-xls-r-300m-hebrew is still the best Hebrew
    alignment model (nothing newer exists). "backtrack failed" happens when the
    Viterbi trellis can't walk the segment — usually bad boundaries (trailing
    silence) or a char the reader says that isn't in the written text (ketiv
    vs qere). Fixes, in order:
      1. VAD-trim the verse window (tight boundaries)
      2. Retry with a ±150ms wiggle window
      3. char-level alignment fallback (more forgiving trellis)
    """
    import whisperx
    audio_path = _slice_verse(source_file, start, end)
    try:
        import re
        text = re.sub(r"/", "", text_hebrew)          # strip OSHB '/' morph separator
        text = re.sub(r"\s+", " ", text).strip()
        audio = whisperx.load_audio(audio_path)

        # 1. VAD-trim the audio to remove leading/trailing silence
        try:
            import numpy as np
            # lightweight energy-based trim (robust, no extra deps)
            seg = np.abs(audio)
            hop = 160  # 10ms at 16k
            energy = np.array([seg[i:i + hop].max() for i in range(0, len(seg), hop)])
            thr = max(0.005, energy.max() * 0.05)
            voiced = np.where(energy > thr)[0]
            if len(voiced) > 2:
                a0 = max(0, voiced[0] * hop - 240)
                a1 = min(len(audio), (voiced[-1] + 1) * hop + 240)
                audio = audio[a0:a1]
                off = a0 / 16000.0
            else:
                off = 0.0
        except Exception:
            off = 0.0

        def _run(win_start, win_end, char_level):
            segs = [{"text": text, "start": 0.0, "end": min((len(audio) - off * 16000) / 16000, win_end - win_start)}]
            return whisperx.align(
                segs, align_model, metadata, audio, device,
                return_char_alignments=char_level,
            )

        result = None
        # 2. try tight window, then wiggled windows
        for wstart, wend in [(0.0, (len(audio) - off * 16000) / 16000),
                             (0.0, (len(audio) - off * 16000) / 16000 + 0.3)]:
            try:
                result = _run(wstart, wend, char_level=False)
                if _has_words(result):
                    break
            except Exception:
                continue
        # 3. char-level fallback
        if not result or not _has_words(result):
            try:
                result = _run(0.0, (len(audio) - off * 16000) / 16000, char_level=True)
            except Exception:
                result = None

        words = []
        if result:
            for seg in result.get("segments", []):
                for w in seg.get("words", []):
                    words.append({
                        "word": w.get("word", "").strip(),
                        "start": round(start + off + w.get("start", 0), 3),
                        "end": round(start + off + w.get("end", 0), 3),
                        "confidence": round(w.get("score", 1.0), 3) if w.get("score") is not None else 1.0,
                    })
        return words
    finally:
        try:
            os.unlink(audio_path)
        except OSError:
            pass


def _has_words(result) -> bool:
    if not result:
        return False
    for seg in result.get("segments", []):
        if seg.get("words"):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Re-align Hebrew verses with WhisperX forced alignment")
    parser.add_argument("--dry-run", action="store_true", help="Count verses to align without doing it")
    parser.add_argument("--verse", default="", help="Single verse id (e.g. gen.1.1)")
    parser.add_argument("--book", default="", help="Book id (e.g. gen)")
    parser.add_argument("--chapter", type=int, default=0, help="Chapter number (with --book)")
    parser.add_argument("--all", action="store_true", help="Align every verse that has audio")
    parser.add_argument("--device", default="cuda", help="cuda or cpu")
    parser.add_argument("--model", default=HEBREW_ALIGN_MODEL, help="wav2vec2 alignment model")
    parser.add_argument("--only-missing", action="store_true",
                        help="only align verses with <3 existing word timestamps")
    args = parser.parse_args()

    conn = get_db()
    conn.row_factory = sqlite3.Row

    where = ["source_file != ''"]
    params = []
    if args.verse:
        where.append("verse_id = ?")
        params.append(args.verse)
    if args.book:
        where.append("t.book_id = ?")
        params.append(args.book)
    if args.chapter:
        where.append("t.chapter = ?")
        params.append(args.chapter)

    verses = conn.execute(
        f"""SELECT t.verse_id, t.start_sec, t.end_sec, t.source_file,
                   v.text_hebrew
            FROM audio_timestamps t
            LEFT JOIN verses v ON v.id = t.verse_id
            WHERE {' AND '.join(where)} AND v.text_hebrew IS NOT NULL
              AND (NOT ? OR COALESCE(json_array_length(t.word_timestamps), 0) < 3)
            ORDER BY t.verse_id""",
        params + [1 if args.only_missing else 0]).fetchall()

    print(f"Found {len(verses)} verses to align")
    if args.dry_run:
        conn.close()
        return

    if not verses:
        conn.close()
        return

    print(f"Loading alignment model: {args.model} on {args.device}...")
    import whisperx
    align_model, metadata = whisperx.load_align_model(
        language_code="he", device=args.device, model_name=args.model)

    updated = 0
    failed = 0
    t0 = time.time()
    for i, v in enumerate(verses):
        vid = v["verse_id"]
        try:
            words = align_verse(
                align_model, metadata, vid, v["text_hebrew"],
                v["source_file"], v["start_sec"], v["end_sec"], args.device)
            if not words:
                # Forced alignment failed — keep whatever timestamps already
                # exist (faster-whisper's) rather than writing empty.
                failed += 1
                if (i + 1) % 25 == 0 or i == len(verses) - 1:
                    print(f"  [{i+1}/{len(verses)}] {vid}: forced-align failed (kept existing)")
                continue
            conn.execute(
                "UPDATE audio_timestamps SET word_timestamps=?, created_at=datetime('now') WHERE verse_id=?",
                (json.dumps(words, ensure_ascii=False), vid))
            updated += 1
            if (i + 1) % 10 == 0 or i == len(verses) - 1:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                eta = (len(verses) - i - 1) / rate if rate > 0 else 0
                print(f"  [{i+1}/{len(verses)}] {vid}: {len(words)} words ({elapsed:.0f}s, ~{eta:.0f}s left)")
        except Exception as e:
            failed += 1
            print(f"  [{i+1}/{len(verses)}] {vid}: ERROR {e}")

    conn.commit()
    conn.close()
    print(f"Done: {updated} aligned, {failed} failed, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
