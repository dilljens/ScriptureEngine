#!/usr/bin/env python3
"""Generate Hebrew word audio: phonikud G2P → Kokoro-hebrew (ONNX).

Math Academy Way + audio review decision: word-level audio is TTS. Pipeline:

  1. phonikud (Hebrew G2P → IPA, MIT) converts POINTED text to correct IPA.
     Essential: espeak-ng (Kokoro's default phonemizer) DROPS Hebrew vowels
     entirely (בָּרָא → 'vrʔ'), but phonikud produces correct 'bara', and
     distinguishes qatal (katˈal) from qittel (kitˈel).
  2. Kokoro-hebrew ONNX (thewh1teagle/kokoro-hebrew-nc) speaks the IPA with
     is_phonemes=True. Single speaker (he_shaul), non-commercial terms,
     downloadable WITHOUT a gated HF token.

Requires Python <3.13 (phonikud constraint). Use the venv-align venv:
    uv venv venv-align --python 3.12
    uv pip install --python venv-align/bin/python \
        git+https://github.com/thewh1teagle/phonikud.git kokoro-onnx

Output: data/audio/words/{node_id}.wav, mirrored to data/audio/letters/ for
consonant/vowel nodes so the existing letter endpoint works.

Usage:
    python3 scripts/generate_word_audio.py --dry-run
    python3 scripts/generate_word_audio.py --apply
    python3 scripts/generate_word_audio.py --apply --limit 50
"""

import argparse
import json
import re
import shutil
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
WORDS_DIR = BASE / "data" / "audio" / "words"
LETTERS_DIR = BASE / "data" / "audio" / "letters"
KOKORO_MODEL = BASE / "data" / "audio" / "kokoro" / "kokoro.onnx"
KOKORO_VOICES = BASE / "data" / "audio" / "kokoro" / "voices-hebrew.bin"
VOICE = "he_shaul"


def _pointed_text(node_id, title, content):
    heb = content.get("hebrew") or ""
    if heb:
        return heb
    # Title Hebrew before the em-dash: "שְׁמַע יִשְׂרָאֵל — Hear O Israel" → the phrase;
    # "Root כתב — write" → כתב
    if title and "—" in title:
        head = title.split("—", 1)[0]
        if any("\u0590" <= ch <= "\u05FF" for ch in head):
            # Strip the English "Root " label for root nodes so TTS reads only Hebrew
            head = re.sub(r"^Root\s+", "", head, flags=re.IGNORECASE).strip()
            if head:
                return head
    for p in reversed(re.findall(r"\(([^)]+)\)", title or "")):
        if any("\u0590" <= ch <= "\u05FF" for ch in p):
            return p
    return ""


def _iter_items(conn):
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT n.id, n.title, n.category, l.content_json
        FROM hebrew_nodes n JOIN hebrew_lessons l ON l.node_id = n.id
        WHERE n.category IN ('consonant','vowel','word','grammar','phrase','root')
        ORDER BY n.category, n.id
    """).fetchall()
    for r in rows:
        try:
            content = json.loads(r["content_json"]) if r["content_json"] else {}
        except (json.JSONDecodeError, TypeError):
            content = {}
        text = _pointed_text(r["id"], r["title"], content)
        if not text:
            continue
        yield (r["id"], r["title"], r["category"], text)


def load_models():
    """Load phonikud (G2P) and Kokoro (TTS)."""
    from phonikud import phonemize
    from kokoro_onnx import Kokoro
    kokoro = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    return phonemize, kokoro


def synth_word(phonemize, kokoro, pointed_text, out_path, category=None):
    """Synthesize one pointed word: phonikud → IPA → Kokoro phonemes.

    Vowel nodes carry only a niqqud mark (e.g. 'ַ'), which has no sound alone —
    synthesize it on a carrier syllable (bet + vowel) so the learner hears the
    vowel's sound. The explanation field gives the sound for the UI.
    """
    import numpy as np
    import soundfile as sf

    if category == "vowel":
        # carrier: bet + the vowel mark → e.g. בַּ = 'ba'
        carrier = "\u05d1" + pointed_text
        text_for_ipa = carrier
    else:
        text_for_ipa = pointed_text

    ipa = phonemize(text_for_ipa).strip()
    if not ipa:
        raise ValueError(f"no IPA for: {pointed_text!r}")
    samples, sr = kokoro.create(ipa, voice=VOICE, lang="he", is_phonemes=True)
    samples = np.asarray(samples, dtype=np.float32)
    rms = float(np.sqrt(np.mean(samples ** 2)))
    if rms > 1e-6:
        samples = samples * (0.12 / rms)
        samples = np.clip(samples, -1.0, 1.0)
    sf.write(str(out_path), samples, sr)
    voiced = int((np.abs(samples) > 0.01).sum()) / sr
    return len(samples) / sr, voiced


def main():
    parser = argparse.ArgumentParser(description="Generate Hebrew word audio (phonikud → Kokoro)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Only generate first N items (debug)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N items (resume)")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if the .wav already exists")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to apply")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    items = list(_iter_items(conn))
    items = items[args.offset:]
    if args.limit:
        items = items[:args.limit]
    # Idempotent: skip nodes whose audio already exists unless --force
    if not args.force:
        before = len(items)
        items = [it for it in items if not (WORDS_DIR / f"{it[0]}.wav").exists()]
        print(f"Items to generate: {len(items)} ({before - len(items)} already exist)")
    else:
        print(f"Items to generate: {len(items)} (--force)")

    if args.dry_run:
        for nid, title, cat, text in items[:12]:
            print(f"  {nid:<26} [{cat:<10}] {text}")
        conn.close()
        return

    WORDS_DIR.mkdir(parents=True, exist_ok=True)
    LETTERS_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading phonikud + Kokoro-hebrew...")
    phonemize, kokoro = load_models()

    done = 0
    errors = 0
    silent = 0
    for nid, title, cat, text in items:
        out = WORDS_DIR / f"{nid}.wav"
        try:
            dur, voiced = synth_word(phonemize, kokoro, text, out, category=cat)
            if voiced < 0.15:
                silent += 1
            if cat in ("consonant", "vowel"):
                shutil.copy(out, LETTERS_DIR / f"{nid}.wav")
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(items)} ({nid})")
        except Exception as e:
            errors += 1
            print(f"  ERROR {nid} ({text!r}): {e}")

    conn.close()
    print(f"Done: {done} generated, {errors} errors, {silent} suspiciously-short")


if __name__ == "__main__":
    main()
