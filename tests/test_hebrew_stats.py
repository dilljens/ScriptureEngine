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


def test_profile_shape_and_goal_roundtrip(hebdb):
    out = H.get_hebrew_profile(user_id="default", session_token="", authorization="")
    assert out["ok"] is True
    d = out["data"]
    assert d["frontier_level"] >= 1
    assert isinstance(d["skills"], list) and d["skills"]
    assert set(d["pacing"]) == {"new_cards_per_day", "max_reviews_per_day", "desired_retention"}
    assert d["goal_choices"] == ["read", "vocab", "parse", "fluency"]
    sk = d["skills"][0]
    assert {"category", "practiced", "avg_mastery", "mastered", "due"} <= set(sk)
    # Goal round-trips through prefs; junk is rejected.
    r = H.set_hebrew_prefs({"user_id": "default", "goal": "read",
                            "new_cards_per_day": 10, "max_reviews_per_day": 100},
                           authorization="")
    assert r["ok"] and r["data"]["goal"] == "read"
    d2 = H.get_hebrew_profile(user_id="default", session_token="", authorization="")["data"]
    assert d2["goal"] == "read"
    import fastapi
    with pytest.raises(fastapi.HTTPException):
        H.set_hebrew_prefs({"user_id": "default", "goal": "bogus"}, authorization="")


def test_today_counts_review_vs_new_and_undo(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT n.id FROM hebrew_nodes n WHERE NOT EXISTS (SELECT 1 FROM hebrew_review_state"
        " WHERE user_id='default' AND node_id=n.id) LIMIT 1").fetchone()[0]
    # Fresh card rated twice (Again then Good): introduced today, not a review.
    H.process_hebrew_review(node_id=node, rating=1, user_id="default",
                            card_mode="forward")
    H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                            card_mode="forward")
    q = H.get_hebrew_review_queue(user_id="default", authorization="", limit=50)
    assert q["data"]["new_introduced_today"] == 1, q["data"]
    assert q["data"]["reviews_done_today"] == 0, q["data"]
    # An older card (progress from yesterday) counts as reviewed.
    old = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1 OFFSET 5").fetchone()[0]
    conn = sqlite3.connect(str(hebdb))
    conn.execute(
        "INSERT OR REPLACE INTO hebrew_progress (user_id, node_id, mastery, attempts, correct, last_practiced)"
        " VALUES ('default', ?, 0.5, 3, 2, date('now','-1 day'))", (old,))
    conn.execute(
        "INSERT OR REPLACE INTO hebrew_review_state"
        " (user_id, node_id, card_mode, stability, difficulty, due, last_review, reps, lapses)"
        " VALUES ('default', ?, 'forward', 2.0, 5.0, date('now','-1 day'), date('now','-1 day'), 3, 0)",
        (old,))
    conn.commit()
    conn.close()
    H.process_hebrew_review(node_id=old, rating=3, user_id="default",
                            card_mode="forward")
    q2 = H.get_hebrew_review_queue(user_id="default", authorization="", limit=50)
    assert q2["data"]["reviews_done_today"] == 1, q2["data"]
    assert q2["data"]["new_introduced_today"] == 1, q2["data"]
    # Undo the last rating: the count drops back (net counts).
    H.undo_hebrew_review({"user_id": "default", "node_id": old,
                          "card_mode": "forward"}, authorization="")
    q3 = H.get_hebrew_review_queue(user_id="default", authorization="", limit=50)
    assert q3["data"]["reviews_done_today"] == 0, q3["data"]
    assert q3["data"]["new_introduced_today"] == 1, q3["data"]
