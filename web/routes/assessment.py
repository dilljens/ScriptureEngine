"""Knowledge Assessment — direct HTTP endpoints."""
import contextlib
import json
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


def get_db():
    from lib.db import get_db as _get_db
    return _get_db()


# ── New quiz endpoint: serves deep questions from assessment_items ──

@router.get("/api/v1/quiz")
def get_quiz_questions(
    tier: str = Query(default="", description="Filter by tier: text, analysis, consistency"),
    count: int = Query(default=10, ge=1, le=50),
    bloom_level: str = Query(default="", description="Filter by bloom_level"),
    user_id: str = Query(default="default", description="User ID for adaptive progress"),
):
    """Get deep scripture understanding questions from the assessment_items table.

    Questions show passage text, test analysis/understanding, and are tier-labeled.
    Replaces the old BLIM-based assessment engine for self-testing.
    """
    conn = get_db()
    cursor = conn.cursor()

    where = []
    params = []

    # Convert Query objects to actual values
    tier_val = tier if isinstance(tier, str) else str(tier.query if hasattr(tier, 'query') else "")
    bloom_val = bloom_level if isinstance(bloom_level, str) else ""
    count_val = count if isinstance(count, int) else 10
    user_val = user_id if isinstance(user_id, str) else "default"

    if tier_val:
        tiers = [t.strip() for t in tier_val.split(",") if t.strip()]
        if tiers:
            where.append(f"tier IN ({','.join('?' for _ in tiers)})")
            params.extend(tiers)
    if bloom_val:
        where.append("bloom_level=?")
        params.append(bloom_val)

    where_clause = " AND ".join(where) if where else "1=1"

    # Count total available
    total = cursor.execute(f"SELECT COUNT(*) FROM assessment_items WHERE {where_clause}", params).fetchone()[0]

    # Adaptive: prioritize questions the user hasn't seen or got wrong
    # Create user_progress table if needed
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            question_id INTEGER NOT NULL,
            correct INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            last_seen TEXT,
            PRIMARY KEY (user_id, question_id)
        )
    """)

    # Get questions with adaptive ordering
    rows = cursor.execute(f"""
        SELECT a.question_type, a.question_text, a.options_json, a.correct_answer, a.bloom_level, a.tier,
               a.id as question_id, a.explanation,
               COALESCE(qp.correct, 0) as user_correct,
               COALESCE(qp.attempts, 0) as user_attempts
        FROM assessment_items a
        LEFT JOIN quiz_progress qp ON qp.question_id=a.id AND qp.user_id=?
        WHERE {where_clause}
        ORDER BY
            CASE WHEN qp.attempts IS NULL THEN 0 ELSE 1 END,  -- unseen first
            CAST(qp.correct AS REAL) / NULLIF(qp.attempts, 0) ASC NULLS FIRST,  -- lowest accuracy first
            RANDOM()
        LIMIT ?
    """, [user_val] + params + [count_val]).fetchall()

    questions = []
    for r in rows:
        opts = []
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            opts = json.loads(r[2]) if r[2] else []

        questions.append({
            "type": r[0],
            "question": r[1],
            "options": opts,
            "correct_answer": r[3],
            "bloom_level": r[4] or "",
            "tier": r[5] or "text",
            "question_id": r[6],
            "explanation": r[7] or "",
        })

    # Rebuild with question_ids included
    questions_with_ids = questions

    conn.close()

    return {"ok": True, "data": {
        "questions": questions_with_ids,
        "total": total,
        "returned": len(questions),
    }}


@router.post("/api/v1/quiz/answer")
def quiz_answer(body: dict):
    """Record a quiz answer and update adaptive progress."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            question_id INTEGER NOT NULL,
            correct INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            last_seen TEXT,
            PRIMARY KEY (user_id, question_id)
        )
    """)

    user_id = body.get("user_id", "default")
    question_id = body.get("question_id", 0)
    correct = body.get("correct", False)

    if not question_id:
        conn.close()
        raise HTTPException(400, "question_id required")

    # Upsert progress
    existing = cursor.execute(
        "SELECT correct, attempts FROM quiz_progress WHERE user_id=? AND question_id=?",
        (user_id, question_id)
    ).fetchone()

    if existing:
        cursor.execute("""
            UPDATE quiz_progress
            SET correct=correct + ?, attempts=attempts + 1, last_seen=datetime('now')
            WHERE user_id=? AND question_id=?
        """, (1 if correct else 0, user_id, question_id))
    else:
        cursor.execute("""
            INSERT INTO quiz_progress (user_id, question_id, correct, attempts, last_seen)
            VALUES (?, ?, ?, 1, datetime('now'))
        """, (user_id, question_id, 1 if correct else 0))

    conn.commit()
    conn.close()

    return {"ok": True, "data": {"recorded": True, "correct": correct}}


# ── Old BLIM assessment (kept for backward compatibility) ──

@router.post("/api/v1/assessment/start")
def assessment_start(user_id: str = "default", target_layer: str = "", max_items: int = 20):
    """Start an adaptive assessment session. Returns first question."""
    from lib.api.assessment import start_assessment
    from lib.db import get_db
    conn = get_db()
    kwargs = {"user_id": user_id, "max_items": max_items}
    if target_layer:
        kwargs["target_layer"] = target_layer
    result = start_assessment(conn, **kwargs)
    conn.close()
    if not result.get("ok"):
        raise HTTPException(500, result.get("error", "Assessment failed"))
    # start_assessment returns data directly (no "data" wrapper)
    return {"ok": True, "data": result}


@router.post("/api/v1/assessment/answer")
def assessment_answer(user_id: str = "default", correct: bool = False):
    """Submit an answer, get next question."""
    from lib.api.assessment import submit_answer
    from lib.db import get_db
    conn = get_db()
    result = submit_answer(conn, user_id=user_id, correct=correct)
    conn.close()
    if not result.get("ok"):
        raise HTTPException(500, result.get("error", "Answer failed"))
    return {"ok": True, "data": result}


@router.get("/api/v1/assessment/progress")
def assessment_progress(user_id: str = "default"):
    """Get current assessment progress."""
    from lib.api.assessment import get_progress
    from lib.db import get_db
    conn = get_db()
    result = get_progress(conn, user_id=user_id)
    conn.close()
    return {"ok": True, "data": result}
