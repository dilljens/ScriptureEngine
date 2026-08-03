"""Come Follow Me + General Conference browse routes (Library study collections)."""

from fastapi import APIRouter, HTTPException
from lib.db import get_db
from lib.api.cfm import cfm_scripture_blocks

router = APIRouter(prefix="/api/v1")

_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}


@router.get("/cfm/collections")
def cfm_collections():
    """Overview of the study collections (counts + available years) for library cards."""
    conn = get_db()
    lessons = conn.execute(
        "SELECT COUNT(*) AS c, MIN(year) AS min_y, MAX(year) AS max_y FROM cfm_lessons"
    ).fetchone()
    talks = conn.execute(
        "SELECT COUNT(*) AS c, MIN(year) AS min_y, MAX(year) AS max_y FROM talks"
    ).fetchone()
    return {
        "ok": True,
        "data": {
            "cfm": {"count": lessons["c"], "years": [lessons["min_y"], lessons["max_y"]]},
            "conference": {"count": talks["c"], "years": [talks["min_y"], talks["max_y"]]},
        },
    }


@router.get("/cfm/lessons")
def cfm_lessons_list(year: int | None = None):
    """List Come Follow Me lessons — grouped client-side by month via date_range."""
    conn = get_db()
    sql = ("SELECT ref_id, year, week_slug, date_range, title, scripture_block, start_date "
           "FROM cfm_lessons")
    params = []
    if year is not None:
        sql += " WHERE year = ?"
        params.append(year)
    sql += " ORDER BY start_date, week_slug"
    rows = conn.execute(sql, params).fetchall()
    return {
        "ok": True,
        "data": {
            "collection": "cfm",
            "count": len(rows),
            "lessons": [dict(r) for r in rows],
        },
    }


@router.get("/cfm/lessons/{ref_id}")
def cfm_lesson_detail(ref_id: str):
    """Full text of one Come Follow Me lesson."""
    conn = get_db()
    r = conn.execute("SELECT * FROM cfm_lessons WHERE ref_id = ?", (ref_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail=f"No lesson {ref_id}")
    return {"ok": True, "data": dict(r)}


@router.get("/cfm/lessons/{ref_id}/scriptures")
def cfm_lesson_scriptures(ref_id: str):
    """Parse a lesson's scripture_block into structured, chapter-resolved references.

    e.g. "Genesis 1–2; Moses 2–3; Abraham 4–5" → blocks with book ids and
    chapter lists, ready for the weekly-study view to fetch passage text.
    """
    conn = get_db()
    res = cfm_scripture_blocks(conn, ref_id)
    if not res["ok"]:
        raise HTTPException(status_code=404, detail=res.get("error", "Not found"))
    return {"ok": True, "data": res}


@router.get("/conference/talks")
def conference_talks_list(year: int | None = None, month: int | None = None):
    """List General Conference talks, newest first."""
    conn = get_db()
    sql = ("SELECT ref_id, year, month, session, speaker, title, date FROM talks")
    params = []
    if year is not None:
        sql += " WHERE year = ?"
        params.append(year)
        if month is not None:
            sql += " AND month = ?"
            params.append(month)
    sql += " ORDER BY year DESC, month DESC, session, ref_id"
    rows = conn.execute(sql, params).fetchall()
    return {
        "ok": True,
        "data": {
            "collection": "conference",
            "count": len(rows),
            "talks": [dict(r) for r in rows],
        },
    }


@router.get("/conference/talks/{ref_id}")
def conference_talk_detail(ref_id: str):
    """Full text of one conference talk."""
    conn = get_db()
    r = conn.execute("SELECT * FROM talks WHERE ref_id = ?", (ref_id,)).fetchone()
    if not r:
        raise HTTPException(status_code=404, detail=f"No talk {ref_id}")
    return {"ok": True, "data": dict(r)}
