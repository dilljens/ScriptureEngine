#!/usr/bin/env python3
"""Align Hebrew verse audio with word-level timestamps using faster-whisper.

Processes all WAV files in data/audio/verses/ and stores word timestamps
as JSON sidecar files alongside the audio.

Usage:
    LD_LIBRARY_PATH=/tmp/cublas-fix:$LD_LIBRARY_PATH python3 scripts/align_hebrew_audio.py
    python3 scripts/align_hebrew_audio.py --model ivrit-ai/whisper-large-v3-ct2
    python3 scripts/align_hebrew_audio.py --verse gen.1.1  # single verse
    python3 scripts/align_hebrew_audio.py --all --gpu      # all files, GPU
"""

import argparse
import json
import os
import time
from pathlib import Path

# Ensure LD_LIBRARY_PATH is set for CUDA
_cublas_dir = "/tmp/cublas-fix"
if os.path.isdir(_cublas_dir):
    os.environ.setdefault("LD_LIBRARY_PATH", "")
    if _cublas_dir not in os.environ["LD_LIBRARY_PATH"]:
        os.environ["LD_LIBRARY_PATH"] = _cublas_dir + ":" + os.environ["LD_LIBRARY_PATH"]

AUDIO_DIR = Path(__file__).parent.parent / "data" / "audio" / "verses"
ALIGN_DIR = Path(__file__).parent.parent / "data" / "audio" / "alignments"


def align_verse(audio_path: str, model, verse_id: str) -> list[dict]:
    """Transcribe and align a single verse audio file.

    Returns list of {word, start, end, confidence} dicts.
    """
    segments, info = model.transcribe(
        audio_path,
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
                words.append({
                    "word": w.word.strip().strip(".,;:!?"),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                    "confidence": round(w.probability, 3) if w.probability else 1.0,
                })

    return words


def main():
    parser = argparse.ArgumentParser(description="Align Hebrew verse audio with word timestamps")
    parser.add_argument("--model", default="ivrit-ai/whisper-large-v3-ct2",
                        help="Whisper model (default: ivrit-ai/whisper-large-v3-ct2)")
    parser.add_argument("--verse", type=str, default="",
                        help="Single verse ID to process (e.g. gen.1.1)")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda",
                        help="Device (default: cuda if available)")
    parser.add_argument("--all", action="store_true", help="Process all audio files")
    args = parser.parse_args()

    # Find audio files
    if args.verse:
        candidates = [AUDIO_DIR / f"{args.verse}.wav"]
        if not candidates[0].exists():
            candidates = [AUDIO_DIR / f"{args.verse}_cloned.wav"]
    elif args.all:
        candidates = sorted(AUDIO_DIR.glob("*.wav"))
    else:
        # Default: process files that don't have alignments yet
        existing = set(p.stem for p in ALIGN_DIR.glob("*.json"))
        candidates = [p for p in AUDIO_DIR.glob("*.wav") if p.stem not in existing]
        if not candidates:
            print("No unaligned files found. Use --all to re-align all.")
            return

    if not candidates:
        print(f"No audio files found in {AUDIO_DIR}")
        return

    # Load model
    print(f"Loading model: {args.model} ({args.device})...")
    device = args.device
    compute = "float16" if device == "cuda" else "int8"
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(args.model, device=device, compute_type=compute)
    except Exception as e:
        print(f"Failed to load model: {e}")
        print("Falling back to CPU...")
        model = WhisperModel(args.model, device="cpu", compute_type="int8")

    print(f"Model loaded. Processing {len(candidates)} file(s)...")

    ALIGN_DIR.mkdir(parents=True, exist_ok=True)

    count = 0
    errors = 0
    total_start = time.time()

    for i, audio_path in enumerate(candidates):
        verse_id = audio_path.stem
        out_path = ALIGN_DIR / f"{verse_id}.json"

        # Skip if already aligned (unless --verse forces redo)
        if out_path.exists() and not args.verse:
            continue

        print(f"  [{i+1}/{len(candidates)}] {verse_id}...", end="", flush=True)
        t0 = time.time()

        try:
            words = align_verse(str(audio_path), model, verse_id)
            if words:
                data = {
                    "ref": verse_id,
                    "duration": round(words[-1]["end"] - words[0]["start"], 3) if len(words) > 1 else 0,
                    "word_count": len(words),
                    "words": words,
                }
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                count += 1
                elapsed = time.time() - t0
                print(f" {len(words)} words in {elapsed:.1f}s")
            else:
                print(" no words detected")
                errors += 1
        except Exception as e:
            print(f" ERROR: {e}")
            errors += 1

    total_time = time.time() - total_start
    print(f"\nDone: {count} aligned, {errors} errors in {total_time:.1f}s")


if __name__ == "__main__":
    main()
