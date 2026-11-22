"""B2: undo-last-review (single step) + suspend/unsuspend.

Isolated tmp COPY of the real memorize.db; writes never touch production.
"""
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


def _rows(db, sql, args=()):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(sql, args).fetchall()
    finally:
        conn.close()


def _state(db, node, mode=""):
    r = _rows(db, "SELECT stability,difficulty,due,last_review,last_rating,reps,lapses"
                  " FROM hebrew_review_state WHERE user_id='default' AND node_id=? AND card_mode=?",
              (node, mode))
    return tuple(r[0]) if r else None


def _prog(db, node):
    r = _rows(db, "SELECT mastery,attempts,correct FROM hebrew_progress"
                  " WHERE user_id='default' AND node_id=?", (node,))
    return tuple(r[0]) if r else None


def test_review_undo_restores_exact_state(tmp_path, hebdb):
    node = _rows(hebdb, "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1")[0][0]
    before_state = _state(hebdb, node, "forward")
    before_prog = _prog(hebdb, node)
    H.process_hebrew_review(node_id=node, rating=4, user_id="default", card_mode="forward")
    assert _state(hebdb, node, "forward") != before_state
    out = H.undo_hebrew_review({"user_id": "default", "node_id": node, "card_mode": "forward"}, authorization="")
    assert out["ok"] is True
    assert _state(hebdb, node, "forward") == before_state
    assert _prog(hebdb, node) == before_prog
    # Single step is consumed: second undo 404s.
    with pytest.raises(Exception):
        H.undo_hebrew_review({"user_id": "default", "node_id": node, "card_mode": "forward"}, authorization="")


def test_undo_new_card_removes_rows(tmp_path, hebdb):
    # Pick a node with no review_state row yet for this mode.
    node = _rows(hebdb, """SELECT n.id FROM hebrew_nodes n
        WHERE NOT EXISTS (SELECT 1 FROM hebrew_review_state s
          WHERE s.user_id='default' AND s.node_id=n.id AND s.card_mode='visual_only')
        LIMIT 1""")[0][0]
    assert _state(hebdb, node, "visual_only") is None
    H.process_hebrew_review(node_id=node, rating=3, user_id="default", card_mode="visual_only")
    assert _state(hebdb, node, "visual_only") is not None
    out = H.undo_hebrew_review({"user_id": "default", "node_id": node, "card_mode": "visual_only"}, authorization="")
    assert out["ok"] is True and out["data"]["restored_new_card"] is True
    assert _state(hebdb, node, "visual_only") is None


def test_suspend_hides_from_queue_and_unsuspend_restores(tmp_path, hebdb):
    node = _rows(hebdb, "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1")[0][0]
    H.process_hebrew_review(node_id=node, rating=2, user_id="default", card_mode="forward")
    conn = sqlite3.connect(str(hebdb))
    conn.execute("UPDATE hebrew_review_state SET due='2000-01-01'"
                 " WHERE user_id='default' AND node_id=? AND card_mode='forward'", (node,))
    conn.commit()
    conn.close()
    def _contains(q, nid):
        for r in q["data"]["reviews"]:
            if r.get("node_id") == nid:
                return True
            if r.get("primary_node_id") == nid:
                return True
            for it in (r.get("items") or []):
                if it.get("node_id") == nid:
                    return True
        return False
    q1 = H.get_hebrew_review_queue(user_id="default", authorization="", limit=200)
    assert q1["ok"] and _contains(q1, node)
    # Suspend just the forward direction: node stays but forward is gone.
    H.suspend_hebrew_card({"user_id": "default", "node_id": node, "card_mode": "forward"}, authorization="")
    q2 = H.get_hebrew_review_queue(user_id="default", authorization="", limit=200)
    fwd = [r for r in q2["data"]["reviews"] if r.get("node_id") == node]
    assert all("forward" not in (r.get("due_modes") or []) for r in fwd)
    listed = H.list_hebrew_suspended(user_id="default", authorization="")
    assert any(s["node_id"] == node for s in listed["data"]["suspended"])
    # Suspend whole node: disappears entirely.
    H.suspend_hebrew_card({"user_id": "default", "node_id": node, "card_mode": ""}, authorization="")
    q3 = H.get_hebrew_review_queue(user_id="default", authorization="", limit=200)
    assert not _contains(q3, node)
    # Unsuspend both: back in queue.
    H.unsuspend_hebrew_card({"user_id": "default", "node_id": node, "card_mode": "forward"}, authorization="")
    H.unsuspend_hebrew_card({"user_id": "default", "node_id": node, "card_mode": ""}, authorization="")
    q4 = H.get_hebrew_review_queue(user_id="default", authorization="", limit=200)
    assert _contains(q4, node)
