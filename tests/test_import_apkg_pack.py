"""Generic apkg-pack importer: gloss, images, tag/media filters, pack.json."""

import json
import sqlite3
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_script(name: str):
    import importlib.util
    path = Path(__file__).resolve().parent.parent / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _load_script("import_apkg_pack")


def _make_pack_apkg(path: Path):
    """3 notes: audio+gloss, image+gloss, Ross-tagged (excluded)."""
    work = path.parent / "raw"
    work.mkdir(exist_ok=True)
    (work / "0").write_bytes(b"FAKE_MP3")
    (work / "1").write_bytes(b"FAKE_PNG")
    (work / "2").write_bytes(b"ROSS_MP3")
    (work / "media").write_text(json.dumps(
        {"0": "el.mp3", "1": "el.png", "2": "ross_el.mp3"}))
    db = work / "collection.anki21"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE col (models TEXT)")
    models = {"m1": {"flds": [{"name": "Hebrew"}, {"name": "Gloss"}]}}
    conn.execute("INSERT INTO col VALUES (?)", (json.dumps(models),))
    conn.execute("CREATE TABLE notes (id INTEGER, mid TEXT, flds TEXT, tags TEXT)")
    conn.execute("INSERT INTO notes VALUES (1, 'm1', ?, '')",
                 ("אֵל [sound:el.mp3]\x1fGod",))
    conn.execute("INSERT INTO notes VALUES (2, 'm1', ?, '')",
                 ('אֵל <img src="el.png">\x1fGod',))
    conn.execute("INSERT INTO notes VALUES (3, 'm1', ?, 'third-party')",
                 ("אֵל [sound:ross_el.mp3]\x1fGod",))
    conn.commit()
    conn.close()
    with zipfile.ZipFile(path, "w") as z:
        for f in ("0", "1", "2", "media", "collection.anki21"):
            z.write(work / f, f)


def test_pack_parse_images_and_gloss(tmp_path):
    apkg = tmp_path / "pack.apkg"
    _make_pack_apkg(apkg)
    parsed = mod.parse_apkg(apkg)
    assert len(parsed["notes"]) == 3
    assert mod.pick_hebrew_field(parsed["notes"]) == "Hebrew"
    assert mod.pick_gloss_field(parsed["notes"], "Hebrew") == "Gloss"
    entries = mod.build_pack(parsed, media="all")
    assert len(entries) == 1  # merged on headword
    e = entries[0]
    assert e == {"hebrew": "אֵל", "gloss": "God",
                 "audio": ["el.mp3", "ross_el.mp3"], "images": ["el.png"]}


def test_pack_filters(tmp_path):
    apkg = tmp_path / "pack.apkg"
    _make_pack_apkg(apkg)
    parsed = mod.parse_apkg(apkg)
    entries = mod.build_pack(parsed, exclude_tags=["third-party"],
                             exclude_media=["ross"], media="all")
    assert len(entries) == 1
    assert entries[0]["audio"] == ["el.mp3"]


def test_pack_apply_writes_manifest_and_pack_json(tmp_path):
    apkg = tmp_path / "pack.apkg"
    _make_pack_apkg(apkg)
    parsed = mod.parse_apkg(apkg)
    out = tmp_path / "anki"
    entries = mod.build_pack(parsed, exclude_tags=["third-party"],
                             exclude_media=["ross"], media="all")
    stats = mod.apply_pack(parsed, entries, out, "testpack")
    assert stats["files_copied"] == 2  # 1 mp3 + 1 png
    manifest = json.loads((out / "manifest.json").read_text("utf-8"))
    assert manifest == {"אֵל": ["אֵל__el.mp3"]}
    pack = json.loads((out / "pack.json").read_text("utf-8"))
    assert pack["pack"] == "testpack"
    assert pack["entries"] == [{"hebrew": "אֵל", "gloss": "God",
                                "audio": ["אֵל__el.mp3"],
                                "images": ["אֵל__el.png"]}]
    assert (out / "אֵל__el.png").read_bytes() == b"FAKE_PNG"
    # Idempotent re-run copies nothing.
    stats2 = mod.apply_pack(parsed, entries, out, "testpack")
    assert stats2["files_copied"] == 0


def test_legacy_audio_only_path_unchanged(tmp_path):
    """Default `whv` behavior: audio-only, legacy manifest shape."""
    apkg = tmp_path / "pack.apkg"
    _make_pack_apkg(apkg)
    parsed = mod.parse_apkg(apkg)
    mapping = mod.build_mapping(parsed)
    assert mapping == {"אֵל": ["el.mp3", "ross_el.mp3"]}
    stats = mod.apply_import(parsed, mapping, tmp_path / "anki")
    assert stats["files_copied"] == 2
    manifest = json.loads((tmp_path / "anki" / "manifest.json").read_text("utf-8"))
    assert set(manifest["אֵל"]) == {"אֵל__el.mp3", "אֵל__ross_el.mp3"}
