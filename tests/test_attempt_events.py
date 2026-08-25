"""Track C2: append-only hebrew_attempt_events — append, idempotency, scoping.

Exercises the real writer from web.routes.hebrew against a throwaway
memorize-style DB; no live learner data is touched.
"""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.hebrew import (  # noqa: E402
    _ensure_attempt_events_schema,
    _record_attempt_event,
)

SCHEMA = (
    "CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY);"
    "INSERT INTO hebrew_nodes VALUES ('letter_aleph');"
)


def _db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "m.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _ensure_attempt_events_schema(conn)
    return conn


def test_every_graded_answer_appends_one_event(tmp_path):
    conn = _db(tmp_path)
    assert _record_attempt_event(conn, "u1", "letter_aleph", "q1", "Aleph", True)
    assert _record_attempt_event(conn, "u1", "letter_aleph", "q1", "Bet", False)
    n = conn.execute("SELECT COUNT(*) FROM hebrew_attempt_events").fetchone()[0]
    assert n == 2


def test_identical_retry_inside_a_minute_is_idempotent(tmp_path):
    conn = _db(tmp_path)
    first = _record_attempt_event(conn, "u1", "letter_aleph", "q1", " Aleph ", True)
    dup = _record_attempt_event(conn, "u1", "letter_aleph", "q1", "aleph", True)
    assert first is True and dup is False
    assert conn.execute(
        "SELECT COUNT(*) FROM hebrew_attempt_events").fetchone()[0] == 1


def test_users_and_nodes_are_isolated_in_the_event_log(tmp_path):
    conn = _db(tmp_path)
    _record_attempt_event(conn, "u1", "letter_aleph", "q1", "Aleph", True)
    _record_attempt_event(conn, "u2", "letter_aleph", "q1", "Aleph", True)
    rows = conn.execute(
        "SELECT user_id FROM hebrew_attempt_events ORDER BY user_id"
    ).fetchall()
    assert [r[0] for r in rows] == ["u1", "u2"]


def test_correctness_is_stored_not_recomputed(tmp_path):
    conn = _db(tmp_path)
    _record_attempt_event(conn, "u1", "letter_aleph", "q1", "wrong", False)
    row = conn.execute(
        "SELECT correct, evaluator_version FROM hebrew_attempt_events").fetchone()
    assert row["correct"] == 0
    assert row["evaluator_version"]  # grader version stamped for audits
