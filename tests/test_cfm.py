"""Tests for the Come Follow Me + General Conference corpora tools and routes."""

import datetime
import sqlite3
import time

import pytest

from lib.db import get_db, init_db
from lib.api import call_tool, TOOL_REGISTRY
from web.routes.chat import _filter_tools, _scope_allowed, TOOL_DEFINITIONS


def _exec(conn, sql, params=()):
    """Write with retry — the app's background job sweeper can hold the DB lock."""
    for attempt in range(40):
        try:
            return conn.execute(sql, params)
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 39:
                time.sleep(0.5)
                continue
            raise


@pytest.fixture(scope="module")
def seeded():
    """Seed the CFM/GC tables with two rows each; clean up afterwards."""
    init_db()  # ensure tables exist in whatever DB the tests resolve to
    conn = get_db()
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=1)).isoformat()
    end = (today + datetime.timedelta(days=1)).isoformat()
    rows = [
        ("cfm.2026.03", 2026, "03", "January 12-18", start, end,
         "In the Beginning", "Genesis 1-2; Moses 2-3; Abraham 4-5",
         "God created the heaven and the earth. The atonement and covenant."),
        ("cfm.2026.10", 2026, "10", "March 2-8", "2026-03-02", "2026-03-08",
         "The Abrahamic Covenant", "Genesis 24-33",
         "Abraham received a covenant of blessing."),
    ]
    talks = [
        ("gc.2025.04.13holland", 2025, 4, "Saturday Morning", "Jeffrey R. Holland",
         "As a Little Child", "2025-04-05",
         "Become as a little child. The atonement of Christ redeems us."),
        ("gc.2025.04.57nelson", 2025, 4, "Sunday Afternoon", "Russell M. Nelson",
         "Confidence in the Presence of God", "2025-04-06",
         "Charity and virtue bring confidence before God."),
    ]
    _exec(conn, "DELETE FROM cfm_lessons")
    _exec(conn, "DELETE FROM talks")
    # Seed books + minimal verses so cfm_scripture_blocks can resolve names
    # (the shared test DB has only a few books).
    book_rows = [
        ("moses", "Moses", "ot"), ("abraham", "Abraham", "ot"),
        ("ruth", "Ruth", "ot"), ("1sam", "1 Samuel", "ot"), ("2sam", "2 Samuel", "ot"),
    ]
    for bid, title, wid in book_rows:
        _exec(conn, "INSERT OR IGNORE INTO books (id, title, work_id, position) VALUES (?,?,?,0)",
              (bid, title, wid))
    for ch in range(1, 5):
        _exec(conn, "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?,?,?,?,?)",
              (f"ruth.{ch}.1", "ruth", ch, 1, f"Ruth {ch}:1 test text"))
    for r in rows:
        _exec(conn,
              "INSERT INTO cfm_lessons (ref_id, year, week_slug, date_range, start_date, end_date, title, scripture_block, text) "
              "VALUES (?,?,?,?,?,?,?,?,?)", r)
    for t in talks:
        _exec(conn,
              "INSERT INTO talks (ref_id, year, month, session, speaker, title, date, text) "
              "VALUES (?,?,?,?,?,?,?,?)", t)
    conn.commit()
    yield {"lessons": rows, "talks": talks}
    _exec(conn, "DELETE FROM cfm_lessons")
    _exec(conn, "DELETE FROM talks")
    conn.commit()


def test_tools_registered():
    for name in ("scripture_cfm_lesson", "scripture_conference_talk", "scripture_cfm_search"):
        assert name in TOOL_REGISTRY


def test_cfm_lesson_by_week(seeded):
    conn = get_db()
    r = call_tool("scripture_cfm_lesson", conn, year=2026, week="03")
    assert r["ok"] and r["lesson"]["title"] == "In the Beginning"
    assert "Genesis 1-2" in r["lesson"]["scripture_block"]


def test_cfm_lesson_current_week(seeded):
    conn = get_db()
    r = call_tool("scripture_cfm_lesson", conn, year=2026)
    assert r["ok"] and r["lesson"]["title"] == "In the Beginning"  # seeded with today's range


def test_cfm_lesson_missing(seeded):
    conn = get_db()
    r = call_tool("scripture_cfm_lesson", conn, year=2026, week="99")
    assert not r["ok"] and "error" in r


def test_conference_talk_by_speaker(seeded):
    conn = get_db()
    r = call_tool("scripture_conference_talk", conn, speaker="Holland")
    assert r["ok"] and r["talk"]["speaker"] == "Jeffrey R. Holland"
    assert r["talk"]["title"] == "As a Little Child"


def test_conference_talk_missing(seeded):
    conn = get_db()
    r = call_tool("scripture_conference_talk", conn, speaker="Nobody")
    assert not r["ok"] and "error" in r


def test_cfm_search(seeded):
    conn = get_db()
    r = call_tool("scripture_cfm_search", conn, query="atonement", corpus="both")
    assert r["ok"] and r["count"] >= 1
    corpora = {x["corpus"] for x in r["results"]}
    assert "conference" in corpora  # Holland talk mentions atonement


