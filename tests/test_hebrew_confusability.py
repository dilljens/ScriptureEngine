"""Track B: confusability matrix — seed script + non-interference separation.

The review queue and curriculum generator read `hebrew_confusability`
(node_a, node_b) and reorder so confusable pairs are never adjacent.
These tests verify:
  1. the seed script is idempotent and honors MEMORIZE_DB_PATH,
  2. the interleave helper keeps confusable pairs >=3 items apart,
  3. the review-queue endpoint actually wires the table in.
"""
import sqlite3
from pathlib import Path

import pytest

import scripts.seed_hebrew_confusability as seed_mod


# ── Helpers ──

def _due_item(node_id, category, level, retrievability=0.5):
    return {
        "node_id": node_id, "category": category, "level": level,
        "retrievability": retrievability, "title": node_id,
        "mastery": 0.5, "attempts": 3, "correct": 2, "scheduler": "adaptive-v1",
    }


def _flatten_reviews(reviews):
    """Flatten compressed groups back to their member node ids."""
    flat = []
    for r in reviews:
        if isinstance(r, dict) and r.get("type") == "compressed":
            flat.extend(it["node_id"] for it in r.get("items", []))
        else:
            flat.append(r["node_id"])
    return flat


def _positions(flat, a, b):
    return flat.index(a), flat.index(b)


# ── 1. Seed script ──

def test_seed_inserts_pairs_and_is_idempotent(tmp_path):
    db = tmp_path / "memorize.db"
    _make_minimal_db(db)
    assert seed_mod.seed(db) == 28          # fresh insert (2 of 30 pairs skipped)
    assert seed_mod.seed(db) == 0           # idempotent re-run
    conn = sqlite3.connect(str(db))
    rows = set(conn.execute(
        "SELECT node_a, node_b FROM hebrew_confusability").fetchall())
    conn.close()
    assert ("shin", "sin") in rows
    assert ("bet", "vav") in rows
    assert ("aleph", "ayin") in rows
    assert ("tet", "tav") in rows
    assert ("he", "chet") in rows
    assert ("sin", "samekh") in rows
    assert len(rows) == 28


def test_seed_honors_memorize_db_path(tmp_path, monkeypatch):
    db = tmp_path / "custom.db"
    _make_minimal_db(db)
    monkeypatch.setenv("MEMORIZE_DB_PATH", str(db))
    assert seed_mod.seed(seed_mod._resolve_db_path()) == 28


def test_seed_skips_missing_nodes(tmp_path):
    db = tmp_path / "memorize.db"
    _make_minimal_db(db)
    conn = sqlite3.connect(str(db))
    conn.execute("DELETE FROM hebrew_nodes WHERE id IN ('perfect_3ms','imperfect_3ms')")
    conn.commit()
    conn.close()
    assert seed_mod.seed(db) == 28  # the missing-node pair is the 29th, skipped


def _make_minimal_db(db):
    """Build a minimal memorize.db with hebrew_nodes + hebrew_confusability."""
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY, title TEXT, level INTEGER, category TEXT, description TEXT)")
    # Every node referenced by CONFUSABLE_PAIRS that exists in the real DB
    existing = [
        "aleph", "ayin", "bet", "chet", "dalet", "gimel", "he", "kaf",
        "kaf_final", "mem", "mem_final", "nun", "nun_final", "pe", "pe_final",
        "qof", "resh", "samekh", "shin", "sin", "tav", "tet", "tsade",
        "tsade_final", "vav", "zayin",
        "vowel_patah", "vowel_qamats", "vowel_segol", "vowel_tsere",
        "vowel_hiriq", "vowel_hiriq_yod", "vowel_holam", "vowel_holam_vav",
        "vowel_shuruq", "vowel_qubuts", "vowel_sheva_na", "vowel_sheva_nah",
        "qal_perfect", "qal_imperfect", "niphal", "pual", "hiphil", "hophal",
        "piel", "construct_chain", "definite_article",
        "infinitive_construct", "infinitive_absolute",
    ]
    for nid in existing:
        conn.execute(
            "INSERT OR IGNORE INTO hebrew_nodes (id, title, level, category) VALUES (?,?,1,'consonant')",
            (nid, nid))
    conn.commit()
    conn.close()


# ── 2. Interleave helper (pure) ──

def test_interleave_separates_confusable_pair_by_3():
    from web.routes.hebrew import _interleave_due_items
    pairs = {("shin", "sin"), ("sin", "shin")}
    by_cat = {"consonant": [
        _due_item("shin", "consonant", 1, 0.1),
        _due_item("sin", "consonant", 1, 0.2),
        _due_item("bet", "consonant", 1, 0.9),
        _due_item("samekh", "consonant", 1, 0.9),
        _due_item("he", "consonant", 1, 0.9),
        _due_item("tav", "consonant", 1, 0.9),
        _due_item("aleph", "consonant", 1, 0.9),
        _due_item("qof", "consonant", 1, 0.9),
    ]}
    out = _interleave_due_items(by_cat, pairs)
    ids = [it["node_id"] for it in out]
    assert "shin" in ids and "sin" in ids
    assert abs(ids.index("shin") - ids.index("sin")) >= 4  # >=3 items between


