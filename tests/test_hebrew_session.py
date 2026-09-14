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


def _placement_answer(question):
    rows = _mem_db_rows(
        "SELECT correct_answer FROM hebrew_practice_items WHERE id=?",
        question["question_id"],
    )
    return rows[0]["correct_answer"]


def _practice_answer(question):
    rows = _mem_db_rows(
        "SELECT correct_answer FROM hebrew_practice_items WHERE id=?",
        question["question_id"],
    )
    return rows[0]["correct_answer"]


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
    quiz = client.get("/api/v1/hebrew/lesson/qal_perfect/quiz")
    assert quiz.status_code == 200
    question = next(
        q for q in quiz.json()["data"]["questions"]
        if q["type"] == "multiple_choice" and len(q["options"]) >= 2
    )
    # Submit the issued label TEXT, not the index: the server shuffles MC
    # options per request, so an index is meaningless to it.
    answer = _practice_answer(question)
    assert answer in question["options"]
    r = client.post("/api/v1/hebrew/progress", json={
        "user_id": "attacker-forged",
        "session_token": token,
        "node_id": question["node_id"],
        "question_id": question["question_id"],
        "answer": answer,
        "answer_mode": "choice_index",
    })
    assert r.status_code == 200
    rows = _mem_db_rows(
        "SELECT user_id, attempts, correct FROM hebrew_progress "
        "WHERE node_id=? AND user_id='real-user-123'",
        question["node_id"],
    )
    assert rows and rows[0]["attempts"] == 1 and rows[0]["correct"] == 1
    # the forged user_id must NOT have received the attempt
    forged = _mem_db_rows(
        "SELECT 1 FROM hebrew_progress WHERE node_id=? AND user_id='attacker-forged'",
        question["node_id"],
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


def test_progress_rejects_forged_user_without_session(client):
    quiz = client.get("/api/v1/hebrew/lesson/qal_perfect/quiz")
    question = next(q for q in quiz.json()["data"]["questions"] if q["question_id"] is not None)
    response = client.post("/api/v1/hebrew/progress", json={
        "user_id": "victim-user",
        "node_id": question["node_id"],
        "question_id": question["question_id"],
        "answer": "",
        "answer_mode": "free_text",
    })
    assert response.status_code == 401


@pytest.mark.parametrize("path", [
    "/api/v1/hebrew/curriculum",
    "/api/v1/hebrew/review-queue",
    "/api/v1/hebrew/learning-speeds",
    "/api/v1/hebrew/diagnostic",
    "/api/v1/hebrew/quiz",
    "/api/v1/hebrew/gamification",
])
def test_user_scoped_reads_reject_forged_query_user(client, path):
    response = client.get(path, params={"user_id": "victim-user"})
    assert response.status_code == 401


def test_user_scoped_read_binds_bearer_session_over_forged_query(client):
    token = _make_token("real-read-user")
    response = client.get(
        "/api/v1/hebrew/gamification",
        params={"user_id": "victim-user"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_generic_hebrew_progress_tool_requires_session(client):
    response = client.get(
        "/api/v1/tools/scripture_hebrew_progress",
        params={"user_id": "victim-user"},
    )
    assert response.status_code == 401

    token = _make_token("real-tool-user")
    response = client.get(
        "/api/v1/tools/scripture_hebrew_progress",
        params={"user_id": "victim-user", "session_token": token},
    )
    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == "real-tool-user"


def test_aggregate_progress_requires_session_for_custom_user(client):
    response = client.get("/api/v1/user/progress/victim-user")
    assert response.status_code == 401

    token = _make_token("real-aggregate-user")
    response = client.get(
        "/api/v1/user/progress/victim-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["user_id"] == "real-aggregate-user"


def test_interleaved_reviews_require_session_for_custom_user(client):
    response = client.get(
        "/api/v1/review/interleaved", params={"user_id": "victim-user"}
    )
    assert response.status_code == 401


def test_fsrs_custom_user_without_session_returns_401(client):
    response = client.post("/api/v1/hebrew/fsrs/review", json={
        "user_id": "victim-user", "node_id": "aleph", "rating": 3,
    })
    assert response.status_code == 401


def test_adaptive_answer_requires_placement_owner(client):
    token = _make_token("placement-owner")
    started = client.post("/api/v1/hebrew/diagnostic/adaptive/start", json={
        "user_id": "placement-owner", "session_token": token,
    })
    assert started.status_code == 200
    q = started.json()["data"]["question"]
    response = client.post("/api/v1/hebrew/diagnostic/adaptive/answer", json={
        "session_id": started.json()["data"]["session_id"],
        "question_id": q["question_id"], "question_nonce": q["question_nonce"],
        "answer": _placement_answer(q),
    })
    assert response.status_code == 403


def test_progress_grades_issued_choice_instead_of_client_boolean(client):
    """A question id plus answer is authoritative over an ambiguous boolean."""
    quiz = client.get("/api/v1/hebrew/lesson/qal_perfect/quiz")
    assert quiz.status_code == 200
    questions = quiz.json()["data"]["questions"]
    question = next(
        q for q in questions
        if q["type"] == "multiple_choice"
        and len(q["options"]) >= 2
        and _practice_answer(q) in q["options"]
    )
    answer_text = _practice_answer(question)
    assert answer_text in question["options"]
    user_id = "authoritative-hebrew-progress"
    token = _make_token(user_id)

    r = client.post("/api/v1/hebrew/progress", json={
        "user_id": user_id,
        "session_token": token,
        "node_id": question["node_id"],
        "question_id": question["question_id"],
        "answer": answer_text,
        "answer_mode": "choice_index",
        "correct": False,
    })

    assert r.status_code == 200
    assert r.json()["data"]["correct"] == 1

    wrong_text = next(o for o in question["options"] if o != answer_text)
    r = client.post("/api/v1/hebrew/progress", json={
        "user_id": user_id,
        "session_token": token,
        "node_id": question["node_id"],
        "question_id": question["question_id"],
        "answer": wrong_text,
        "answer_mode": "choice_index",
        "correct": True,
    })
    assert r.status_code == 200
    assert r.json()["data"]["correct"] == 1

    rows = _mem_db_rows(
        "SELECT attempts, correct FROM hebrew_progress WHERE user_id=? AND node_id=?",
        user_id, question["node_id"],
    )
    assert rows == [{"attempts": 2, "correct": 1}]


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
        "SELECT user_id, reps FROM hebrew_review_state WHERE node_id='aleph' AND user_id='review-user'"
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
