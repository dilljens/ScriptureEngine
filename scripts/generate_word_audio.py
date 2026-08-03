#!/usr/bin/env python3
"""Generate Hebrew word audio with F5-TTS Hebrew v2.

Math Academy Way + audio review decision: word-level audio is TTS (real
Shmuelof audio is CC BY-NC-ND — splicing it into word clips is not legal for
a public app). F5-TTS Hebrew v2 is Apache-2.0 and was re-vocalized with the
Phonikud G2P at training time, so it reads pointed Hebrew (niqqud) correctly
from the pointed text directly — no separate G2P step at inference.

Loads the model exactly as the model card requires: `model_state_dict`
(not ema), `text_num_embeds` overridden to the custom vocab size, the
included `vocab.txt` for tokenization, and `model.sample()` called directly
(the high-level F5 API is documented as broken for fine-tuned models).
Uses `no_ref_audio=True` so no reference clip is needed (built-in voice).

Output: data/audio/words/{node_id}.wav, mirrored to data/audio/letters/ for
consonant/vowel nodes so the existing letter endpoint works.

Usage:
    python3 scripts/generate_word_audio.py --dry-run
    python3 scripts/generate_word_audio.py --apply
    python3 scripts/generate_word_audio.py --apply --nfe 24   # faster, slightly lower quality
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
WORDS_DIR = BASE / "data" / "audio" / "words"
LETTERS_DIR = BASE / "data" / "audio" / "letters"


def _pointed_text(node_id, title, content):
    heb = content.get("hebrew") or ""
    if heb:
        return heb
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


def load_f5_model(device="cuda"):
    """Load F5-TTS Hebrew v2 using the official loader + F5TTS_v1_Base arch.

    Model card: use `model_state_dict` (NOT ema) — the fine-tune checkpoint
    is already pruned to a single state dict.
    """
    from cached_path import cached_path
    from f5_tts.infer.utils_infer import load_model

    ckpt = cached_path("hf://Yzamari/f5tts-hebrew-v2/model.safetensors")
    vocab_file = cached_path("hf://Yzamari/f5tts-hebrew-v2/vocab.txt")

    from f5_tts.model import DiT
    model = load_model(
        DiT,
        dict(
            dim=1024, depth=22, heads=16, ff_mult=2, text_dim=512,
            text_mask_padding=True, conv_layers=4, attn_backend="torch",
            attn_mask_enabled=False,
        ),
        str(ckpt),
        mel_spec_type="vocos",
        vocab_file=str(vocab_file),
        use_ema=False,  # model card: NOT ema
        device=device,
    )
    model = model.to(device).eval()
    return model


def synth_f5_word(text, model, device="cuda", nfe=32, seed=None):
    """Synthesize one pointed Hebrew word with the fine-tuned F5 model.

    Mirrors f5_tts's _infer_basic but with no_ref_audio=True (no reference
    clip → built-in voice) and a duration scaled to the word length.
    """
    import torch
    from f5_tts.infer.utils_infer import convert_char_to_pinyin, target_sample_rate, hop_length

    final_text_list = convert_char_to_pinyin([text])

    # cond is the WAVEFORM (CFM converts to mel internally). With
    # no_ref_audio=True it gets zeroed, but it must have a real waveform shape
    # for the internal mel computation — use a short silence prompt.
    ref_audio_len = int(0.6 * target_sample_rate / hop_length)  # 0.6s silence
    gen_text_len = len(text.encode("utf-8"))
    duration = ref_audio_len + max(40, int(gen_text_len * 24) + 40)

    with torch.inference_mode():
        generated, _ = model.sample(
            cond=torch.zeros(1, int(0.6 * target_sample_rate), device=device),
            text=final_text_list,
            duration=duration,
            steps=nfe,
            cfg_strength=2.0,          # F5 default
            sway_sampling_coef=-1.0,   # F5 default
            seed=seed,
            no_ref_audio=True,
        )
        generated = generated[:, ref_audio_len:, :]  # drop silence-prompt prefix
        generated = generated.permute(0, 2, 1).float()  # [B, time, mel] -> [B, mel, time]

    # decode mel → wav with the model's vocos vocoder
    from f5_tts.infer.utils_infer import load_vocoder
    vocoder = load_vocoder("vocos", device=device)
    wav = vocoder.decode(generated)
    # normalize to F5's target RMS (0.1) so short words aren't whisper-quiet
    import torch as _t
    rms = _t.sqrt(_t.mean(wav ** 2))
    if rms.item() > 0:
        wav = wav * (0.1 / rms)
    return wav


def main():
    parser = argparse.ArgumentParser(description="Generate Hebrew word audio")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--nfe", type=int, default=32)
    parser.add_argument("--limit", type=int, default=0, help="Only generate first N items (debug)")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to apply")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    items = list(_iter_items(conn))
    if args.limit:
        items = items[:args.limit]
    print(f"Items to generate: {len(items)}")

    if args.dry_run:
        for nid, title, cat, text in items[:12]:
            print(f"  {nid:<26} [{cat:<10}] {text}")
        conn.close()
        return

    WORDS_DIR.mkdir(parents=True, exist_ok=True)
    LETTERS_DIR.mkdir(parents=True, exist_ok=True)

    import torch
    import torchaudio
    print("Loading F5-TTS Hebrew v2...")
    model = load_f5_model(args.device)

    done = 0
    errors = 0
    for nid, title, cat, text in items:
        out = WORDS_DIR / f"{nid}.wav"
        try:
            wav = synth_f5_word(text, model, args.device, nfe=args.nfe)
            if wav.dim() == 1:
                wav = wav.unsqueeze(0)
            torchaudio.save(str(out), wav.cpu(), 24000)
            if cat in ("consonant", "vowel"):
                torchaudio.save(str(LETTERS_DIR / f"{nid}.wav"), wav.cpu(), 24000)
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{len(items)} ({nid})")
        except Exception as e:
            errors += 1
            print(f"  ERROR {nid} ({text!r}): {e}")

    conn.close()
    print(f"Done: {done} generated, {errors} errors")


if __name__ == "__main__":
    main()
