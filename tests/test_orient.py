"""Orient endpoint: the machine's first-call briefing (docs/inbox/proposal-api-orient.md)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.api import call_tool

pytestmark = pytest.mark.usefixtures("client")


def test_orient_index_is_small_and_actionable(client):
    r = client.get("/api/v1/orient")
    assert r.status_code == 200
    data = r.json()["data"]
    assert "verses" in data["what_this_is"]
    assert len(data["conventions"]) >= 4
    caps = {c["name"] for c in data["capabilities"]}
    assert {"lookup", "guide", "search", "language", "tools"} <= caps
    topic_ids = {t["id"] for t in data["topics"]}
    assert {"refs", "quality", "layers", "limits", "research"} == topic_ids
    # The index must stay an index — every capability names where to start.
    assert all(c["start"].startswith("/") for c in data["capabilities"])
    assert len(r.content) < 16_000  # briefing, not a manual


def test_orient_health_surfaces_degraded_capabilities(client):
    data = client.get("/api/v1/orient").json()["data"]["health"]
    assert "degraded" in data
    for item in data["degraded"]:
        assert item.get("consequence")  # a flag without its cost is useless


def test_every_topic_is_fetchable_and_substantive(client):
    for tid in ("refs", "quality", "layers", "limits", "research"):
        r = client.get(f"/api/v1/orient/{tid}")
        assert r.status_code == 200, tid
        body = r.json()["data"]["markdown"]
        assert len(body) > 400, f"topic too thin: {tid}"


def test_quality_topic_carries_the_money_sentence(client):
    md = client.get("/api/v1/orient/quality").json()["data"]["markdown"]
    assert "algorithmic proposals" in md and "verify" in md.lower()


def test_limits_topic_publishes_the_lxx_gap_and_cloudflare_ua(client):
    md = client.get("/api/v1/orient/limits").json()["data"]["markdown"]
    assert "Septuagint" in md or "LXX" in md
    assert "User-Agent" in md


def test_refs_topic_documents_psalm_versification(client):
    md = client.get("/api/v1/orient/refs").json()["data"]["markdown"]
    assert "KJV" in md and "MT" in md


def test_unknown_topic_is_a_teaching_404(client):
    r = client.get("/api/v1/orient/gematria-magic")
    assert r.status_code == 404
    body = r.json()
    assert "quality" in body["hint"]  # lists the valid topics


def test_health_endpoint_reports_degraded_with_consequences(client):
    data = client.get("/api/v1/health").json()["data"]
    assert isinstance(data["degraded"], list)
    assert all("subsystem" in d and "consequence" in d for d in data["degraded"])


def test_psalms_payload_discloses_dual_versification(client, prod_db):
    # Don't assume a specific psalm exists in the test DB — pick a real one.
    row = prod_db.execute(
        "SELECT id FROM verses WHERE id LIKE 'psa.%' LIMIT 1").fetchone()
    if not row:
        pytest.skip("No psalms in test database")
    data = client.get(f"/api/v1/verses/{row[0]}").json()["data"]
    v = data.get("versification")
    assert v and v["english_scheme"] == "kjv" and v["interlinear_scheme"] == "mt"
    assert "orient/refs" in v["see"]


def test_non_psalms_payload_has_no_versification_note(client):
    data = client.get("/api/v1/verses/gen.1.1").json()["data"]
    assert "versification" not in data


def test_orient_is_discoverable_from_openapi_description(client):
    desc = client.get("/openapi.json").json()["info"]["description"]
    assert "/api/v1/orient" in desc


# ── Field-note regressions (docs/inbox/report-api-field-notes.md) ────────────
# Defect #2: unknown /api/* paths returned 200 + SPA HTML.
# Proposal item 3: errors that teach (hint + see on 404s).

def test_unknown_api_path_returns_json_404_not_spa_html(client):
    r = client.get("/api/v1/no-such-endpoint")
    assert r.status_code == 404
    assert "text/html" not in r.headers.get("content-type", "")
    body = r.json()
    assert body["ok"] is False
    assert body["see"] == "/api/v1/orient"


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


# ── Defect #1: the gematria tool wrapper works again ──────────────────────────

def test_scripture_gematria_wrapper_survives_transliteration(prod_db):
    result = call_tool("scripture_gematria", prod_db, word="אור")
    assert "error" not in result
    assert result["gematria"]["standard"] == 207
    # The exact line that used to raise transliterate() TypeError:
    assert result["hebrew_display"]["transliteration"]
