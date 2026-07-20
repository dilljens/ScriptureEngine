"""Joseph Smith teachings JS/ discourses search."""

from fastapi import APIRouter, Query

router = APIRouter()


def get_db():
    from lib.db import get_db as _get_db
    return _get_db()


@router.get("/api/v1/js/search")
def search_js(q: str = "", limit: int = 20, year: int = 0):
    """Search Joseph Smith teachings/discourses."""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, title, source, year FROM js_sources WHERE content LIKE ? ORDER BY year LIMIT ?",
            (f"%{q}%", limit),
        ).fetchall()
    except Exception:
        rows = []
    conn.close()
    return {"ok": True, "data": {
        "results": [dict(r) for r in rows],
        "total": len(rows),
    }}


@router.get("/api/v1/js/text/{text_id}")
def get_js_text(text_id: int):
    """Get full text of a JS teaching/discourse."""
    conn = get_db()
    row = conn.execute("SELECT * FROM js_sources WHERE id = ?", (text_id,)).fetchone()
    conn.close()
    if not row:
        return {"ok": False, "error": "Not found"}
    return {"ok": True, "data": dict(row)}