def test_scope_filtering():
    names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert "scripture_cfm_lesson" in names  # present in the master list

    # No scopes → CFM/GC tools are dropped, canon tools stay
    no_scope = [t["function"]["name"] for t in _filter_tools(TOOL_DEFINITIONS, [], [])]
    assert "scripture_verse" in no_scope
    assert not any("cfm" in n or "conference" in n for n in no_scope)

    # cfm scope → lesson + search in, talk out
    cfm_scope = [t["function"]["name"] for t in _filter_tools(TOOL_DEFINITIONS, ["cfm"], [])]
    assert "scripture_cfm_lesson" in cfm_scope
    assert "scripture_cfm_search" in cfm_scope
    assert "scripture_conference_talk" not in cfm_scope

    # conference scope → talk + search in, lesson out
    gc_scope = [t["function"]["name"] for t in _filter_tools(TOOL_DEFINITIONS, ["conference"], [])]
    assert "scripture_conference_talk" in gc_scope
    assert "scripture_cfm_lesson" not in gc_scope

    # disabled_tools still respected
    disabled = [t["function"]["name"] for t in _filter_tools(TOOL_DEFINITIONS, [], ["scripture_verse"])]
    assert "scripture_verse" not in disabled


def test_scope_allowed():
    assert not _scope_allowed("scripture_cfm_lesson", [])
    assert _scope_allowed("scripture_cfm_lesson", ["cfm"])
    assert not _scope_allowed("scripture_conference_talk", ["cfm"])
    assert _scope_allowed("scripture_cfm_search", ["conference"])  # either scope unlocks
    assert _scope_allowed("scripture_verse", [])  # non-scoped always allowed


def test_library_endpoints(client, seeded):
    r = client.get("/api/v1/cfm/collections")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"]
    assert body["data"]["cfm"]["count"] == 2
    assert body["data"]["conference"]["count"] == 2

    r = client.get("/api/v1/cfm/lessons")
    body = r.json()
    assert body["ok"] and body["data"]["count"] == 2
    titles = {l["title"] for l in body["data"]["lessons"]}
    assert titles == {"In the Beginning", "The Abrahamic Covenant"}

    r = client.get("/api/v1/cfm/lessons/cfm.2026.03")
    body = r.json()
    assert body["ok"] and body["data"]["title"] == "In the Beginning"
    assert len(body["data"]["text"]) > 10

    r = client.get("/api/v1/conference/talks")
    body = r.json()
    assert body["ok"] and body["data"]["count"] == 2
    speakers = {t["speaker"] for t in body["data"]["talks"]}
    assert speakers == {"Jeffrey R. Holland", "Russell M. Nelson"}

    r = client.get("/api/v1/conference/talks/gc.2025.04.13holland")
    body = r.json()
    assert body["ok"] and body["data"]["speaker"] == "Jeffrey R. Holland"

    r = client.get("/api/v1/cfm/lessons/cfm.1999.01")
    assert r.status_code == 404



def _set_block(conn, ref_id, block):
    _exec(conn, "UPDATE cfm_lessons SET scripture_block=? WHERE ref_id=?", (block, ref_id))
    conn.commit()


def test_scripture_block_parser(seeded):
    """Ranges, continuation chapters, book changes."""
    from lib.api.cfm import cfm_scripture_blocks
    conn = get_db()
    _set_block(conn, "cfm.2026.03", "Exodus 19–20; 24; 31–34")
    res = cfm_scripture_blocks(conn, "cfm.2026.03")
    assert res["ok"]
    exo = [b for b in res["blocks"] if b["book_id"] == "exo"][0]
    assert exo["chapters"] == [19, 20, 24, 31, 32, 33, 34]
    assert exo["whole_book"] is False

    _set_block(conn, "cfm.2026.03", "Genesis 1–2; Moses 2–3; Abraham 4–5")
    res = cfm_scripture_blocks(conn, "cfm.2026.03")
    blocks = {b["book_id"]: b["chapters"] for b in res["blocks"]}
    assert blocks["gen"] == [1, 2]
    assert blocks["moses"] == [2, 3]
    assert blocks["abraham"] == [4, 5]


def test_scripture_block_bare_and_abbrev(seeded):
    """Bare books → whole book; '1 Samuel …' with \xa0; abbreviated '102–3'."""
    from lib.api.cfm import cfm_scripture_blocks
    conn = get_db()
    _set_block(conn, "cfm.2026.03", "Ruth; 1\u00a0Samuel 17–18; 24–26; 2\u00a0Samuel 5–7")
    res = cfm_scripture_blocks(conn, "cfm.2026.03")
    ruth = [b for b in res["blocks"] if b["book_id"] == "ruth"][0]
    assert ruth["whole_book"] is True and ruth["chapters"] == [1, 2, 3, 4]
    s1 = [b for b in res["blocks"] if b["book_id"] == "1sam"][0]
    assert s1["chapters"] == [17, 18, 24, 25, 26]
    s2 = [b for b in res["blocks"] if b["book_id"] == "2sam"][0]
    assert s2["chapters"] == [5, 6, 7]

    _set_block(conn, "cfm.2026.03", "Psalms 102–3; 116–19")
    res = cfm_scripture_blocks(conn, "cfm.2026.03")
    psa = [b for b in res["blocks"] if b["book_id"] == "psa"][0]
    assert psa["chapters"] == [102, 103, 116, 117, 118, 119]


def test_scriptures_endpoint(client, seeded):
    _set_block(get_db(), "cfm.2026.03", "Genesis 1–2; Moses 2–3; Abraham 4–5")
    r = client.get("/api/v1/cfm/lessons/cfm.2026.03/scriptures")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["ref_id"] == "cfm.2026.03"
    assert any(b["book_id"] == "gen" and b["chapters"] == [1, 2] for b in data["blocks"])
    assert any(b["book_id"] == "abraham" and b["chapters"] == [4, 5] for b in data["blocks"])
