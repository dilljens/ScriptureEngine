"""Acceptance tests for the external audit inbox batch (James Jensen, Aug-Sep 2026).

Each test pins one reported item: unauthenticated writes, catalog/content
agreement, D&C reference shapes, unified error envelopes, tool-param 422s,
the ?layer= filter, chapter guides, and versification disclosure.
"""
import json

import pytest

from lib.api.refs import (
    format_reference,
    normalize_ref,
    versification_block,
    versification_offset,
)


# ── lib/api/refs.py: pure unit tests (no DB) ─────────────────────────────

def test_dc_short_forms_expand_to_canonical():
    assert normalize_ref("dc121.7") == "dc121.121.7"
    assert normalize_ref("dc.121.7") == "dc121.121.7"
    assert normalize_ref("D&C.121.7") == "dc121.121.7"
    assert normalize_ref("dc121") == "dc121.121"
    assert normalize_ref("dc.121") == "dc121.121"
    # dc1.1 is ambiguous: verse routes read the verse, chapter routes the chapter.
    assert normalize_ref("dc1.1") == "dc1.1.1"
    assert normalize_ref("dc1.1", expect="chapter") == "dc1.1"


def test_dc_canonical_and_others_untouched():
    assert normalize_ref("dc121.121.7") == "dc121.121.7"
    assert normalize_ref("dc121.1.7") == "dc121.1.7"  # invalid stays invalid
    assert normalize_ref("gen.1.1") == "gen.1.1"
    assert normalize_ref("psa.23") == "psa.23"
    assert normalize_ref("") == ""


def test_dc_reference_display_drops_the_repeat():
    assert format_reference("Doctrine and Covenants 121", "dc121.121.7", 121, 7) == \
        "Doctrine and Covenants 121:7"
    assert format_reference("Genesis", "gen.1.1", 1, 1) == "Genesis 1:1"


def test_measured_versification_offsets():
    assert versification_offset("psa", 51) == 2
    assert versification_offset("psa", 50) == 0
    assert versification_offset("psa", 69) == 1
    assert versification_offset("jonah", 1) == -1
    assert versification_offset("jonah", 2) == 1
    assert versification_offset("psa", 999) is None  # unmeasured, never guessed
    assert versification_offset("gen", 1) is None


def test_versification_block_names_the_number_or_says_unmeasured():
    assert versification_block("psa", 51)["offset"] == 2
    assert "unmeasured" in versification_block("psa", 23)["note"].lower() \
        or "verify" in versification_block("psa", 23)["note"].lower()
    assert versification_block("gen", 1) is None


# ── Unauthenticated writes: 401s and server-side authorship ──────────────

def test_debug_log_rejects_anonymous(client):
    r = client.post("/api/v1/debug/log", json={"level": "error", "message": "x" * 5000})
    assert r.status_code == 401


def test_debug_log_accepts_session_and_truncates(client):
    from web.routes import auth
    token = auth._generate_session_token("log-user")
    big = "y" * 9000
    r = client.post("/api/v1/debug/log", json={"session_token": token, "message": big})
    assert r.status_code == 200
    import sqlite3
    from lib.db import DEFAULT_DB_PATH
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    try:
        row = conn.execute(
            "SELECT message FROM client_logs WHERE message LIKE 'yyyy%' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None and len(row[0]) <= 2000


def test_debug_logs_rejects_anonymous(client):
    assert client.get("/api/v1/debug/logs").status_code == 401


def test_forum_post_ignores_forged_author(client):
    import sqlite3
    from lib.db import DEFAULT_DB_PATH
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    try:
        conn.execute(
            "INSERT OR IGNORE INTO forum_topics (id, title, slug) VALUES (4242, 't', 't-4242')"
        )
        conn.commit()
    finally:
        conn.close()
    r = client.post("/api/v1/forum/posts", params={"user_id": "alice"},
                    json={"topic_id": 4242, "content": "hi", "author": "mallory"})
    assert r.status_code == 200
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    try:
        row = conn.execute(
            "SELECT author FROM forum_posts WHERE topic_id=4242 ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        conn.execute("DELETE FROM forum_posts WHERE topic_id=4242")
        conn.execute("DELETE FROM forum_topics WHERE id=4242")
        conn.commit()
    finally:
        conn.close()
    assert row is not None and row[0] == "alice"


# ── Catalog/content agreement ────────────────────────────────────────────

def test_books_carry_availability_matching_content(client):
    data = client.get("/api/v1/books").json()["data"]
    works = data["works"] if isinstance(data, dict) else data
    seen = 0
    for w in works:
        for b in w["books"]:
            seen += 1
            assert isinstance(b["verses"], int)
            assert b["available"] == (b["verses"] > 0), b["id"]
    assert seen > 0


# ── D&C shapes, end to end ───────────────────────────────────────────────

def test_dc_alias_resolves_and_displays_once(client):
    r = client.get("/api/v1/verses/dc1.1")
    assert r.status_code == 200
    ref = r.json()["data"]["reference"]
    assert ref == "D&C Section 1:1"  # fixture title; the point is no doubled number
    assert "1:1:1" not in ref and "1 1:" not in ref


def test_dc_chapter_short_form(client):
    assert client.get("/api/v1/chapter/dc1").status_code == 200


# ── One error envelope everywhere ────────────────────────────────────────

def test_chapter_404_teaches(client):
    r = client.get("/api/v1/chapter/zzz.999")
    assert r.status_code == 404
    body = r.json()
    assert body["ok"] is False and "hint" in body and body["see"] == "/api/v1/orient"


def test_book_summary_404_teaches(client):
    r = client.get("/api/v1/book/nope-not-a-book/connection-summary")
    assert r.status_code == 404
    body = r.json()
    assert body["ok"] is False and "hint" in body and body["see"] == "/api/v1/orient"


def test_tool_missing_param_is_422_not_500(client):
    r = client.post("/api/v1/tools/scripture_batch_lookup", json={})
    assert r.status_code == 422
    assert "verses" in r.json()["detail"]
    r = client.get("/api/v1/tools/scripture_batch_lookup")
    assert r.status_code == 422


# ── ?layer= filter + chapter guides ──────────────────────────────────────

def _seed_guide(monkeypatch):
    import web.server as server
    guide = {
        "connections_json": json.dumps({
            "sod": [{"type": "x", "target": "john.1.1"}],
            "intertextual": [{"type": "y", "target": "gen.1.1"}],
        }),
        "total_connections": 2,
        "layer_count": 2,
    }
    monkeypatch.setattr(server, "GUIDE_CACHE", {"gen.1.1": guide})


def test_guide_layer_filter(client, monkeypatch):
    _seed_guide(monkeypatch)
    r = client.get("/api/v1/verses/gen.1.1/guide", params={"layer": "sod"})
    assert r.status_code == 200
    conns = r.json()["data"]["connections"]
    assert set(conns) == {"sod"}
    r = client.get("/api/v1/verses/gen.1.1/guide", params={"layer": "bogus"})
    assert r.status_code == 400


def test_chapter_guides_batch(client):
    r = client.get("/api/v1/chapter/gen.1/guides")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["verses"] >= 1
    assert all("verse" in g for g in data["guides"])
    r = client.get("/api/v1/chapter/zzz.999/guides")
    assert r.status_code == 404


# ── Versification on the payload ─────────────────────────────────────────

def test_verse_payload_carries_measured_or_honest_block(client):
    r = client.get("/api/v1/verses/psa.23.1")
    assert r.status_code == 200
    block = r.json()["data"].get("versification")
    assert block is not None and block["interlinear_scheme"] == "mt"
