"""P2-B hebrew_cloze + two_way_translation + hebrew_visual_only (Hebrew side).

Isolated tmp COPY of the real memorize.db (real cloze items + nodes);
writes never touch production.
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


def _backdate_due(db, node_id, card_mode):
    conn = sqlite3.connect(str(db))
    conn.execute("UPDATE hebrew_review_state SET due='2000-01-01'"
                 " WHERE user_id='default' AND node_id=? AND card_mode=?",
                 (node_id, card_mode))
    conn.commit()
    conn.close()


def test_cloze_next_deterministic_no_answer_leak(hebdb):
    first = H.get_cloze_next(user_id="default", authorization="",
                             limit=5, day="2026-09-21")
    assert first["ok"] and first["data"]["count"] > 0
    card = first["data"]["cards"][0]
    assert "______" in card["prompt"] and card["blank_start"] >= 0
    # The answer must NOT travel to the client payload.
    truth = _rows(hebdb, "SELECT correct_answer FROM hebrew_practice_items"
                         " WHERE id=?", (card["question_id"],))[0][0]
    assert truth and truth.strip()
    # The answer must not appear in the prompt content channel. (The node
    # id itself names the lesson topic — e.g. vocab_אבדה_276 — which is the
    # lesson label, not a leak of this card's answer.)
    assert truth not in card["prompt"]
    # Same day → same cards (stable target word per node).
    second = H.get_cloze_next(user_id="default", authorization="",
                              limit=5, day="2026-09-21")
    assert [c["question_id"] for c in second["data"]["cards"]] == \
           [c["question_id"] for c in first["data"]["cards"]]


def test_cloze_rating_grades_through_progress(hebdb):
    card = H.get_cloze_next(user_id="default", authorization="",
                            limit=1, day="2026-09-21")["data"]["cards"][0]
    truth = _rows(hebdb, "SELECT correct_answer FROM hebrew_practice_items"
                         " WHERE id=?", (card["question_id"],))[0][0]
    out = H.update_hebrew_progress(
        {"user_id": "default", "node_id": card["node_id"],
         "question_id": card["question_id"], "answer": truth},
        authorization="")
    assert out["ok"] is True


def test_translation_next_lists_distinct_directions(hebdb):
    node = _rows(hebdb, "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1")[0][0]
    H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                            card_mode="forward")
    H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                            card_mode="reverse")
    _backdate_due(hebdb, node, "forward")
    _backdate_due(hebdb, node, "reverse")
    out = H.get_translation_next(user_id="default", authorization="", limit=10)
    dirs = {c["direction"] for c in out["data"]["cards"] if not c["is_new"]}
    assert {"forward", "reverse"} <= dirs
    rated = H.process_hebrew_review(node_id=node, rating=4, user_id="default",
                                    card_mode="reverse")
    assert rated["data"]["card_mode"] == "reverse"


def test_visual_only_schedules_distinct_rows(hebdb):
    node = _rows(hebdb, "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1")[0][0]
    out = H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                                  card_mode="visual_only")
    assert out["data"]["card_mode"] == "visual_only"
    _backdate_due(hebdb, node, "visual_only")
    cards = H.get_visual_next(user_id="default", authorization="",
                              limit=10)["data"]["cards"]
    mine = [c for c in cards if c["node_id"] == node and not c["is_new"]]
    assert mine and mine[0]["a11y_name"]


def test_bogus_card_mode_still_coerces_to_general(hebdb):
    node = _rows(hebdb, "SELECT id FROM hebrew_nodes ORDER BY id LIMIT 1")[0][0]
    out = H.process_hebrew_review(node_id=node, rating=3, user_id="default",
                                  card_mode="bogus")
    assert out["data"]["card_mode"] == ""
