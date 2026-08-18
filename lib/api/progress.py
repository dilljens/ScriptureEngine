"""Progress-visibility tools for the chat LLM.

These tools let the LLM see what a user has actually done — quiz answers,
Hebrew learning progress, and placement results — so it can personalize
teaching instead of guessing. All are read-only; they never mutate state.

Three stores are read:
- quiz_progress / chat_quiz_answers (scripture.db) — MC question results
- hebrew_progress / hebrew_review_state / hebrew_gamification (memorize.db)
- hebrew_placement_sessions / hebrew_diagnostic_batches (memorize.db)
"""

import json
import sqlite3
from pathlib import Path

from lib.assessment.irt import get_mastery_summary

# memorize.db location — mirrors the convention in web/routes/hebrew.py
# (env override first, then <project>/data/memorize.db).
def _mem_db_path():
    import os

    override = os.environ.get("MEMORIZE_DB_PATH")
    if override:
        return Path(override)
    return Path(__file__).parent.parent.parent / "data" / "memorize.db"


def quiz_progress(conn, user_id="default", limit=10):
    """See a user's multiple-choice question results: mastery by PaRDeS layer,
    IRT ability estimate, and their most recent answers. Use this when the user
    has answered quiz/MC questions in the app or in chat and you need to know
    what they got right or wrong, what's weak, or how they're trending."""
    # Formal assessment mastery (quiz_progress table → IRT summary)
    summary = get_mastery_summary(conn, user_id=user_id)
    summary["ok"] = True

    # Most recent answers from both the formal quiz store and chat quizzes
    recent = _recent_quiz_answers(conn, user_id, limit)
    summary["recent_answers"] = recent
    summary["chat_quiz_count"] = _chat_quiz_count(conn, user_id)
    return summary


