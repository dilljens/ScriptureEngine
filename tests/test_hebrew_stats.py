"""B3: retention & forecast stats reconcile with the queue."""
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


def test_stats_shape_and_forecast_reconciles(hebdb):
    out = H.get_hebrew_stats(user_id="default", session_token="", authorization="")
    assert out["ok"] is True
    d = out["data"]
    assert len(d["forecast"]) == 31
    assert len(d["heatmap"]) == 30
    assert set(d["retention"]) == {"by_mode_30d", "overall_30d", "fsrs_lifetime_by_mode"}
    # Day-0 reconciles with a direct due-count query (same filter).
    conn = sqlite3.connect(str(hebdb))
    direct = conn.execute(
        "SELECT COUNT(*) FROM hebrew_review_state"
        " WHERE user_id='default' AND due <= datetime('now','localtime')").fetchone()[0]
    conn.close()
    assert d["forecast"][0]["due"] == direct


def test_stats_excludes_suspended_from_forecast(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id FROM hebrew_review_state WHERE user_id='default'"
        " AND due <= datetime('now','localtime') LIMIT 1").fetchone()
    if not node:
        pytest.skip("no due rows to suspend")
    nid = node[0]
    H.suspend_hebrew_card({"user_id": "default", "node_id": nid, "card_mode": ""},
                          authorization="")
    out = H.get_hebrew_stats(user_id="default", session_token="", authorization="")
    d = out["data"]
    assert d["suspended_count"] >= 1
    conn = sqlite3.connect(str(hebdb))
    direct = conn.execute(
        """SELECT COUNT(*) FROM hebrew_review_state s
           WHERE s.user_id='default' AND s.due <= datetime('now','localtime')
           AND NOT EXISTS (SELECT 1 FROM hebrew_suspended x
             WHERE x.user_id='default' AND x.node_id=s.node_id AND x.card_mode IN ('', s.card_mode))"""
    ).fetchone()[0]
    conn.close()
    assert d["forecast"][0]["due"] == direct
    H.unsuspend_hebrew_card({"user_id": "default", "node_id": nid, "card_mode": ""},
                            authorization="")
