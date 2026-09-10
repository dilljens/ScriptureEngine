#!/usr/bin/env python3
"""Import word audio from an Anki shared deck (.apkg) for Hebrew study.

AnkiWeb's shared-deck license is PERSONAL STUDY ONLY — decks you download may
not be redistributed. This script is for local use: you download a deck with
Anki Desktop (e.g. a Biblical Hebrew vocab deck with [sound:] clips), then run:

    python3 scripts/import_anki_audio.py ~/Downloads/hebrew.apkg --dry-run
    python3 scripts/import_anki_audio.py ~/Downloads/hebrew.apkg --apply

Output (gitignored): data/audio/anki/<hebrew>__<orig>.mp3 + manifest.json
mapping Hebrew headwords to files. The /hebrew/audio endpoint serves them.

.apkg layout: a ZIP with a `media` JSON map ({"0": "word.mp3", ...}), media
blobs named by key, and collection.anki21(b)/.anki2 SQLite (notes.flds fields
joined by \\x1f, [sound:file] tags in field HTML). Stdlib only.
"""

import argparse
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

BASE = Path(__file__).parent.parent
ANKI_DIR = BASE / "data" / "audio" / "anki"
MANIFEST = ANKI_DIR / "manifest.json"

SOUND_RE = re.compile(r"\[sound:([^\]]+)\]")
TAG_RE = re.compile(r"<[^>]+>")
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")


def clean_field_html(value: str) -> str:
    """Strip Anki [sound:] tags and HTML, normalize whitespace."""
    value = SOUND_RE.sub("", value or "")
    value = TAG_RE.sub("", value)
    return " ".join(value.split()).strip()


def headword_key(text: str) -> str:
    """NFC-normalized headword used for manifest lookup."""
    return unicodedata.normalize("NFC", (text or "").strip())


def sanitize_filename(name: str) -> str:
    """Filesystem-safe but Hebrew-preserving filename."""
    out = []
    for ch in name:
        if ch.isalnum() or ch in "-_. " or "\u0590" <= ch <= "\u05FF":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out).strip().rstrip(".") or "audio"


def parse_apkg(path: Path) -> dict:
    """Parse an .apkg into {deck, notes: [{fields, sounds, tags}], media: {name: bytes}}.

    Pure-ish (reads only the given file); raises FileNotFoundError/ValueError.
    """
    if not path.exists():
        raise FileNotFoundError(f"not found: {path}")
    tmp = Path(tempfile.mkdtemp(prefix="apkg_"))
    with zipfile.ZipFile(path) as z:
        z.extractall(tmp)
    media_map = json.loads((tmp / "media").read_text(encoding="utf-8"))
    media = {}
    for key, fname in media_map.items():
        blob = tmp / key
        if blob.exists():
            media[fname] = blob.read_bytes()
    # Newest usable collection DB wins (.anki21b > .anki21 > .anki2 dummy check).
    con = None
    for name in ("collection.anki21b", "collection.anki21", "collection.anki2"):
        p = tmp / name
        if not p.exists():
            continue
        try:
            c = sqlite3.connect(str(p))
            n = c.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
            if n > 1:
                con = c
                break
            c.close()
        except sqlite3.Error:
            continue
    if con is None:
        raise ValueError("no usable collection DB in apkg (dummy .anki2 only?)")
    try:
        models = json.loads(con.execute("SELECT models FROM col").fetchone()[0])
        mid_to_fields = {mid: [f["name"] for f in m["flds"]] for mid, m in models.items()}
        notes = []
        for nid, mid, flds, tags in con.execute("SELECT id, mid, flds, tags FROM notes"):
            fields = dict(zip(mid_to_fields.get(str(mid), []), flds.split("\x1f")))
            sounds = sorted({s for v in fields.values() for s in SOUND_RE.findall(v or "")})
            notes.append({"id": nid, "fields": fields, "sounds": sounds, "tags": tags or ""})
    finally:
        con.close()
    shutil.rmtree(tmp, ignore_errors=True)
    return {"notes": notes, "media": media}


def pick_hebrew_field(notes: list, preferred: str = "") -> str:
    """Choose the field holding Hebrew headwords (explicit name or heuristic)."""
    if preferred:
        return preferred
    scores: dict = {}
    for note in notes[:200]:
        for name, value in note["fields"].items():
            if value and HEBREW_RE.search(value):
                scores[name] = scores.get(name, 0) + 1
    if not scores:
        raise ValueError("no field with Hebrew text found (use --hebrew-field)")
    return max(scores.items(), key=lambda kv: kv[1])[0]


def build_mapping(parsed: dict, hebrew_field: str = "") -> dict:
    """Map Hebrew headword -> [sound filenames present in the apkg media]."""
    field = hebrew_field or pick_hebrew_field(parsed["notes"])
    mapping: dict = {}
    for note in parsed["notes"]:
        raw = note["fields"].get(field, "")
        headword = headword_key(clean_field_html(raw))
        if not headword or not HEBREW_RE.search(headword):
            continue
        files = [s for s in note["sounds"] if s in parsed["media"]]
        if files:
            mapping.setdefault(headword, [])
            for f in files:
                if f not in mapping[headword]:
                    mapping[headword].append(f)
    return mapping


def apply_import(parsed: dict, mapping: dict, out_dir: Path = ANKI_DIR) -> dict:
    """Copy media blobs to out_dir and merge manifest.json. Returns stats."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {}
    existing_files = {f for files in manifest.values() for f in files}
    copied, words = 0, 0
    for headword, files in mapping.items():
        stored = []
        for fname in files:
            target_name = f"{sanitize_filename(headword)}__{sanitize_filename(fname)}"
            target = out_dir / target_name
            if target_name not in existing_files and not target.exists():
                target.write_bytes(parsed["media"][fname])
                copied += 1
            existing_files.add(target_name)
            stored.append(target_name)
        if headword not in manifest:
            words += 1
        manifest[headword] = sorted(set(manifest.get(headword, []) + stored))
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"words": len(mapping), "new_words": words, "files_copied": copied,
            "total_manifest_words": len(manifest)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Anki .apkg word audio (local, personal use)")
    parser.add_argument("apkg", help="Path to the downloaded .apkg file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--hebrew-field", default="", help="Field holding the Hebrew headword")
    parser.add_argument("--out", default=str(ANKI_DIR))
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to import")
        return 1
    parsed = parse_apkg(Path(args.apkg))
    print(f"Notes: {len(parsed['notes'])}, media files: {len(parsed['media'])}")
    field = args.hebrew_field or pick_hebrew_field(parsed["notes"])
    print(f"Hebrew field: {field}")
    mapping = build_mapping(parsed, field)
    with_audio = sum(1 for n in parsed["notes"] if n["sounds"])
    print(f"Notes with [sound:]: {with_audio}, headwords mapped: {len(mapping)}")
    for hw in list(mapping)[:8]:
        print(f"  {hw} -> {mapping[hw]}")
    if args.dry_run:
        return 0
    stats = apply_import(parsed, mapping, Path(args.out))
    print(f"Imported: {stats['new_words']} new words, {stats['files_copied']} files "
          f"({stats['total_manifest_words']} words in manifest)")
    print("Reminder: Anki shared decks are personal-study only — do not commit data/audio/anki/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
