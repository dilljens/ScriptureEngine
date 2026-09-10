"""Anki-parity for Hebrew learning: per-direction scheduling, pacing, grading."""

import importlib.util
import json
import sqlite3
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.hebrew import (
    _anki_fold,
    _ensure_hebrew_review_state,
    _grade_verb_answer,
    read_hebrew_prefs,
    resolve_pacing,
)

BASE = Path(__file__).resolve().parent.parent


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, BASE / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_resolve_pacing_pref_and_override():
    prefs = {"new_cards_per_day": 10, "max_reviews_per_day": 100}
    assert resolve_pacing(-1, -1, prefs) == (10, 100)
    assert resolve_pacing(5, 50, prefs) == (5, 50)
    assert resolve_pacing(-5, -1, prefs) == (10, 100)  # negative = use pref
    assert resolve_pacing(0, 0, prefs) == (0, 0)  # explicit 0 = none/unlimited
    assert resolve_pacing(-1, -1, {}) == (10, 100)  # defaults


def test_hebrew_prefs_defaults_and_roundtrip(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "prefs.db"))
    assert read_hebrew_prefs(conn, "u1") == {"new_cards_per_day": 10, "max_reviews_per_day": 100}
    conn.execute(
        "INSERT INTO hebrew_prefs (user_id, new_cards_per_day, max_reviews_per_day)"
        " VALUES ('u1', 5, 50)")
    assert read_hebrew_prefs(conn, "u1") == {"new_cards_per_day": 5, "max_reviews_per_day": 50}
    conn.close()


def test_review_state_migration_adds_card_mode(tmp_path):
    db = tmp_path / "m.db"
    conn = sqlite3.connect(str(db))
    # Old schema: PK(user_id, node_id), no card_mode
    conn.execute("""
        CREATE TABLE hebrew_review_state (
            user_id TEXT NOT NULL, node_id TEXT NOT NULL,
            stability REAL NOT NULL DEFAULT 0.0, difficulty REAL NOT NULL DEFAULT 5.0,
            due TEXT NOT NULL DEFAULT (datetime('now')),
            last_review TEXT, last_rating INTEGER,
            reps INTEGER NOT NULL DEFAULT 0, lapses INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY(user_id,node_id)
        )
    """)
    conn.execute(
        "INSERT INTO hebrew_review_state (user_id, node_id, stability, reps)"
        " VALUES ('u', 'aleph', 2.5, 3)")
    conn.commit()
    _ensure_hebrew_review_state(conn)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(hebrew_review_state)").fetchall()]
    assert "card_mode" in cols
    row = conn.execute(
        "SELECT stability, reps, card_mode FROM hebrew_review_state").fetchone()
    assert tuple(row) == (2.5, 3, "")
    # New PK allows one row per direction
    conn.execute(
        "INSERT INTO hebrew_review_state (user_id, node_id, card_mode, stability)"
        " VALUES ('u', 'aleph', 'hearing', 1.0)")
    assert conn.execute("SELECT COUNT(*) FROM hebrew_review_state").fetchone()[0] == 2
    # Idempotent: second ensure is a no-op
    _ensure_hebrew_review_state(conn)
    assert conn.execute("SELECT COUNT(*) FROM hebrew_review_state").fetchone()[0] == 2
    conn.close()


def test_grade_verb_answer_text_letter_index():
    drill = {"correct": "Qal", "options": json.dumps(["Qal", "Niphal", "Piel", "Hiphil"])}
    assert _grade_verb_answer(drill, "Qal") is True
    assert _grade_verb_answer(drill, "qal") is True
    assert _grade_verb_answer(drill, "A") is True
    assert _grade_verb_answer(drill, "a") is True
    assert _grade_verb_answer(drill, "0") is True
    assert _grade_verb_answer(drill, "1") is True  # 1-based also accepted
    assert _grade_verb_answer(drill, "Niphal") is False
    assert _grade_verb_answer(drill, "B") is False
    assert _grade_verb_answer(drill, "") is False
    assert _grade_verb_answer({"correct": "", "options": "[]"}, "Qal") is False


def test_anki_fold_strips_niqqud_and_finals():
    assert _anki_fold("בְּרֵאשִׁית") == _anki_fold("בראשית")
    assert _anki_fold("אֵל") == _anki_fold("אל")
    assert _anki_fold("ך") == "כ"


def _make_apkg(path: Path):
    """Minimal .apkg: 2 notes with [sound:], 2 media blobs."""
    work = path.parent / "raw"
    work.mkdir(exist_ok=True)
    (work / "0").write_bytes(b"FAKE_MP3_A")
    (work / "1").write_bytes(b"FAKE_MP3_B")
    (work / "media").write_text(json.dumps({"0": "el.mp3", "1": "shama.mp3"}))
    db = work / "collection.anki21"
    conn = sqlite3.connect(str(db))
    models = {"m1": {"flds": [{"name": "Hebrew"}, {"name": "Gloss"}]}}
    conn.execute("CREATE TABLE col (models TEXT)")
    conn.execute("INSERT INTO col VALUES (?)", (json.dumps(models),))
    conn.execute("CREATE TABLE notes (id INTEGER, mid TEXT, flds TEXT, tags TEXT)")
    conn.execute("INSERT INTO notes VALUES (1, 'm1', ?, '')",
                 ("אֵל [sound:el.mp3]\x1fGod",))
    conn.execute("INSERT INTO notes VALUES (2, 'm1', ?, 'audio-author')",
                 ("<b>שְׁמַע</b> [sound:shama.mp3]\x1fhear",))
    conn.commit()
    conn.close()
    with zipfile.ZipFile(path, "w") as z:
        for f in ("0", "1", "media", "collection.anki21"):
            z.write(work / f, f)


