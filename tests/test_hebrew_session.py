"""Track B: Hebrew review/progress/diagnostic session-token binding.

The learner frontend sends its session token (stored as `scripture_session_token`
in localStorage) on Hebrew write endpoints. The backend must bind the operation
to the token's REAL user — a caller-supplied (forged) user_id is ignored — and
reject invalid tokens with 401 so anonymous learners fall back to 'default'.
"""
import hashlib
import secrets
import sqlite3

import pytest
from fastapi import HTTPException

from lib.db import get_db as get_scripture_db
from web.routes.hebrew import _resolve_hebrew_user


def _make_token(user_id="real-user-123"):
    """Insert a real session token for a user in the auth DB (test.db)."""
    token = hashlib.sha256(f"{user_id}:{secrets.token_hex(32)}".encode()).hexdigest()
    conn = get_scripture_db()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (id, user_id, token_hash) VALUES (?,?,?)",
        (token[:16], user_id, token),
    )
    conn.commit()
    conn.close()
    return token


def _mem_db_rows(sql, *args):
    import web.routes.hebrew as hebrew_routes

    conn = sqlite3.connect(hebrew_routes.MEM_DB)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, args)]
    conn.close()
    return rows


def test_resolve_binds_real_user_and_ignores_forged_id():
    token = _make_token("real-user-123")
    assert _resolve_hebrew_user("forged-user", token) == "real-user-123"


def test_resolve_defaults_when_no_token():
    assert _resolve_hebrew_user("custom-user", "") == "custom-user"
    assert _resolve_hebrew_user("", "") == "default"


def test_resolve_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        _resolve_hebrew_user("forged-user", "definitely-not-a-session-token")
    assert exc.value.status_code == 401


def test_progress_binds_session_token_over_forged_user_id(client):
    token = _make_token("real-user-123")
    r = client.post("/api/v1/hebrew/progress", json={
        "user_id": "attacker-forged",
        "session_token": token,
        "node_id": "aleph",
        "correct": True,
    })
    assert r.status_code == 200
    rows = _mem_db_rows(
        "SELECT user_id, attempts, correct FROM hebrew_progress "
        "WHERE node_id='aleph' AND user_id='real-user-123'"
    )
    assert rows and rows[0]["attempts"] == 1 and rows[0]["correct"] == 1
    # the forged user_id must NOT have received the attempt
    forged = _mem_db_rows(
        "SELECT 1 FROM hebrew_progress WHERE node_id='aleph' AND user_id='attacker-forged'"
    )
    assert not forged


def test_progress_invalid_token_returns_401(client):
    r = client.post("/api/v1/hebrew/progress", json={
        "user_id": "attacker-forged",
        "session_token": "not-a-real-token",
        "node_id": "aleph",
        "correct": True,
    })
    assert r.status_code == 401


def test_fsrs_review_binds_session_token(client):
    token = _make_token("review-user")
    r = client.post("/api/v1/hebrew/fsrs/review", json={
        "user_id": "forged",
        "session_token": token,
        "node_id": "aleph",
        "rating": 3,
    })
    assert r.status_code == 200
    rows = _mem_db_rows(
        "SELECT user_id, reps FROM hebrew_review_state WHERE node_id='aleph'"
    )
    assert rows and rows[0]["user_id"] == "review-user"
    assert rows[0]["reps"] == 1


def test_fsrs_review_invalid_token_returns_401(client):
    r = client.post("/api/v1/hebrew/fsrs/review", json={
        "user_id": "forged",
        "session_token": "not-a-real-token",
        "node_id": "aleph",
        "rating": 3,
    })
    assert r.status_code == 401
