"""Track C: per-topic learning speeds (Phase 7).

Verifies the ability/difficulty model in web/routes/hebrew.py:
  - per-user per-topic (category-level) accuracy rollup
  - learning_speed = per-topic ability / topic difficulty
  - interval modulation with caps [0.25x, 4x]
  - two users on the same topic get different intervals per their accuracy
  - the `learning_speed < 0.5 → no FIRe credit` rule is preserved
"""
import sqlite3

import pytest


def _seed_progress(client, user_id, rows):
    """rows: [(node_id, attempts, correct)] → hebrew_progress in the isolated DB."""
    import web.routes.hebrew as hebrew_routes
    conn = sqlite3.connect(str(hebrew_routes.MEM_DB))
    for node_id, attempts, correct in rows:
        mastery = round(correct / max(attempts, 1), 3)
        conn.execute(
            "INSERT OR REPLACE INTO hebrew_progress (user_id,node_id,mastery,attempts,correct,last_practiced) "
            "VALUES (?,?,?,?,?,datetime('now'))",
            (user_id, node_id, mastery, attempts, correct))
    conn.commit()
    conn.close()


def _mem_rows(sql, *args):
    import web.routes.hebrew as hebrew_routes
    conn = sqlite3.connect(str(hebrew_routes.MEM_DB))
    rows = conn.execute(sql, args).fetchall()
    conn.close()
    return rows


# ── 1. Per-user per-topic accuracy rollup ──

def test_category_accuracy_rollup(client):
    from web.routes.hebrew import _get_user_category_accuracy
    _seed_progress(client, "rollup-user", [
        ("aleph", 10, 10), ("bet", 10, 10),          # consonant → 1.0
        ("vav", 10, 10), ("shin", 10, 10),
        ("qal_perfect", 10, 0), ("piel", 10, 0),     # grammar → 0.0
        ("vowel_patah", 4, 1),                       # vowel → 0.25
    ])
    rollup = _get_user_category_accuracy("rollup-user")
    assert rollup.get("consonant") == 1.0
    assert rollup.get("verb") == 0.0      # qal_perfect/piel are category 'verb'
    assert rollup.get("vowel") == 0.25
    # A user with no progress gets an empty rollup.
    assert _get_user_category_accuracy("nobody") == {}


def test_compute_speed_uses_per_topic_ability(client):
    import web.routes.hebrew as hebrew_routes
    _seed_progress(client, "hi", [("aleph", 10, 10), ("bet", 10, 10),
                                  ("vav", 10, 10), ("shin", 10, 10)])
    _seed_progress(client, "lo", [("aleph", 10, 0), ("bet", 10, 0),
                                  ("vav", 10, 0), ("shin", 10, 0)])
    hi_speeds = hebrew_routes.compute_learning_speed("hi")[0]
    lo_speeds = hebrew_routes.compute_learning_speed("lo")[0]
    assert "shin" in hi_speeds and "shin" in lo_speeds
    # Same topic difficulty, different per-topic ability → different speed.
    assert hi_speeds["shin"] > lo_speeds["shin"]


# ── 2. Caps ──

def test_clamp_learning_speed_exact_caps():
    from web.routes.hebrew import clamp_learning_speed
    assert clamp_learning_speed(10.0) == 4.0
    assert clamp_learning_speed(0.0) == 0.25
    assert clamp_learning_speed(-5.0) == 0.25
    assert clamp_learning_speed(1.5) == 1.5


def test_interval_caps_respected_in_review(client):
    import web.routes.hebrew as hebrew_routes
    # hi: perfect consonant ability; lo: zero consonant ability. Same topic.
    _seed_progress(client, "hi", [("aleph", 10, 10), ("bet", 10, 10),
                                  ("vav", 10, 10), ("shin", 10, 10)])
    # Two "average" users keep topic difficulty from bottoming out.
    _seed_progress(client, "avg1", [("shin", 9, 9)])
    _seed_progress(client, "avg2", [("shin", 9, 9)])
    _seed_progress(client, "lo", [("aleph", 10, 0), ("bet", 10, 0),
                                  ("vav", 10, 0), ("shin", 10, 0)])

    r_hi = hebrew_routes.process_hebrew_review("shin", rating=3, user_id="hi")
    r_lo = hebrew_routes.process_hebrew_review("shin", rating=3, user_id="lo")

    assert hebrew_routes.LEARNING_SPEED_MIN <= r_hi["data"]["learning_speed"] <= hebrew_routes.LEARNING_SPEED_MAX
    assert hebrew_routes.LEARNING_SPEED_MIN <= r_lo["data"]["learning_speed"] <= hebrew_routes.LEARNING_SPEED_MAX

    base = hebrew_routes.fsrs_next_interval(hebrew_routes.fsrs_initial_stability(3))
    floor_interval = max(1, round(base * hebrew_routes.LEARNING_SPEED_MIN))
    cap_interval = max(1, round(base * hebrew_routes.LEARNING_SPEED_MAX))
    assert floor_interval <= r_hi["data"]["interval"] <= cap_interval
    assert floor_interval <= r_lo["data"]["interval"] <= cap_interval


def test_two_users_same_topic_get_different_intervals(client):
    import web.routes.hebrew as hebrew_routes
    _seed_progress(client, "hi", [("aleph", 10, 10), ("bet", 10, 10),
                                  ("vav", 10, 10), ("shin", 10, 10)])
    _seed_progress(client, "lo", [("aleph", 10, 0), ("bet", 10, 0),
                                  ("vav", 10, 0), ("shin", 10, 0)])

    r_hi = hebrew_routes.process_hebrew_review("shin", rating=3, user_id="hi")
    r_lo = hebrew_routes.process_hebrew_review("shin", rating=3, user_id="lo")

    assert r_hi["data"]["interval"] != r_lo["data"]["interval"]
    assert r_hi["data"]["interval"] > r_lo["data"]["interval"]
    assert r_hi["data"]["learning_speed"] > r_lo["data"]["learning_speed"]


# ── 3. FIRe gate preserved ──

def test_low_speed_skips_fire_credit(client):
    import web.routes.hebrew as hebrew_routes
    # Zero-accuracy user → learning_speed floor → no FIRe credit.
    _seed_progress(client, "slow", [("aleph", 10, 0), ("bet", 10, 0),
                                    ("shin", 10, 0)])
    # Give shin a prerequisite so FIRe would have credit to flow.
    conn = sqlite3.connect(str(hebrew_routes.MEM_DB))
    conn.execute("INSERT OR IGNORE INTO hebrew_edges (source_id,target_id) VALUES ('aleph','shin')")
    conn.commit()
    conn.close()

    r = hebrew_routes.process_hebrew_review("shin", rating=3, user_id="slow")
    assert r["data"]["learning_speed"] < 0.5
    assert r["data"]["fire_credits"] == {}
    # And the slow learner's interval sits at the floor.
    base = hebrew_routes.fsrs_next_interval(hebrew_routes.fsrs_initial_stability(3))
    assert r["data"]["interval"] == max(1, round(base * hebrew_routes.LEARNING_SPEED_MIN))


@pytest.mark.parametrize("node_id", ["aleph", "shin", "vowel_patah", "qal_perfect"])
def test_review_endpoint_returns_speed_fields(client, node_id):
    import web.routes.hebrew as hebrew_routes
    _seed_progress(client, "tester", [(node_id, 3, 2)])
    r = client.post("/api/v1/hebrew/fsrs/review", json={
        "node_id": node_id, "rating": 3, "user_id": "tester"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert "learning_speed" in data
    assert "user_ability" in data
    assert data["interval"] >= 1