def test_interleave_separates_with_symmetric_pairs():
    from web.routes.hebrew import _interleave_due_items
    # Callers build symmetric sets (both directions) from the table — as the
    # review-queue endpoint does.
    pairs = {("he", "chet"), ("chet", "he")}
    by_cat = {"consonant": [
        _due_item("he", "consonant", 1, 0.1),
        _due_item("chet", "consonant", 1, 0.2),
        _due_item("bet", "consonant", 1, 0.9),
        _due_item("vav", "consonant", 1, 0.9),
        _due_item("gimel", "consonant", 1, 0.9),
        _due_item("dalet", "consonant", 1, 0.9),
        _due_item("lamed", "consonant", 1, 0.9),
        _due_item("nun", "consonant", 1, 0.9),
    ]}
    out = _interleave_due_items(by_cat, pairs)
    ids = [it["node_id"] for it in out]
    assert abs(ids.index("he") - ids.index("chet")) >= 4


def test_interleave_does_not_break_when_confusable_pair_unavoidable():
    from web.routes.hebrew import _interleave_due_items
    # Only a confusable pair — no room to separate; must still return both.
    pairs = {("shin", "sin"), ("sin", "shin")}
    by_cat = {"consonant": [
        _due_item("shin", "consonant", 1, 0.1),
        _due_item("sin", "consonant", 1, 0.2),
    ]}
    out = _interleave_due_items(by_cat, pairs)
    assert {it["node_id"] for it in out} == {"shin", "sin"}


# ── 3. Review-queue integration ──

@pytest.fixture
def _seed_due_pool(client):
    import web.routes.hebrew as hebrew_routes
    conn = sqlite3.connect(str(hebrew_routes.MEM_DB))
    conn.row_factory = sqlite3.Row
    # Only the pair under test — deterministic, independent of the template.
    conn.execute("DELETE FROM hebrew_confusability")
    conn.execute(
        "INSERT OR IGNORE INTO hebrew_confusability (node_a,node_b,reason,strength) VALUES ('shin','sin','test pair',0.7)")
    nodes = [
        ("shin", "consonant", 1), ("sin", "consonant", 1),
        ("bet", "consonant", 1), ("vav", "consonant", 1),
        ("he", "consonant", 1), ("chet", "consonant", 1),
        ("vowel_patah", "vowel", 2), ("vowel_qamats", "vowel", 2),
        ("vowel_segol", "vowel", 2), ("vowel_tsere", "vowel", 2),
        ("qal_perfect", "grammar", 4), ("qal_imperfect", "grammar", 4),
        ("piel", "grammar", 4), ("pual", "grammar", 4),
        ("aleph", "consonant", 1), ("samekh", "consonant", 1),
    ]
    for nid, cat, level in nodes:
        conn.execute(
            "INSERT OR REPLACE INTO hebrew_progress (user_id,node_id,mastery,attempts,correct,last_practiced) "
            "VALUES ('conf-user',?,0.5,3,2,'2020-01-01 00:00:00')", (nid,))
        conn.execute("""
            INSERT OR REPLACE INTO hebrew_review_state
                (user_id,node_id,stability,difficulty,due,last_review,last_rating,reps,lapses)
            VALUES ('conf-user',?,2.0,5.0,'2020-01-01 00:00:00','2020-01-01 00:00:00',3,2,0)
        """, (nid,))
    conn.commit()
    conn.close()


def test_review_queue_separates_confusable_pair_when_both_due(client, _seed_due_pool):
    r = client.get("/api/v1/hebrew/review-queue", params={"user_id": "conf-user", "limit": 30})
    assert r.status_code == 200
    data = r.json()["data"]
    flat = _flatten_reviews(data["reviews"])
    assert "shin" in flat and "sin" in flat, f"both due nodes must appear: {flat}"
    # Non-interference: >=3 other items between the confusable pair.
    shin_pos, sin_pos = _positions(flat, "shin", "sin")
    assert abs(shin_pos - sin_pos) >= 4, f"shin/sin too close in queue: {flat}"


def test_review_queue_pair_confusability_warning(client, _seed_due_pool):
    r = client.get("/api/v1/hebrew/review-queue", params={"user_id": "conf-user", "limit": 30})
    data = r.json()["data"]
    shin = next((it for it in data["reviews"]
                 if isinstance(it, dict) and it.get("node_id") == "shin"), None)
    if shin:
        assert shin.get("confusability_warning") == ["sin"]
