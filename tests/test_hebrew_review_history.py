"""Review-history retention: every real rating appends an immutable row."""
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


def _hist(db, user="default", node=None):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        q = "SELECT * FROM hebrew_review_history WHERE user_id=?"
        args: list = [user]
        if node:
            q += " AND node_id=?"
            args.append(node)
        return conn.execute(q + " ORDER BY id", args).fetchall()
    except sqlite3.OperationalError:
        return []  # table created lazily on first recorded review
    finally:
        conn.close()


def test_direct_review_appends_full_state_row(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    out = H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                                  card_mode="forward")
    rows = _hist(hebdb, "default", node)
    assert len(rows) == 1
    h = dict(rows[0])
    assert h["rating"] == 3 and h["card_mode"] == "forward"
    assert h["delta_t"] is None  # first sight: no elapsed time
    assert h["s_before"] is None
    assert h["s_after"] == pytest.approx(out["data"]["stability"], abs=0.01)
    assert h["sf_after"] == pytest.approx(0.8 * h["s_after"])
    assert h["interval_days"] >= 1 and h["desired_retention"] == 0.9
    # Second review records delta_t and before/after.
    H.process_hebrew_review(node_id=node, rating=4, user_id="default",
                            card_mode="forward")
    rows = _hist(hebdb, "default", node)
    assert len(rows) == 2
    assert rows[1]["delta_t"] is not None and rows[1]["delta_t"] >= 0
    assert rows[1]["s_before"] == rows[0]["s_after"]
    assert rows[1]["retrievability"] is not None


def test_lesson_loop_feed_appends_history(hebdb):
    row = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id, id, correct_answer FROM hebrew_practice_items"
        " WHERE question_text LIKE 'Complete the verse%' LIMIT 1").fetchone()
    node_id, qid, truth = row
    before = len(_hist(hebdb, "anon_hist1", node_id))
    H.update_hebrew_progress(
        {"user_id": "anon_hist1", "node_id": node_id,
         "question_id": qid, "answer": truth},
        authorization="")
    after = _hist(hebdb, "anon_hist1", node_id)
    assert len(after) == before + 1
    assert after[-1]["rating"] == 3


def test_undo_removes_matching_history_row(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                            card_mode="forward")
    assert len(_hist(hebdb, "default", node)) == 1
    H.undo_hebrew_review({"user_id": "default", "node_id": node,
                          "card_mode": "forward"}, authorization="")
    assert _hist(hebdb, "default", node) == []


def test_history_endpoint_filters(hebdb):
    node = sqlite3.connect(str(hebdb)).execute(
        "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1").fetchone()[0]
    H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                            card_mode="forward")
    out = H.get_hebrew_history(user_id="default", node_id=node,
                               session_token="", authorization="")
    assert out["ok"] and len(out["data"]["history"]) == 1
    out2 = H.get_hebrew_history(user_id="default", node_id="nope",
                                session_token="", authorization="")
    assert out2["data"]["history"] == []
