#!/usr/bin/env python3
"""Generate Hebrew letter audio using OmniVoice TTS with voice cloning.

Uses the same OmniVoice pipeline as generate_audio.py to produce
letter-by-letter pronunciation audio files for the Hebrew aleph-bet.

Output: data/audio/letters/{node_id}.wav

Usage:
  python3 scripts/generate_letter_audio.py                  # all letters
  python3 scripts/generate_letter_audio.py --reclone         # voice-cloned from Shmuelof
  python3 scripts/generate_letter_audio.py --letter aleph    # single letter
"""

import argparse
import os
import sys
import sqlite3
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import soundfile as sf
import torch
from omnivoice import OmniVoice

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"

# Letters to generate — (node_id, hebrew_char, name, pronunciation_text)
# pronunciation_text is what the model will speak
LETTERS = [
    # Consonants
    ("aleph", "א", "Aleph", "א Aleph"),
    ("bet", "בּ", "Bet", "ב Bet"),
    ("gimel", "ג", "Gimel", "ג Gimel"),
    ("dalet", "ד", "Dalet", "ד Dalet"),
    ("he", "ה", "He", "ה He"),
    ("vav", "ו", "Vav", "ו Vav"),
    ("zayin", "ז", "Zayin", "ז Zayin"),
    ("chet", "ח", "Chet", "ח Chet"),
    ("tet", "ט", "Tet", "ט Tet"),
    ("yod", "י", "Yod", "י Yod"),
    ("kaf", "כ", "Kaf", "כ Kaf"),
    ("kaf_final", "ך", "Kaf final", "ך Kaf final"),
    ("lamed", "ל", "Lamed", "ל Lamed"),
    ("mem", "מ", "Mem", "מ Mem"),
    ("mem_final", "ם", "Mem final", "ם Mem final"),
    ("nun", "נ", "Nun", "נ Nun"),
    ("nun_final", "ן", "Nun final", "ן Nun final"),
    ("samekh", "ס", "Samekh", "ס Samekh"),
    ("ayin", "ע", "Ayin", "ע Ayin"),
    ("pe", "פ", "Pe", "פ Pe"),
    ("pe_final", "ף", "Pe final", "ף Pe final"),
    ("tsade", "צ", "Tsade", "צ Tsade"),
    ("tsade_final", "ץ", "Tsade final", "ץ Tsade final"),
    ("qof", "ק", "Qof", "ק Qof"),
    ("resh", "ר", "Resh", "ר Resh"),
    ("shin", "שׁ", "Shin", "שׁ Shin"),
    ("sin", "שׂ", "Sin", "שׂ Sin"),
    ("tav", "ת", "Tav", "ת Tav"),
    # Vowels
    ("vowel_patah", "ַ", "Patah", "ַ Patah"),
    ("vowel_qamats", "ָ", "Qamats", "ָ Qamats"),
    ("vowel_hiriq", "ִ", "Hiriq", "ִ Hiriq"),
    ("vowel_tsere", "ֵ", "Tsere", "ֵ Tsere"),
    ("vowel_segol", "ֶ", "Segol", "ֶ Segol"),
    ("vowel_holam", "ֹ", "Holam", "ֹ Holam"),
    ("vowel_qubuts", "ֻ", "Qubuts", "ֻ Qubuts"),
    ("vowel_sheva", "ְ", "Sheva", "ְ Sheva"),
    ("vowel_hataf_patah", "ֲ", "Hataf Patah", "ֲ Hataf Patah"),
    ("vowel_hataf_qamats", "ֳ", "Hataf Qamats", "ֳ Hataf Qamats"),
    ("vowel_hataf_segol", "ֱ", "Hataf Segol", "ֱ Hataf Segol"),
    ("vowel_hiriq_yod", "ִי", "Hiriq Yod", "ִי Hiriq Yod"),
    ("vowel_tsere_yod", "ֵי", "Tsere Yod", "ֵי Tsere Yod"),
    ("vowel_segol_yod", "ֶי", "Segol Yod", "ֶי Segol Yod"),
    ("vowel_holam_vav", "וֹ", "Holam Male", "וֹ Holam Male"),
    ("vowel_shuruq", "וּ", "Shuruq", "וּ Shuruq"),
    ("vowel_qamats_qatan", "ָ", "Qamats Qatan", "ָ Qamats Qatan"),
    ("vowel_sheva_na", "ְ", "Sheva Na", "ְ Sheva Na"),
    ("vowel_sheva_nah", "ְ", "Sheva Nah", "ְ Sheva Nah"),
]


def main():
    parser = argparse.ArgumentParser(description="Generate Hebrew letter audio")
    parser.add_argument("--reclone", action="store_true",
                        help="Use voice cloning with Shmuelof reference")
    parser.add_argument("--reference", type=str,
                        default="data/audio/clone/shmuelof_8s.wav",
                        help="Reference audio for voice cloning")
    parser.add_argument("--letter", type=str, default="",
                        help="Single letter node_id to generate (e.g. 'aleph')")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Speaking speed")
    args = parser.parse_args()

    out_dir = Path(__file__).parent.parent / "data" / "audio" / "letters"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Filter to one letter if specified
    letters = [l for l in LETTERS if not args.letter or l[0] == args.letter]
    if not letters:
        print(f"No letters matched filter: {args.letter}")
        sys.exit(1)

    # Check already generated
    to_generate = []
    for node_id, heb, name, text in letters:
        outpath = out_dir / f"{node_id}.wav"
        if not outpath.exists():
            to_generate.append((node_id, heb, name, text))
            print(f"  PENDING: {node_id:20s} ({heb} {name})")
        else:
            print(f"  EXISTS:  {node_id:20s} ({heb} {name})")

    if not to_generate:
        print("\nAll letter audio files already exist!")
        return

    print(f"\nLoading OmniVoice (this may take a minute on first run)...")
    try:
        model = OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map="cuda:0" if torch.cuda.is_available() else "cpu",
            dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
    except Exception as e:
        print(f"Failed to load OmniVoice: {e}")
        print("Install with: pip install omnivoice torch soundfile")
        sys.exit(1)

    print(f"Generating {len(to_generate)} letter audio files...")

    ref_path = args.reference
    if args.reclone and not os.path.exists(ref_path):
        print(f"Reference audio not found: {ref_path}")
        print("Falling back to standard TTS (no voice cloning)")
        args.reclone = False

    count = 0
    for node_id, heb, name, text in to_generate:
        outpath = out_dir / f"{node_id}.wav"
        try:
            if args.reclone:
                audio = model.generate(text=text, ref_audio=ref_path, speed=args.speed)
            else:
                audio = model.generate(text=text, speed=args.speed)
            sf.write(str(outpath), audio[0], 24000)
            count += 1
            if count % 5 == 0:
                print(f"  {count}/{len(to_generate)}...", flush=True)
        except Exception as e:
            print(f"  FAILED {node_id} ({heb} {name}): {e}")

    print(f"\nDone! Generated {count} letter audio files in {out_dir}")
    print(f"Run: ls {out_dir}/*.wav | wc -l")


if __name__ == "__main__":
    main()
