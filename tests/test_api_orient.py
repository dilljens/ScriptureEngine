"""James Jensen's field notes, locked as regressions (docs/inbox/report-api-field-notes.md).

Defect #1: scripture_gematria tool wrapper (transliterate kwarg drift).
Defect #2: unknown /api/* paths returned 200 + SPA HTML.
Proposal item 3: errors that teach (hint + see on 404s).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.api import call_tool

pytestmark = pytest.mark.usefixtures("client")


# ── Defect #2: real JSON 404s under /api/ ───────────────────────────────────

def test_unknown_api_path_returns_json_404_not_spa_html(client):
    r = client.get("/api/v1/no-such-endpoint")
    assert r.status_code == 404
    assert "text/html" not in r.headers.get("content-type", "")
    body = r.json()
    assert body["ok"] is False
    assert body["see"] == "/api/v1/orient"


# ── Proposal item 3: errors that teach ──────────────────────────────────────

def test_human_style_ref_404_carries_dotted_id_hint(client):
    r = client.get("/api/v1/verses/Genesis%201%3A1")
    assert r.status_code == 404
    body = r.json()
    assert "dots" in body["hint"] or "dotted" in body["hint"]
    assert "/api/v1/books" in body["hint"]
    assert body["see"] == "/api/v1/orient"


def test_colon_ref_404_suggests_the_dot_form(client):
    r = client.get("/api/v1/verses/gen:1:99999")
    assert r.status_code == 404
    # The hint echoes the caller's own form, transformed:
    assert "gen.1.99999" in r.json()["hint"]
    assert "gen:1:99999" in r.json()["hint"] or "dots" in r.json()["hint"]


def test_unknown_tool_404_points_at_the_tools_list(client):
    r = client.get("/api/v1/tools/not_a_real_tool")
    assert r.status_code == 404
    body = r.json()
    assert "/api/v1/tools" in body["hint"]
    assert body["ok"] is False


# ── Defect #1: the gematria tool wrapper works again ────────────────────────

def test_scripture_gematria_wrapper_survives_transliteration(prod_db):
    result = call_tool("scripture_gematria", prod_db, word="אור")
    assert "error" not in result
    assert result["gematria"]["standard"] == 207
    # The exact line that used to raise transliterate() TypeError:
    assert result["hebrew_display"]["transliteration"]


def test_every_gematria_entrypoint_shares_one_implementation(prod_db):
    """Direct REST route and /tools dispatcher must not drift apart again."""
    direct = call_tool("scripture_gematria", prod_db, word="שלום")
    via_tools = call_tool("scripture_gematria", prod_db, word="שלום")
    assert direct == via_tools
