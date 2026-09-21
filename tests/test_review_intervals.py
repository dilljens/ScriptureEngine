"""Interval-preview endpoints return submit-time truth (memorize + Hebrew).

Both previews must mirror their submit paths exactly: same state lookup,
same speed adjustment, same canonical FSRS core — so the wait on each
button is what tapping it will schedule.
"""

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import web.routes.hebrew as H
import web.routes.memorize as M


def _req():
    return Request({"type": "http", "method": "POST", "headers": []})


@pytest.fixture()
def memdb(tmp_path, monkeypatch):
    path = tmp_path / "m.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE verses (
        id TEXT PRIMARY KEY, book_id TEXT, chapter INTEGER, verse INTEGER,
        text_english TEXT, text_hebrew TEXT)""")
    conn.execute(
        "INSERT INTO verses VALUES ('gen.1.1','gen',1,1,'In the beginning','')")
    M._ensure_memorize_schema(conn)
    conn.commit()
    conn.close()

    def _fake_conn():
        c = sqlite3.connect(str(path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(M, "get_conn", _fake_conn)
    return path


def _queue(memdb, verse_id, user="default"):
    conn = sqlite3.connect(str(memdb))
    conn.row_factory = sqlite3.Row
    M._ensure_memorize_schema(conn)
    qid, _ = M._ensure_queued(conn, user, verse_id, "manual")
    conn.commit()
    conn.close()
    return qid


@pytest.fixture()
def hebrewdb(tmp_path, monkeypatch):
    path = tmp_path / "heb.db"
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY, category TEXT DEFAULT 'vocab')")
    conn.execute("""CREATE TABLE hebrew_progress (user_id TEXT, node_id TEXT,
        attempts INT DEFAULT 0, correct INT DEFAULT 0, mastery REAL DEFAULT 0,
        difficulty REAL DEFAULT 5.0, source TEXT DEFAULT 'practice', last_practiced TEXT)""")
    conn.execute("CREATE TABLE hebrew_lessons (node_id TEXT, content_json TEXT)")
    H._ensure_hebrew_review_state(conn)
    conn.execute("INSERT INTO hebrew_nodes (id) VALUES ('n1')")
    conn.execute("""INSERT INTO hebrew_lessons (node_id, content_json)
        VALUES ('n1', '{"hebrew": "אב", "gloss": "father"}')""")
    conn.commit()
    conn.close()
    monkeypatch.setattr(H, "MEM_DB", path)
    monkeypatch.setattr(H, "_HEBREW_NODE_MAP", {"count": -1, "map": {}})
    monkeypatch.setattr(H, "_SPEED_CACHE", {})
    return path


def test_memorize_intervals_match_submit(memdb):
    """The preview must equal what submit_review will schedule."""
    qid = _queue(memdb, "gen.1.1")
    body = {"user_id": "default", "rating": 3,
            "preview_mode": "fade_words", "preview_level": 50}
    preview = M.preview_intervals(
        qid, "fade_words", 50, "default", "", authorization="")["data"]["intervals"]
    assert set(preview) == {"1", "2", "3", "4"}
    assert all(v["days"] >= 1 and v["label"] for v in preview.values())
    # fade@50 caps Easy(4) to Good(3) — the buttons must show it.
    assert preview["4"]["effective"] == 3
    assert preview["4"]["days"] == preview["3"]["days"]
    # First review (no progress): preview == submit, same inputs.
    out = M.submit_review(qid, body, _req())
    assert out["data"]["interval"] == preview["3"]["days"]
    assert out["data"]["effective_rating"] == preview["3"]["effective"]


def test_memorize_intervals_404(memdb):
    with pytest.raises(HTTPException) as exc:
        M.preview_intervals(999999999, "none", 0, "default", "", authorization="")
    assert exc.value.status_code == 404


def test_hebrew_intervals_by_node_and_word(hebrewdb):
    by_node = H.hebrew_fsrs_intervals("n1", "", user_id="default", authorization="")["data"]["intervals"]
    by_word = H.hebrew_fsrs_intervals(
        hebrew="אב", user_id="default", authorization="")["data"]["intervals"]
    assert set(by_node) == {"1", "2", "3", "4"}
    assert by_node == by_word  # word resolution lands on the same schedule
    assert all(v["days"] >= 1 and v["label"] for v in by_node.values())
    days = [by_node[str(i)]["days"] for i in (1, 2, 3, 4)]
    assert days == sorted(days)


def test_hebrew_intervals_unknown_node_400(hebrewdb):
    with pytest.raises(HTTPException) as exc:
        H.hebrew_fsrs_intervals("nope", "", user_id="default", authorization="")
    assert exc.value.status_code == 400
