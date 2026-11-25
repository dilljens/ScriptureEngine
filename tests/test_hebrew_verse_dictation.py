"""Verse-level dictation (R3-verse): gloss-cued target in verse audio."""
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes import hebrew as H

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def hebdb(tmp_path, monkeypatch):
    src = ROOT / "data" / "memorize.db"
    if not src.exists():
        pytest.skip("Hebrew database not found")
    isolated = tmp_path / "memorize.db"
    shutil.copy2(src, isolated)
    monkeypatch.setattr(H, "MEM_DB", isolated)
    return isolated


def _seeded(db):
    return sqlite3.connect(str(db)).execute(
        "SELECT COUNT(*) FROM hebrew_practice_items"
        " WHERE question_type='dictation' AND question_text LIKE '🎧 Verse dictation%'"
    ).fetchone()[0]


def _ensure_seeded(db):
    """Seed verse-dictation rows into the isolated copy via the real seeder."""
    import runpy
    import sys as _sys
    saved = list(_sys.argv)
    _sys.argv = ["seed_verse_dictation", "--apply", "--count", "300", "--db", str(db)]
    try:
        runpy.run_path(str(ROOT / "scripts" / "seed_verse_dictation.py"),
                       run_name="__main__")
    except SystemExit as e:
        assert e.code in (0, None), e.code
    finally:
        _sys.argv = saved


def test_converter_routes_verse_audio(hebdb):
    row = sqlite3.connect(str(hebdb)).execute(
        "SELECT id, node_id, question_type, question_text, options_json, correct_answer, difficulty"
        " FROM hebrew_practice_items WHERE question_type='dictation'"
        " AND question_text LIKE '🎧 Verse dictation%' LIMIT 1").fetchone()
    if not row:
        pytest.skip("verse dictation not seeded in fixture DB")
    import sqlite3 as _s
    conn = _s.connect(str(hebdb))
    conn.row_factory = _s.Row
    try:
        node = conn.execute(
            "SELECT id, title, category FROM hebrew_nodes WHERE id=?",
            (row[1],)).fetchone()
        assert node is not None
        item = {k: row[i] for i, k in enumerate(
            ["id", "node_id", "question_type", "question_text",
             "options_json", "correct_answer", "difficulty"])}
        q = H._practice_to_quiz_question(item, dict(node))
    finally:
        conn.close()
    assert q["type"] == "dictation"
    assert q["answer_mode"] == H.ANSWER_MODE_FREE_TEXT  # never MC
    assert q.get("audio_url", "").startswith("/api/v1/audio/play/")
    # audio_url must name the same verse the question names
    import re
    m = re.search(r"\(([a-z0-9]+\.\d+\.\d+)\)", q["question"])
    assert m and m.group(1) in q["audio_url"], q


def test_verse_dictation_next_gated_without_history(hebdb):
    out = H.get_verse_dictation_next(user_id="default", limit=5,
                                     session_token="", authorization="")
    assert out["ok"] is True
    d = out["data"]
    # No word-dictation history in a fresh copy: ungated (None), not blocked.
    assert d["word_retention"] is None
    assert d["gated"] is False
    assert isinstance(d["cards"], list)
    if d["cards"]:
        c0 = d["cards"][0]
        assert c0.get("gloss"), "cards must carry the gloss cue"
        assert (c0.get("audio_url") or "").startswith("/api/v1/audio/play/")
        # The gloss is grounded: it matches the lesson's own gloss.
        import sqlite3 as _s
        conn = _s.connect(str(hebdb))
        try:
            import json as _j
            cj = conn.execute(
                "SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                (c0["node_id"],)).fetchone()[0]
            assert c0["gloss"] == (_j.loads(cj or "{}").get("gloss") or "")
        finally:
            conn.close()


def test_lesson_quiz_serves_verse_dictation_typed(hebdb):
    # Day-rotation dedups same-answer production items (word + verse cards
    # share a skeleton), so convert the verse item directly — same code
    # path the quiz uses — instead of depending on today's hash pick.
    conn = sqlite3.connect(str(hebdb))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM hebrew_practice_items"
            " WHERE question_type='dictation' AND question_text LIKE '🎧 Verse dictation%'"
            " LIMIT 1").fetchone()
        assert row, "verse dictation must be seeded"
        node = conn.execute(
            "SELECT id, title, category FROM hebrew_nodes WHERE id=?",
            (row["node_id"],)).fetchone()
        q = H._practice_to_quiz_question(dict(row), dict(node))
    finally:
        conn.close()
    assert q["type"] == "dictation"
    assert q["answer_mode"] == H.ANSWER_MODE_FREE_TEXT, q
    assert (q.get("audio_url") or "").startswith("/api/v1/audio/play/"), q
    # Grades identically to the word card (same skeleton convention).
    out = H.update_hebrew_progress(
        {"user_id": "default", "node_id": row["node_id"],
         "question_id": row["id"], "answer": row["correct_answer"]},
        authorization="")
    assert out["ok"] is True and out["data"]["correct"]


def test_word_retention_gate_trips_on_failures(hebdb):
    # Simulate: enough word-dictation failures to drop below 80%.
    conn = sqlite3.connect(str(hebdb))
    rows = conn.execute(
        "SELECT id, node_id FROM hebrew_practice_items"
        " WHERE question_type='dictation' AND question_text NOT LIKE '🎧 Verse dictation%'"
        " LIMIT 10").fetchall()
    assert rows, "need word-level dictation items"
    for i, (qid, nid) in enumerate(rows):
        H._record_attempt_event(conn, "default", nid, qid, "wrong",
                                i < 2, mode="hebrew")  # 2/10 correct
    conn.commit()
    got = H._word_dictation_retention(conn, "default")
    conn.close()
    assert got == pytest.approx(0.2)
    out = H.get_verse_dictation_next(user_id="default", limit=5,
                                     session_token="", authorization="")
    assert out["data"]["gated"] is True
    assert out["data"]["cards"] == []
    assert out["data"]["word_retention"] == pytest.approx(0.2)
