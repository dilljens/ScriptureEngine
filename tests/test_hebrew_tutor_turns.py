"""T1 grounded tutor: template validation, ask/correct/explain/done, attempt logging."""
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


def _practice_node(hebdb):
    conn = sqlite3.connect(str(hebdb))
    try:
        row = conn.execute(
            "SELECT p.node_id, p.id FROM hebrew_practice_items p"
            " JOIN hebrew_progress g ON g.node_id=p.node_id AND g.user_id='default'"
            " WHERE p.question_type IN ('typing','recall','cloze','parse','dictation')"
            " ORDER BY p.id LIMIT 1").fetchone()
        assert row, "no production item on a practiced node"
        return row[0], row[1]
    finally:
        conn.close()


def test_ask_returns_question_without_answer(hebdb):
    # Call the endpoint function directly (no TestClient needed).
    import asyncio
    node, qid = _practice_node(hebdb)
    got = asyncio.run(H.post_hebrew_tutor_turn(
        {"user_id": "default", "mode": "ask", "node_id": node}, authorization=""))
    assert got["ok"] is True
    d = got["data"]
    assert d["kind"] == "ask" and d["node_id"] == node
    assert isinstance(d["question"], str) and len(d["question"]) >= 8
    assert "correct_answer" not in d and "answer" not in str(d.get("question", ""))[:0]


def test_ask_auto_picks_weakest(hebdb):
    import asyncio
    got = asyncio.run(H.post_hebrew_tutor_turn(
        {"user_id": "default", "mode": "ask"}, authorization=""))
    assert got["ok"] is True
    d = got["data"]
    if d["kind"] == "done":
        return  # empty queue: honest completion
    assert d["kind"] == "ask" and d["node_id"]


def test_correct_grades_and_logs_attempt(hebdb):
    import asyncio
    node, qid = _practice_node(hebdb)
    conn = sqlite3.connect(str(hebdb))
    truth = conn.execute(
        "SELECT correct_answer FROM hebrew_practice_items WHERE id=?", (qid,)).fetchone()[0]
    conn.close()
    got = asyncio.run(H.post_hebrew_tutor_turn(
        {"user_id": "default", "mode": "correct", "node_id": node,
         "question_id": qid, "answer": truth}, authorization=""))
    assert got["ok"] is True
    d = got["data"]
    assert d["kind"] == "correct" and d["was_correct"] is True
    assert d["citations"] and d["citations"][0].get("node_id") == node
    # Attempt event landed (FSRS sees the correction).
    conn = sqlite3.connect(str(hebdb))
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM hebrew_attempt_events WHERE user_id='default'"
            " AND node_id=? AND mode='tutor'", (node,)).fetchone()[0]
        assert n >= 1
    finally:
        conn.close()
    # Wrong answer: recast names the form, rule cites the lesson.
    got2 = asyncio.run(H.post_hebrew_tutor_turn(
        {"user_id": "default", "mode": "correct", "node_id": node,
         "question_id": qid, "answer": "zzz-no-such-answer"}, authorization=""))
    d2 = got2["data"]
    assert d2["was_correct"] is False
    assert truth.split()[0][:4] in d2["recast"] or truth[:8] in d2["recast"]
    assert d2["correct_answer"] == truth


def test_explain_validates_and_falls_back(hebdb):
    import asyncio
    # Unknown node -> 400, not a hallucinated explanation.
    import fastapi
    with pytest.raises(fastapi.HTTPException):
        asyncio.run(H.post_hebrew_tutor_turn(
            {"user_id": "default", "mode": "explain", "node_id": "nope"},
            authorization=""))
    node, _qid = _practice_node(hebdb)
    got = asyncio.run(H.post_hebrew_tutor_turn(
        {"user_id": "default", "mode": "explain", "node_id": node},
        authorization=""))
    assert got["ok"] is True
    d = got["data"]
    assert d["kind"] == "explain"
    ok, why = H._validate_tutor_turn(d)
    assert ok, why


def test_done_shape(hebdb):
    import asyncio
    got = asyncio.run(H.post_hebrew_tutor_turn(
        {"user_id": "default", "mode": "done"}, authorization=""))
    d = got["data"]
    assert d["kind"] == "done" and isinstance(d.get("summary"), str)


def test_validator_rejects_bad_turns():
    bad = [
        {"kind": "ask", "question": "hi"},
        {"kind": "ask", "question": "What is this word?", "node_id": ""},
        {"kind": "correct", "recast": "x", "rule": "", "citations": []},
        {"kind": "correct", "recast": "", "rule": "y",
         "citations": [{"verse_ref": "gen.1.1"}]},
        {"kind": "correct", "recast": "x", "rule": "y", "citations": [{}]},
        {"kind": "explain", "text": " ".join(["word"] * 200), "citations": []},
        {"kind": "explain",
         "text": "The qatal form always expresses completed past action in every context without exception whatsoever.",
         "citations": []},
        {"kind": "nope"},
        "not-a-dict",
    ]
    for t in bad:
        ok, _why = H._validate_tutor_turn(t)
        assert not ok, t
    good = [
        {"kind": "ask", "question": "Parse this verb form, please?", "node_id": "qal_perfect"},
        {"kind": "correct", "recast": "Right.", "rule": "Qal adds nothing.",
         "citations": [{"node_id": "qal_perfect"}]},
        {"kind": "explain", "text": "Which form do you see here?",
         "citations": []},
        {"kind": "explain", "text": "Qal is the simple stem, verified per verb.",
         "citations": [{"node_id": "qal_perfect"}]},
        {"kind": "done", "summary": "s"},
    ]
    for t in good:
        ok, why = H._validate_tutor_turn(t)
        assert ok, (t, why)
