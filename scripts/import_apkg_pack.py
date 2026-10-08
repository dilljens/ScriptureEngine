#!/usr/bin/env python3
"""Import flashcard packs from Anki shared decks (.apkg) for Hebrew study.

AnkiWeb's shared-deck license is PERSONAL STUDY ONLY — decks you download may
not be redistributed. This script is for local use: you download a deck with
Anki Desktop (e.g. a Biblical Hebrew vocab deck with [sound:] clips), then run:

    python3 scripts/import_apkg_pack.py ~/Downloads/hebrew.apkg --dry-run
    python3 scripts/import_apkg_pack.py ~/Downloads/hebrew.apkg --apply
    python3 scripts/import_apkg_pack.py ~/Downloads/hackett.apkg --pack hackett --apply

Output (gitignored): data/audio/anki/<hebrew>__<orig>.mp3 + manifest.json
mapping Hebrew headwords to audio files, plus pack.json with
[{hebrew, gloss, audio, images}] for vocab seeding. The /hebrew/audio
endpoint serves the audio; pictures are stored for the picture-card direction.

.apkg layout: a ZIP with a `media` JSON map ({"0": "word.mp3", ...}), media
blobs named by key, and collection.anki21(b)/.anki2 SQLite (notes.flds fields
joined by \\x1f, [sound:file] tags and <img src> in field HTML). Stdlib only.

Pack presets (--pack) fill field names and filters; every preset is overridable
by explicit flags. `whv` is the default and reproduces the original audio-only
import byte-for-byte.
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
IMG_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.IGNORECASE)
TAG_RE = re.compile(r"<[^>]+>")
HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
LATIN_RE = re.compile(r"[A-Za-z]{3,}")

AUDIO_EXTS = {".mp3", ".ogg", ".wav", ".m4a", ".opus"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

# Per-pack presets: field names ("" = auto-detect), media kinds to import,
# tag/media filters. Field names for hackett/bbh2 are best-effort — dry-run
# prints the deck's real fields; correct the preset and re-run.
PACKS = {
    "whv": {"hebrew_field": "", "gloss_field": "", "media": "audio",
            "exclude_tags": [], "exclude_media": []},
    # Hackett deck (CC BY-SA 4.0, author audio CC0): Ross-sourced audio
    # subsets carry third-party terms — filtered by media-name substring.
    "hackett": {"hebrew_field": "", "gloss_field": "", "media": "audio",
                "exclude_tags": [], "exclude_media": ["ross", "Ross"]},
    "bbh2": {"hebrew_field": "", "gloss_field": "", "media": "audio",
             "exclude_tags": [], "exclude_media": []},
}


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
            images = sorted({s for v in fields.values() for s in IMG_RE.findall(v or "")})
            notes.append({"id": nid, "fields": fields, "sounds": sounds,
                          "images": images, "tags": tags or ""})
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


def pick_gloss_field(notes: list, hebrew_field: str, preferred: str = "") -> str:
    """Choose the field holding the English gloss (explicit, name, heuristic)."""
    if preferred:
        return preferred
    names = list(notes[0]["fields"]) if notes else []
    for want in ("gloss", "meaning", "english", "definition", "back", "translation"):
        for name in names:
            if name.strip().lower() == want:
                return name
    scores: dict = {}
    for note in notes[:200]:
        for name, value in note["fields"].items():
            if name != hebrew_field and value and LATIN_RE.search(clean_field_html(value)):
                scores[name] = scores.get(name, 0) + 1
    if not scores:
        return ""
    return max(scores.items(), key=lambda kv: kv[1])[0]


def note_excluded(note: dict, exclude_tags: list, exclude_media: list) -> bool:
    """Tag/media filters (e.g. third-party audio subsets on user imports)."""
    tags = set((note.get("tags") or "").split())
    if any(t in tags for t in exclude_tags):
        return True
    blobs = list(note.get("sounds") or []) + list(note.get("images") or [])
    return any(sub in b for b in blobs for sub in exclude_media)


def build_pack(parsed: dict, hebrew_field: str = "", gloss_field: str = "",
               exclude_tags=(), exclude_media=(),
               media: str = "all") -> list:
    """Pack entries [{hebrew, gloss, audio, images}] for vocab seeding.

    media: "audio" (sounds only), "images" (<img> only), "all".
    Only files present in the apkg media map are kept.
    """
    field = hebrew_field or pick_hebrew_field(parsed["notes"])
    gloss_name = gloss_field or pick_gloss_field(parsed["notes"], field)
    want_audio = media in ("audio", "all")
    want_images = media in ("images", "all")
    entries: dict = {}
    for note in parsed["notes"]:
        if note_excluded(note, list(exclude_tags), list(exclude_media)):
            continue
        raw = note["fields"].get(field, "")
        headword = headword_key(clean_field_html(raw))
        if not headword or not HEBREW_RE.search(headword):
            continue
        gloss = headword_key(clean_field_html(note["fields"].get(gloss_name, ""))) if gloss_name else ""
        if gloss == headword:
            gloss = ""
        audio = [s for s in note["sounds"] if s in parsed["media"]] if want_audio else []
        images = [s for s in note.get("images", []) if s in parsed["media"]] if want_images else []
        entry = entries.setdefault(headword, {"hebrew": headword, "gloss": "",
                                              "audio": [], "images": []})
        if gloss and not entry["gloss"]:
            entry["gloss"] = gloss
        for f in audio:
            if f not in entry["audio"]:
                entry["audio"].append(f)
        for f in images:
            if f not in entry["images"]:
                entry["images"].append(f)
    return sorted(entries.values(), key=lambda e: e["hebrew"])


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


def apply_pack(parsed: dict, entries: list, out_dir: Path = ANKI_DIR,
               pack_name: str = "pack") -> dict:
    """Copy entry media to out_dir; write manifest.json (audio) + pack.json.

    manifest.json keeps the legacy audio-only shape (byte-identical for
    audio-only entries); pack.json holds [{hebrew, gloss, audio, images}]
    with stored filenames for vocab seeding.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        manifest = {}
    existing_files = {f for files in manifest.values() for f in files}
    try:
        pack_doc = json.loads((out_dir / "pack.json").read_text(encoding="utf-8"))
        pack = pack_doc.get("entries", [])
        pack_by_hw = {e["hebrew"]: e for e in pack}
    except (FileNotFoundError, json.JSONDecodeError):
        pack, pack_by_hw = [], {}

    def _store(fname: str) -> str:
        target_name = f"{sanitize_filename(headword)}__{sanitize_filename(fname)}"
        target = out_dir / target_name
        if target_name not in existing_files and not target.exists():
            target.write_bytes(parsed["media"][fname])
            stats["files_copied"] += 1
        existing_files.add(target_name)
        return target_name

    stats = {"words": len(entries), "files_copied": 0}
    for e in entries:
        headword = e["hebrew"]
        stored_audio = [_store(f) for f in e["audio"]]
        stored_images = [_store(f) for f in e["images"]]
        if stored_audio:
            manifest[headword] = sorted(set(manifest.get(headword, []) + stored_audio))
        if headword in pack_by_hw:
            old = pack_by_hw[headword]
            old["audio"] = sorted(set(old.get("audio", []) + stored_audio))
            old["images"] = sorted(set(old.get("images", []) + stored_images))
            if e["gloss"] and not old.get("gloss"):
                old["gloss"] = e["gloss"]
        else:
            row = {"hebrew": headword, "gloss": e["gloss"],
                   "audio": stored_audio, "images": stored_images}
            pack.append(row)
            pack_by_hw[headword] = row
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    pack.sort(key=lambda r: r["hebrew"])
    (out_dir / "pack.json").write_text(
        json.dumps({"pack": pack_name, "entries": pack},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    stats["total_manifest_words"] = len(manifest)
    stats["pack_entries"] = len(pack)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Anki .apkg flashcard pack (local, personal use)")
    parser.add_argument("apkg", help="Path to the downloaded .apkg file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--pack", default="whv", choices=sorted(PACKS),
                        help="Pack preset for fields/filters (default: whv)")
    parser.add_argument("--pack-name", default="",
                        help="Name recorded in pack.json (default: --pack value)")
    parser.add_argument("--hebrew-field", default="", help="Field holding the Hebrew headword")
    parser.add_argument("--gloss-field", default="", help="Field holding the English gloss")
    parser.add_argument("--media", default="", choices=("", "audio", "images", "all"),
                        help="Media kinds to import (default: preset's)")
    parser.add_argument("--exclude-tag", action="append", default=[],
                        help="Skip notes with this tag (repeatable)")
    parser.add_argument("--exclude-media", action="append", default=[],
                        help="Skip media files containing this substring (repeatable)")
    parser.add_argument("--out", default=str(ANKI_DIR))
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to import")
        return 1
    preset = PACKS[args.pack]
    hebrew_field = args.hebrew_field or preset["hebrew_field"]
    gloss_field = args.gloss_field or preset["gloss_field"]
    media = args.media or preset["media"]
    exclude_tags = list(preset["exclude_tags"]) + args.exclude_tag
    exclude_media = list(preset["exclude_media"]) + args.exclude_media

    parsed = parse_apkg(Path(args.apkg))
    print(f"Notes: {len(parsed['notes'])}, media files: {len(parsed['media'])}")
    field = hebrew_field or pick_hebrew_field(parsed["notes"])
    print(f"Hebrew field: {field}")
    gloss_name = gloss_field or pick_gloss_field(parsed["notes"], field)
    print(f"Gloss field: {gloss_name or '(none)'}")
    mapping = build_mapping(parsed, field)
    entries = build_pack(parsed, field, gloss_name, exclude_tags, exclude_media,
                         "all" if media == "all" else media)
    with_audio = sum(1 for n in parsed["notes"] if n["sounds"])
    print(f"Notes with [sound:]: {with_audio}, headwords mapped: {len(mapping)}, "
          f"pack entries: {len(entries)}")
    for e in entries[:8]:
        print(f"  {e['hebrew']} = {e['gloss'][:40]} -> {e['audio'] + e['images']}")
    if args.dry_run:
        return 0
    stats = apply_pack(parsed, entries, Path(args.out), args.pack_name or args.pack)
    print(f"Imported: {stats['words']} words, {stats['files_copied']} files "
          f"({stats['total_manifest_words']} words in manifest, "
          f"{stats['pack_entries']} pack entries)")
    print("Reminder: Anki shared decks are personal-study only — do not commit data/audio/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
