"""Knowledge Assessment — direct HTTP endpoints (no LLM needed)."""
import json
import os
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


def get_db():
    from lib.db import get_db as _get_db
    return _get_db()


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
    return {"ok": True, "data": result.get("data", {})}


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
    return {"ok": True, "data": result.get("data", {})}


@router.get("/api/v1/assessment/progress")
def assessment_progress(user_id: str = "default"):
    """Get current assessment progress."""
    from lib.api.assessment import get_progress
    from lib.db import get_db
    conn = get_db()
    result = get_progress(conn, user_id=user_id)
    conn.close()
    return {"ok": True, "data": result}
