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
            next_review TEXT DEFAULT NULL,
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
            next_review TEXT DEFAULT NULL,
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

    # FSRS-like scheduling: after correct, extend interval; after wrong, shorten
    # Simple exponential spacing: 1d → 3d → 7d → 14d → 30d
    SPACING = [1, 3, 7, 14, 30, 60, 90, 180]
    if existing:
        attempts = existing["attempts"] + 1
        if correct:
            # Count consecutive correct streak
            streak = cursor.execute("""
                SELECT COUNT(*) FROM quiz_progress
                WHERE user_id=? AND question_id=? AND correct > 0
            """, (user_id, question_id)).fetchone()[0]
            interval = SPACING[min(streak, len(SPACING) - 1)]
        else:
            interval = 1  # Re-test tomorrow if wrong

        cursor.execute("""
            UPDATE quiz_progress
            SET correct=correct + ?, attempts=?, last_seen=datetime('now'),
                next_review=date('now', '+? days')
            WHERE user_id=? AND question_id=?
        """, (1 if correct else 0, attempts, interval, user_id, question_id))
    else:
        interval = 1 if correct else 1
        cursor.execute("""
            INSERT INTO quiz_progress (user_id, question_id, correct, attempts, last_seen, next_review)
            VALUES (?, ?, ?, 1, datetime('now'), date('now', '+? days'))
        """, (user_id, question_id, 1 if correct else 0, interval))

    conn.commit()

    # Trigger IRT calibration (async — lightweight)
    try:
        from lib.assessment.irt import calibrate_all_items
        calibrate_all_items(conn)
    except Exception:
        log.warning("silent_exception", exc_info=True)
        pass

    conn.close()

    return {"ok": True, "data": {"recorded": True, "correct": correct}}


@router.get("/api/v1/quiz/progress")
def quiz_progress_summary(user_id: str = "default"):
    """Get user's quiz progress summary with IRT ability estimate."""
    from lib.assessment.irt import get_mastery_summary
    conn = get_db()
    result = get_mastery_summary(conn, user_id=user_id)
    conn.close()
    return {"ok": True, "data": result}


@router.get("/api/v1/quiz/due")
def quiz_due_reviews(user_id: str = "default", limit: int = 20):
    """Get assessment items due for review based on FSRS spacing."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            question_id INTEGER NOT NULL,
            correct INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            last_seen TEXT,
            next_review TEXT DEFAULT NULL,
            PRIMARY KEY (user_id, question_id)
        )
    """)

    # Items due for review (next_review is today or past, or never seen)
    due = cursor.execute("""
        SELECT a.id, a.question_type, a.question_text, a.options_json,
               a.correct_answer, a.layer, a.tier, a.explanation,
               COALESCE(qp.correct, 0) as user_correct,
               COALESCE(qp.attempts, 0) as user_attempts,
               qp.next_review
        FROM assessment_items a
        LEFT JOIN quiz_progress qp ON qp.question_id = a.id AND qp.user_id = ?
        WHERE qp.next_review IS NULL  -- never seen
           OR qp.next_review <= date('now')  -- due
        ORDER BY
            CASE WHEN qp.next_review IS NULL THEN 0 ELSE 1 END,  -- unseen first
            qp.next_review ASC  -- most overdue first
        LIMIT ?
    """, (user_id, limit)).fetchall()

    questions = []
    for r in due:
        opts = []
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            opts = json.loads(r[3]) if r[3] else []
        questions.append({
            "id": r[0],
            "type": r[1],
            "question": r[2],
            "options": opts,
            "correct_answer": r[4],
            "layer": r[5],
            "tier": r[6],
            "explanation": r[7] or "",
            "user_correct": r[8],
            "user_attempts": r[9],
            "next_review": r[10],
        })

    conn.close()
    return {"ok": True, "data": {
        "questions": questions,
        "total": len(questions),
    }}


@router.get("/api/v1/quiz/recommendations")
def quiz_recommendations(user_id: str = "default"):
    """Get study recommendations based on assessment weak areas."""
    from lib.assessment.irt import get_mastery_summary
    conn = get_db()

    summary = get_mastery_summary(conn, user_id=user_id)

    # Build recommendations from weak areas
    recommendations = []
    seen_verses = set()

    for weak in summary.get("weak_areas", []):
        layer = weak["layer"]

        # Find verses in this layer that the user should study
        verses = conn.execute("""
            SELECT DISTINCT ki.verse_id, COUNT(*) as conn_count
            FROM knowledge_items ki
            WHERE ki.layer = ? AND ki.star_rating >= 3
            GROUP BY ki.verse_id
            ORDER BY conn_count DESC
            LIMIT 5
        """, (layer,)).fetchall()

        for v in verses:
            if v["verse_id"] not in seen_verses:
                seen_verses.add(v["verse_id"])
                # Get the verse text
                text_row = conn.execute(
                    "SELECT text_english FROM verses WHERE id = ?",
                    (v["verse_id"],),
                ).fetchone()
                recommendations.append({
                    "area": layer,
                    "accuracy_pct": weak["accuracy_pct"],
                    "recommended_verse": v["verse_id"],
                    "reason": f"Review {layer} connections — your accuracy is {weak['accuracy_pct']}%",
                    "text_snippet": (text_row["text_english"] or "")[:100] if text_row else "",
                })

    # Also recommend by PaRDeS level if we have data
    pardes = conn.execute("""
        SELECT ki.pa_r_de_s_level, COUNT(*) as total,
               SUM(CASE WHEN qp.correct > 0 THEN 1 ELSE 0 END) as correct
        FROM quiz_progress qp
        JOIN knowledge_items ki ON ki.id = qp.question_id
        WHERE qp.user_id = ? AND ki.pa_r_de_s_level IS NOT NULL
        GROUP BY ki.pa_r_de_s_level
        ORDER BY CAST(correct AS REAL) / MAX(total, 1) ASC
    """, (user_id,)).fetchall()

    for r in pardes:
        pct = round((r["correct"] / max(r["total"], 1)) * 100, 1)
        if pct < 60:
            recommendations.append({
                "area": f"PaRDeS: {r['pa_r_de_s_level']}",
                "accuracy_pct": pct,
                "recommended_verse": "",
                "reason": f"Weak in {r['pa_r_de_s_level']} level understanding ({pct}% accuracy). Focus on deeper-level connections.",
                "text_snippet": "",
            })

    conn.close()

    return {"ok": True, "data": {
        "summary": summary,
        "recommendations": recommendations[:10],
        "total_recommendations": len(recommendations[:10]),
    }}


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
