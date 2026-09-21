"""P2-B daily_maintenance mode: deterministic daily verse + unified FSRS rating.

Uses an isolated tmp DB (same schema via _ensure_memorize_schema) —
never touches production scripture.db.
"""
import datetime
import sqlite3
import sys
from pathlib import Path

import pytest
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes import memorize as M

VERSES = [
    (f"t.1.{i}", "t", 1, i, f"English words of test verse number {i}",
     f"Hebrew test verse {i}")
    for i in range(1, 11)
]


@pytest.fixture()
def memdb(tmp_path, monkeypatch):
    path = tmp_path / "daily.db"
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
    return path


def _req():
    return Request({"type": "http", "method": "POST", "headers": []})


def test_daily_offset_deterministic_in_range():
    a = M.daily_verse_offset("2026-09-21", 10)
    assert a == M.daily_verse_offset("2026-09-21", 10)
    assert 0 <= a < 10
    # A different day almost surely rotates (hash-based, not asserted strictly
    # beyond sanity — the determinism property above is the contract)
    assert 0 <= M.daily_verse_offset("2026-09-22", 10) < 10


def test_daily_enqueues_source_tagged_item(memdb):
    first = M.get_daily_verse(user_id="default", authorization="", day="2026-09-21")
    assert first["ok"] and first["data"]["date"] == "2026-09-21"
    assert first["data"]["source"] == "daily_maintenance"
    assert first["data"]["queue_id"] > 0
    # Idempotent: same day+user reuses the queue row
    second = M.get_daily_verse(user_id="default", authorization="", day="2026-09-21")
    assert second["data"]["queue_id"] == first["data"]["queue_id"]
    assert second["data"]["verse"]["id"] == first["data"]["verse"]["id"]


def test_daily_rating_flows_through_unified_submit(memdb):
    daily = M.get_daily_verse(user_id="default", authorization="", day="2026-09-21")
    qid = daily["data"]["queue_id"]
    out = M.submit_review(qid, {"user_id": "default", "rating": 3}, _req())
    assert out["ok"]
    assert out["data"]["source"] == "daily_maintenance"
    assert out["data"]["effective_rating"] == 3
    assert out["data"]["interval"] >= 1
    # Auditable: review GET surfaces the source tag
    reviews = M.get_due_reviews(user_id="default", authorization="")["data"]["reviews"]
    tagged = [r for r in reviews if r["queue_id"] == qid]
    assert tagged and tagged[0]["source"] == "daily_maintenance"


def test_modes_lists_daily_available_with_live_totals(memdb):
    M.get_daily_verse(user_id="default", authorization="", day="2026-09-21")
    modes = M.list_memorize_modes()["data"]["modes"]
    daily = next(m for m in modes if m["id"] == "daily_maintenance")
    assert daily["status"] == "available"
    assert daily["surface"] == "/api/v1/memorize/daily"
    totals = M.list_memorize_modes()["data"]["totals"]
    assert totals["scripture_queued"] == 1


def test_bad_day_falls_back_to_today(memdb):
    out = M.get_daily_verse(user_id="default", authorization="", day="not-a-date")
    # Server-local day is the contract (a "daily" verse follows the server).
    today = datetime.date.today().isoformat()  # noqa: DTZ011
    assert out["data"]["date"] == today
