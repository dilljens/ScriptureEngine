"""Level-gated frontier: L(n+1) opens at practiced-average mastery >= 0.5 on L(n)."""
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


def _seed(conn, user, rows):
    for node_id, mastery in rows:
        conn.execute(
            "INSERT OR REPLACE INTO hebrew_progress (user_id, node_id, mastery, attempts, correct)"
            " VALUES (?,?,?,?,?)",
            (user, node_id, mastery, 10, int(10 * mastery)))
    conn.commit()


def _l1_nodes(db, n=5):
    conn = sqlite3.connect(str(db))
    try:
        return [r[0] for r in conn.execute(
            "SELECT id FROM hebrew_nodes WHERE level=1 LIMIT ?", (n,)).fetchall()]
    finally:
        conn.close()


def test_fresh_user_gated_to_level_1(hebdb):
    conn = sqlite3.connect(str(hebdb))
    assert H._max_frontier_level(conn, "anon_gate0") == 1
    conn.close()


def test_gate_opens_with_mastery(hebdb):
    conn = sqlite3.connect(str(hebdb))
    try:
        l1 = _l1_nodes(hebdb, 3)
        _seed(conn, "anon_gate1", [(nid, 0.4) for nid in l1])
        assert H._max_frontier_level(conn, "anon_gate1") == 1
        _seed(conn, "anon_gate2", [(nid, 0.9) for nid in l1])
        assert H._max_frontier_level(conn, "anon_gate2") == 2
    finally:
        conn.close()


def test_gate_never_locks_below_touched_levels(hebdb):
    conn = sqlite3.connect(str(hebdb))
    try:
        l5 = conn.execute("SELECT id FROM hebrew_nodes WHERE level=5 LIMIT 1").fetchone()[0]
        # Legacy-style: touched L5 but never practiced L1 — frontier stays open.
        _seed(conn, "anon_gate3", [(l5, 0.3)])
        assert H._max_frontier_level(conn, "anon_gate3") >= 5
    finally:
        conn.close()


def _new_levels(q):
    lvls = []

    def walk(items):
        for it in items:
            if it.get("is_new"):
                lvls.append(it["level"])
            for sub in (it.get("items") or []):
                if sub.get("is_new"):
                    lvls.append(sub["level"])
    walk(q["data"]["reviews"])
    return lvls


def test_queue_frontier_respects_gate(hebdb):
    conn = sqlite3.connect(str(hebdb))
    try:
        l1 = _l1_nodes(hebdb, 3)
        _seed(conn, "anon_gate4", [(nid, 0.9) for nid in l1])
    finally:
        conn.close()
    q = H.get_hebrew_review_queue(user_id="anon_gate4", authorization="", limit=100,
                                  new_cards_per_day=10)
    assert q["ok"]
    lvls = _new_levels(q)
    assert lvls, "expected new cards for a gated user"
    assert max(lvls) <= 2, lvls