def test_anki_apkg_parse_and_mapping(tmp_path):
    mod = _load_script("import_anki_audio")
    apkg = tmp_path / "heb.apkg"
    _make_apkg(apkg)
    parsed = mod.parse_apkg(apkg)
    assert len(parsed["notes"]) == 2
    assert set(parsed["media"]) == {"el.mp3", "shama.mp3"}
    mapping = mod.build_mapping(parsed)
    assert mapping == {"אֵל": ["el.mp3"], "שְׁמַע": ["shama.mp3"]}
    stats = mod.apply_import(parsed, mapping, tmp_path / "anki")
    assert stats["words"] == 2 and stats["files_copied"] == 2
    manifest = json.loads((tmp_path / "anki" / "manifest.json").read_text("utf-8"))
    assert manifest["אֵל"] == [f for f in manifest["אֵל"] if f.endswith("el.mp3")]
    assert (tmp_path / "anki" / manifest["אֵל"][0]).read_bytes() == b"FAKE_MP3_A"
    # Re-run is idempotent: no new copies, same manifest
    stats2 = mod.apply_import(parsed, mapping, tmp_path / "anki")
    assert stats2["files_copied"] == 0


def test_progress_source_migration(tmp_path):
    from web.routes.hebrew import _ensure_hebrew_progress_source
    conn = sqlite3.connect(str(tmp_path / "p.db"))
    conn.execute("""CREATE TABLE hebrew_progress (
        user_id TEXT, node_id TEXT, mastery REAL, attempts INT, correct INT,
        last_practiced TEXT, PRIMARY KEY(user_id,node_id))""")
    conn.execute("INSERT INTO hebrew_progress VALUES ('u','n',0.5,4,3,datetime('now'))")
    _ensure_hebrew_progress_source(conn)
    _ensure_hebrew_progress_source(conn)  # idempotent
    cols = [r[1] for r in conn.execute("PRAGMA table_info(hebrew_progress)").fetchall()]
    assert "source" in cols
    row = conn.execute("SELECT mastery, source FROM hebrew_progress").fetchone()
    assert tuple(row) == (0.5, "practice")
    conn.close()


def test_placement_marks_tested_out_not_mastered(tmp_path):
    from web.routes.hebrew import _placement_apply_results
    conn = sqlite3.connect(str(tmp_path / "h.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY, title TEXT, level INT, category TEXT, description TEXT)")
    conn.execute("""CREATE TABLE hebrew_progress (user_id TEXT, node_id TEXT, mastery REAL,
        attempts INT, correct INT, last_practiced TEXT, PRIMARY KEY(user_id,node_id))""")
    conn.execute("CREATE TABLE hebrew_edges (source_id TEXT, target_id TEXT)")
    conn.execute("CREATE TABLE hebrew_lessons (node_id TEXT, content_json TEXT)")
    conn.executemany("INSERT INTO hebrew_nodes VALUES (?,?,?,?,?)", [
        ("aleph", "Aleph", 1, "consonant", ""),
        ("bet", "Bet", 1, "consonant", ""),
        ("word1", "Word", 4, "word", ""),
    ])

    def skill(level_hist, n=6):
        return {"count": n, "correct": n, "log": [],
                "level_history": level_hist, "reversals": 3, "level": level_hist[-1]}

    results = {
        "alphabet": skill([3, 3, 3, 3, 3, 3]),  # est 3 → test-out level<=2
        "vocab": skill([1, 1, 1, 1, 1, 1]),     # est clamped to 4 → word1 (L4) excluded
        "grammar": skill([1, 1, 1, 1, 1, 1]),
        "reading": skill([1, 1, 1, 1, 1, 1]),
    }
    applied = _placement_apply_results(conn, "u1", results)
    rows = {r[0]: (r[1], r[2])
            for r in conn.execute("SELECT node_id, mastery, source FROM hebrew_progress")}
    assert rows["aleph"] == (0.8, "placement")
    assert rows["bet"] == (0.8, "placement")
    assert "word1" not in rows  # above the test-out margin: untouched
    assert applied["nodes_tested_out"] >= 2
    conn.close()


def test_tts_wordlist_helpers(tmp_path):
    mod = _load_script("generate_word_audio")
    assert mod.clean_pointed("בְּרֵאשִׁ֖ית") == "בְּרֵאשִׁית"  # te'amim stripped, niqqud kept
    assert "בְּ" in mod.clean_pointed("בְּרֵאשִׁית")
    words_file = tmp_path / "words.json"
    words_file.write_text(json.dumps([
        {"id": "w1", "text": "בְּרֵאשִׁ֖ית", "category": "word"},
        {"id": "w2", "text": "  ", "category": "word"},
    ]), encoding="utf-8")
    items = list(mod._iter_wordlist(words_file))
    assert items == [("w1", "w1", "word", "בְּרֵאשִׁית")]
