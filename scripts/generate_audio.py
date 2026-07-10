#!/usr/bin/env python3
"""Batch Hebrew audio generation using OmniVoice TTS.

Generates verse-by-verse audio files for the Tanakh.

Usage:
  python3 scripts/generate_audio.py                    # all verses
  python3 scripts/generate_audio.py --book gen         # just Genesis
  python3 scripts/generate_audio.py --book gen --chapter 1  # just Gen 1
  python3 scripts/generate_audio.py --reclone          # re-generate with voice cloning
"""

import sys, os, json, argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db
from omnivoice import OmniVoice
import torch, soundfile as sf


def get_verses(book_id=None, chapter=None):
    """Get verses with Hebrew text, optionally filtered."""
    conn = get_db()
    query = "SELECT id, text_hebrew, book_id, chapter, verse FROM verses WHERE text_hebrew IS NOT NULL AND text_hebrew != ''"
    params = []
    if book_id:
        query += " AND book_id = ?"
        params.append(book_id)
    if chapter is not None:
        query += " AND chapter = ?"
        params.append(int(chapter))
    query += " ORDER BY book_id, chapter, verse"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def main():
    parser = argparse.ArgumentParser(description="Generate Hebrew audio for Bible verses")
    parser.add_argument("--book", type=str, default="", help="Book ID (gen, exo, isa, etc.)")
    parser.add_argument("--chapter", type=int, default=None, help="Chapter number")
    parser.add_argument("--speed", type=float, default=1.25, help="Speaking speed (1.0=default, 1.25=natural)")
    parser.add_argument("--reclone", action="store_true", help="Regenerate with voice cloning")
    parser.add_argument("--reference", type=str, default="data/audio/clone/schmueloff_8s.wav",
                        help="Reference audio for voice cloning")
    args = parser.parse_args()

    verses = get_verses(args.book, args.chapter)
    if not verses:
        print(f"No verses found with Hebrew text")
        return

    print(f"Loading OmniVoice...")
    model = OmniVoice.from_pretrained(
        "k2-fsa/OmniVoice",
        device_map="cuda:0",
        dtype=torch.float16
    )
    print(f"Model loaded. Generating {len(verses)} verses...")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "audio", "verses")
    os.makedirs(out_dir, exist_ok=True)

    count = 0
    for r in verses:
        vid = r["id"]
        heb = r["text_hebrew"]
        if not heb:
            continue

        suffix = "_cloned" if args.reclone else ""
        outpath = os.path.join(out_dir, f"{vid}{suffix}.wav")
        if os.path.exists(outpath):
            continue

    try:
        if args.reclone:
            audio = model.generate(text=heb, ref_audio=args.reference, speed=args.speed)
        else:
            audio = model.generate(text=heb, speed=args.speed)
            sf.write(outpath, audio[0], 24000)
            count += 1
            if count % 10 == 0:
                print(f"  {count}/{len(verses)}...", flush=True)
        except Exception as e:
            print(f"  FAILED {vid}: {e}")

    print(f"\nDone! Generated {count} audio files in {out_dir}")


if __name__ == "__main__":
    main()