def _recent_quiz_answers(conn, user_id, limit):
    """Recent formal quiz answers joined with question text."""
    try:
        rows = conn.execute(
            """SELECT qp.question_id, qp.correct, qp.attempts, qp.last_seen,
                      ai.question_text, ai.layer
               FROM quiz_progress qp
               LEFT JOIN assessment_items ai ON ai.id = qp.question_id
               WHERE qp.user_id = ?
               ORDER BY qp.last_seen DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def _chat_quiz_count(conn, user_id):
    """Count of MC answers recorded from chat quiz cards."""
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM chat_quiz_answers WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return row[0] if row else 0
    except sqlite3.OperationalError:
        return 0


def hebrew_progress(conn, user_id="default", limit=10):
    """See a user's Biblical Hebrew learning progress: mastery per category,
    due review items, XP/streak, and their placement/diagnostic results.
    Use this whenever the user asks about Hebrew, their Hebrew progress, what
    to study next, or how they're doing in the Hebrew course."""
    db = _mem_db_path()
    if not db.exists():
        return {"ok": True, "error": "Hebrew learning DB not found", "has_progress": False}

    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row

    try:
        # Per-node mastery rollup by category
        cats = c.execute(
            """SELECT COALESCE(n.category,'other') AS category,
                      COUNT(*) AS total,
                      SUM(CASE WHEN p.mastery >= 0.8 THEN 1 ELSE 0 END) AS mastered,
                      SUM(CASE WHEN p.mastery > 0 AND p.mastery < 0.8 THEN 1 ELSE 0 END) AS in_progress,
                      COALESCE(AVG(p.mastery), 0) AS avg_mastery
               FROM hebrew_nodes n
               LEFT JOIN hebrew_progress p ON p.node_id = n.id AND p.user_id = ?
               GROUP BY category
               ORDER BY avg_mastery DESC""",
            (user_id,),
        ).fetchall()

        # Nodes practiced (any attempt) — most recent first
        practiced = c.execute(
            """SELECT p.node_id, n.title, n.category, p.mastery, p.attempts,
                      p.correct, p.last_practiced
               FROM hebrew_progress p
               JOIN hebrew_nodes n ON n.id = p.node_id
               WHERE p.user_id = ? AND p.attempts > 0
               ORDER BY p.last_practiced DESC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()

        # Due review items (SRS) — count + next few
        due_rows = c.execute(
            """SELECT r.node_id, n.title, n.category, r.due, r.stability,
                      r.difficulty, r.reps, r.lapses
               FROM hebrew_review_state r
               JOIN hebrew_nodes n ON n.id = r.node_id
               WHERE r.user_id = ? AND r.due <= datetime('now')
               ORDER BY r.due ASC
               LIMIT ?""",
            (user_id, limit),
        ).fetchall()
        due_count = c.execute(
            """SELECT COUNT(*) FROM hebrew_review_state
               WHERE user_id = ? AND due <= datetime('now')""",
            (user_id,),
        ).fetchone()[0]

        # Gamification
        gam = c.execute(
            "SELECT xp, streak_count, best_streak, last_review_date FROM hebrew_gamification WHERE user_id = ?",
            (user_id,),
        ).fetchone()

        # Placement + diagnostic
        placement = _latest_placement(c, user_id)
        diagnostic = _latest_diagnostic(c, user_id)
    finally:
        c.close()

    result = {
        "ok": True,
        "user_id": user_id,
        "has_progress": bool(practiced or cats),
        "by_category": [dict(r) for r in cats],
        "practiced_nodes": [dict(r) for r in practiced],
        "due_reviews": {
            "count": due_count,
            "next_items": [dict(r) for r in due_rows],
        },
        "gamification": dict(gam) if gam else None,
        "placement": placement,
        "diagnostic": diagnostic,
    }
    return result


def hebrew_placement(conn, user_id="default"):
    """See where a user placed on the Hebrew placement test (per-skill
    1-up-3-down staircase results) and whether they've taken it. Returns the
    most recent placement per skill: level estimate, items answered, and
    whether it converged. Use this to recommend where the user should start."""
    db = _mem_db_path()
    if not db.exists():
        return {"ok": True, "error": "Hebrew learning DB not found", "has_placement": False}

    c = sqlite3.connect(str(db))
    c.row_factory = sqlite3.Row
    try:
        sessions = c.execute(
            """SELECT session_id, skill_idx, state_json, created_at, used_at
               FROM hebrew_placement_sessions
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT 20""",
            (user_id,),
        ).fetchall()
    finally:
        c.close()

    if not sessions:
        return {
            "ok": True,
            "user_id": user_id,
            "has_placement": False,
            "message": "No placement test taken yet. The user can take it in the Hebrew Learn app.",
        }

    # Latest session only (they repeat the test; the newest result is the truth)
    latest = sessions[0]
    try:
        state = json.loads(latest["state_json"])
    except (json.JSONDecodeError, TypeError):
        state = {}

    skills = []
    for skill, data in state.items():
        if not isinstance(data, dict):
            continue
        skills.append({
            "skill": skill,
            "level_estimate": data.get("level"),
            "items_answered": data.get("count", 0),
            "correct": data.get("correct", 0),
            "reversals": data.get("reversals", 0),
            "converged": data.get("converged", False),
            "level_history": data.get("level_history", []),
        })

    return {
        "ok": True,
        "user_id": user_id,
        "has_placement": True,
        "session_id": latest["session_id"],
        "taken_at": latest["created_at"],
        "applied": bool(latest["used_at"]),
        "skills": skills,
        "summary": _placement_summary(skills),
    }


def _latest_placement(c, user_id):
    """Most recent placement session, collapsed to per-skill level estimates."""
    row = c.execute(
        """SELECT state_json, created_at, used_at
           FROM hebrew_placement_sessions
           WHERE user_id = ?
           ORDER BY created_at DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    try:
        state = json.loads(row["state_json"])
    except (json.JSONDecodeError, TypeError):
        state = {}
    levels = {}
    for skill, data in state.items():
        if isinstance(data, dict) and "level" in data:
            levels[skill] = data["level"]
    return {
        "taken_at": row["created_at"],
        "applied": bool(row["used_at"]),
        "level_estimates": levels,
    }


def _latest_diagnostic(c, user_id):
    """Most recent batch diagnostic (2-3 MC per category pre-assessment)."""
    row = c.execute(
        """SELECT batch_id, question_ids_json, used_at
           FROM hebrew_diagnostic_batches
           WHERE user_id = ?
           ORDER BY expires_at DESC LIMIT 1""",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    try:
        qids = json.loads(row["question_ids_json"])
    except (json.JSONDecodeError, TypeError):
        qids = []
    return {
        "batch_id": row["batch_id"],
        "question_count": len(qids),
        "applied": bool(row["used_at"]),
    }


def _placement_summary(skills):
    """Human-readable one-liner per skill for the LLM."""
    if not skills:
        return "No placement data."
    parts = []
    for s in skills:
        state = "converged" if s["converged"] else ("in progress" if s["items_answered"] else "untouched")
        parts.append(f"{s['skill']}: level {s['level_estimate']} ({state}, {s['items_answered']} items)")
    return "; ".join(parts)
