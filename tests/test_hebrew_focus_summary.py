"""Grammar-focus + session-summary endpoints (isolated MEM_DB copy)."""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE = Path(__file__).resolve().parent.parent


@pytest.fixture()
def mem_copy(tmp_path):
    dest = tmp_path / "memorize.db"
    shutil.copy(BASE / "data" / "memorize.db", dest)
    return dest


@pytest.fixture()
def H(mem_copy, monkeypatch):
    import web.routes.hebrew as mod
    monkeypatch.setattr(mod, "MEM_DB", mem_copy)
    return mod


def test_grammar_focus_shape(H):
    d = H.get_hebrew_grammar_focus("default", 5, "", "")["data"]
    assert "topics" in d and "blocked_by" in d
    for t in d["topics"]:
        assert {"node_id", "title", "weakness", "is_new"} <= set(t)
    if not d["topics"]:
        assert d["blocked_by"], "empty focus must explain what unlocks grammar"


def test_session_summary_roundtrip(H, mem_copy):
    import sqlite3
    r = H.post_hebrew_session_summary({"user_id": "default"}, "")
    assert r["ok"] is True
    assert r["data"]["memory_key"] == "hebrew_knowledge_state"
    conn = sqlite3.connect(str(mem_copy))
    row = conn.execute(
        "SELECT value FROM tutor_memory WHERE user_id='default' AND key='hebrew_knowledge_state'"
    ).fetchone()
    assert row is not None
    import json
    assert json.loads(row[0])["user_id"] == "default"
    conn.close()


def test_guided_lesson_explicit_node(H):
    import asyncio
    r = asyncio.run(H.post_hebrew_guided_lesson(
        {"user_id": "default", "node_id": "qal_perfect"}, ""))
    assert r["ok"] is True
    d = r["data"]
    assert d["topic"]["node_id"] == "qal_perfect"
    assert d["explanation"], "must have an explanation (curriculum fallback ok)"
    assert isinstance(d["drills"], list) and d["drills"]
    for drill in d["drills"]:
        assert "question_text" in drill and "options" in drill


def test_guided_lesson_auto_empty_state(H):
    import asyncio
    r = asyncio.run(H.post_hebrew_guided_lesson({"user_id": "default"}, ""))
    assert r["ok"] is True
    # Default user hasn't unlocked grammar: expect blocked explanation,
    # or a topic if they have — either way the shape holds.
    assert "topic" in r["data"]
