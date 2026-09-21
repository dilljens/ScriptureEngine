"""P2-B audio_mode + audio_first_commute + analytics (verse side).

Isolated tmp DB; audio availability monkeypatched to test verse ids.
"""
import sqlite3
import sys
from pathlib import Path

import pytest
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes import memorize as M

VERSES = [
    (f"au.1.{i}", "au", 1, i, f"English audio test verse {i}",
     f"Hebrew audio test {i}")
    for i in range(1, 7)
]
ALIGNED = {"au.1.1", "au.1.2", "au.1.3"}


@pytest.fixture()
def memdb(tmp_path, monkeypatch):
    path = tmp_path / "audio.db"
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE verses (
        id TEXT PRIMARY KEY, book_id TEXT, chapter INTEGER, verse INTEGER,
        text_english TEXT, text_hebrew TEXT)""")
    conn.executemany(
        "INSERT INTO verses (id, book_id, chapter, verse, text_english,"
        " text_hebrew) VALUES (?,?,?,?,?,?)", VERSES)
    conn.commit()
    M._ensure_memorize_schema(conn)
    conn.commit()
    conn.close()

    def _fake_conn():
        c = sqlite3.connect(str(path))
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(M, "get_conn", _fake_conn)
    monkeypatch.setattr(M, "_AUDIO_VERSE_IDS", set(ALIGNED))
    return path


def _req():
    return Request({"type": "http", "method": "POST", "headers": []})


def _queue(memdb, verse_id, source="manual"):
    conn = sqlite3.connect(str(memdb))
    conn.row_factory = sqlite3.Row
    M._ensure_memorize_schema(conn)
    qid, _ = M._ensure_queued(conn, "default", verse_id, source)
    conn.commit()
    conn.close()
    return qid


def test_audio_next_only_serves_aligned(memdb):
    for v in ("au.1.1", "au.1.2", "au.1.4", "au.1.5"):
        _queue(memdb, v)
    out = M.get_audio_next(user_id="default", authorization="", limit=10)
    got = {i["verse_id"] for i in out["data"]["items"]}
    assert got == {"au.1.1", "au.1.2"}
    first = out["data"]["items"][0]
    assert first["audio"]["play"].endswith(f"/api/v1/audio/play/{first['verse_id']}")
    assert first["queue_id"] > 0


def test_audio_rating_source_recorded_and_auditable(memdb):
    qid = _queue(memdb, "au.1.1")
    out = M.submit_review(qid, {"user_id": "default", "rating": 3,
                                "source": "audio_mode"}, _req())
    assert out["data"]["rating_source"] == "audio_mode"
    # Queue row keeps its origin; the attempt carries the surface.
    assert out["data"]["source"] == "manual"
    modes = M.get_memorize_analytics(
        user_id="default", authorization="")["data"]["per_mode"]
    audio = next(m for m in modes if m["mode"] == "audio_mode")
    assert audio["ratings"] == 1 and audio["success_rate"] == 1.0


def test_commute_playlist_ends_with_rateable_daily(memdb):
    _queue(memdb, "au.1.1")
    out = M.get_commute_playlist(user_id="default", authorization="",
                                 limit=10, day="2026-09-21")
    stops = out["data"]["stops"]
    assert stops[0]["kind"] == "due" and stops[0]["audio"] is not None
    daily = stops[-1]
    assert daily["kind"] == "daily" and daily["queue_id"] > 0
    # Daily stop rates through the unified submit under commute attribution.
    rated = M.submit_review(daily["queue_id"], {"user_id": "default",
                                                "rating": 4,
                                                "source": "audio_first_commute"},
                            _req())
    assert rated["data"]["rating_source"] == "audio_first_commute"


def test_analytics_shape(memdb):
    qid = _queue(memdb, "au.1.1")
    M.submit_review(qid, {"user_id": "default", "rating": 2}, _req())
    _queue(memdb, "au.1.2")  # unrated → still due
    data = M.get_memorize_analytics(
        user_id="default", authorization="")["data"]
    assert data["retention"]["attempts"] >= 1
    assert 0.0 <= data["retention"]["rate"] <= 1.0
    assert data["retention"]["last_30d"]["ratings"] >= 1
    assert data["due_workload"]["due"] >= 1
    assert any(m["mode"] == "manual" for m in data["per_mode"])
