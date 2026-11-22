"""L1 intraday learning: Again returns this session (10m relearn + 20m learn-ahead)."""
import datetime
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


def test_again_reschedules_intraday(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    out = H.process_hebrew_review(node_id=node, rating=4, user_id="default",
                                  card_mode="forward")
    assert out["data"]["is_relearn"] is False
    # Established-card lapse jumps to step 2 (+10m, Anki relearn default).
    out = H.process_hebrew_review(node_id=node, rating=1, user_id="default",
                                  card_mode="forward")
    d = out["data"]
    assert d["is_relearn"] is True
    assert d["relearn_in_min"] == 10
    assert d["interval"] == 0
    assert d["lapses"] >= 1
    due = datetime.datetime.strptime(d["due"], "%Y-%m-%d %H:%M:%S")
    delta_min = (due - datetime.datetime.now()).total_seconds() / 60
    assert 8 <= delta_min <= 11, delta_min


def test_two_step_machine(hebdb):
    # New-card Again lands on step 1 (+1m); Good advances to step 2 (+10m);
    # Good on step 2 graduates; Again anywhere in learning resets to step 1.
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT n.id FROM hebrew_nodes n WHERE NOT EXISTS (SELECT 1"
        " FROM hebrew_review_state s WHERE s.node_id=n.id) LIMIT 1").fetchone()
    assert node, "need a never-reviewed node"
    nid = node[0]
    d1 = H.process_hebrew_review(node_id=nid, rating=1, user_id="anon_step1",
                                 card_mode="forward")["data"]
    assert d1["is_relearn"] and d1["relearn_in_min"] == 1
    step = sqlite3.connect(str(hebdb)).execute(
        "SELECT learn_step FROM hebrew_review_state"
        " WHERE user_id='anon_step1' AND node_id=? AND card_mode='forward'",
        (nid,)).fetchone()[0]
    assert step == 1
    d2 = H.process_hebrew_review(node_id=nid, rating=3, user_id="anon_step1",
                                 card_mode="forward")["data"]
    assert d2["is_relearn"] and d2["relearn_in_min"] == 10
    d3 = H.process_hebrew_review(node_id=nid, rating=1, user_id="anon_step1",
                                 card_mode="forward")["data"]
    assert d3["is_relearn"] and d3["relearn_in_min"] == 1
    d4 = H.process_hebrew_review(node_id=nid, rating=3, user_id="anon_step1",
                                 card_mode="forward")["data"]
    assert d4["is_relearn"] and d4["relearn_in_min"] == 10
    d5 = H.process_hebrew_review(node_id=nid, rating=3, user_id="anon_step1",
                                 card_mode="forward")["data"]
    assert d5["is_relearn"] is False and d5["interval"] >= 1


def test_good_after_again_graduates_to_days(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    # Fresh-card Again -> step 1; Good advances to step 2 (still intraday).
    H.process_hebrew_review(node_id=node, rating=1, user_id="default",
                            card_mode="forward")
    mid = H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                                  card_mode="forward")
    assert mid["data"]["is_relearn"] is True
    assert mid["data"]["relearn_in_min"] == 10
    # Good on step 2 graduates to day-scale.
    out = H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                                  card_mode="forward")
    assert out["data"]["is_relearn"] is False
    assert out["data"]["interval"] >= 1
    due = datetime.datetime.strptime(out["data"]["due"], "%Y-%m-%d %H:%M:%S")
    assert (due - datetime.datetime.now()).total_seconds() > 20 * 60


def test_queue_serves_learn_ahead_with_flag(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    H.process_hebrew_review(node_id=node, rating=1, user_id="default",
                            card_mode="forward")
    q = H.get_hebrew_review_queue(user_id="default", authorization="", limit=200)
    assert q["ok"]
    mine = []
    for r in q["data"]["reviews"]:
        if r.get("node_id") == node:
            mine.append(r)
        elif r.get("primary_node_id") == node or any(
                it.get("node_id") == node for it in (r.get("items") or [])):
            # Compressed groups carry the flag on members when present.
            mine.extend([it for it in (r.get("items") or [])
                         if it.get("node_id") == node] or [r])
    assert mine, "relearn card must stay in queue via learn-ahead"
    assert any(m.get("is_learning") for m in mine)


def test_preview_again_shows_intraday_label(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    out = H.hebrew_fsrs_intervals(node_id=node, card_mode="forward",
                                  user_id="default", authorization="")
    iv = out["data"]["intervals"]
    # Fresh/learning cards return in 1m; established lapses in 10m.
    assert iv["1"]["days"] == 0 and iv["1"]["label"] == "<1m"
    assert all(iv[r]["days"] >= 1 for r in ("2", "3", "4"))
    H.process_hebrew_review(node_id=node, rating=4, user_id="default",
                            card_mode="forward")
    iv2 = H.hebrew_fsrs_intervals(node_id=node, card_mode="forward",
                                  user_id="default", authorization="")["data"]["intervals"]
    assert iv2["1"] == {"days": 0, "label": "<10m"}


def test_undo_restores_pre_relearn_due(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    H.process_hebrew_review(node_id=node, rating=4, user_id="default",
                            card_mode="forward")
    before = sqlite3.connect(str(hebdb)).execute(
        "SELECT due FROM hebrew_review_state WHERE user_id='default'"
        " AND node_id=? AND card_mode='forward'", (node,)).fetchone()[0]
    H.process_hebrew_review(node_id=node, rating=1, user_id="default",
                            card_mode="forward")
    H.undo_hebrew_review({"user_id": "default", "node_id": node,
                          "card_mode": "forward"}, authorization="")
    after = sqlite3.connect(str(hebdb)).execute(
        "SELECT due FROM hebrew_review_state WHERE user_id='default'"
        " AND node_id=? AND card_mode='forward'", (node,)).fetchone()[0]
    assert after == before
