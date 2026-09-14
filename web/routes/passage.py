"""Passage-level connection routes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from lib.db import get_db
from lib.api.passage import (
    get_passage_connections,
    get_chapter_connections,
    get_book_summary,
    get_density_clusters,
)

router = APIRouter(prefix="/api/v1")


def _teaching_404(message: str, hint: str | None = None,
                  see: str | None = "/api/v1/orient") -> JSONResponse:
    """Same teaching-404 envelope as the verse/chapter routes (web/server.py):
    {ok, error, detail, hint?, see?} at 404 — one error shape everywhere."""
    body: dict = {"ok": False, "error": message, "detail": message}
    if hint:
        body["hint"] = hint
    if see:
        body["see"] = see
    return JSONResponse(status_code=404, content=body)


@router.get("/passage/{ref}/connections")
def passage_connections(ref: str, min_density: float = 0.0):
    """Get passage-level connections for a verse range."""
    conn = get_db()
    parts = ref.split("-", 1)
    start = parts[0].strip()
    end = parts[1].strip() if len(parts) > 1 else start
    results = get_passage_connections(conn, start, end, min_density=min_density)
    return {"ref": ref, "count": len(results), "connections": results}


@router.get("/chapter/{book}/{chapter}/connections")
def chapter_connections(book: str, chapter: int):
    """Get connection summary for a chapter."""
    conn = get_db()
    result = get_chapter_connections(conn, book, chapter)
    return result


@router.get("/book/{book}/connection-summary")
def book_connection_summary(book: str):
    """Get book-level connection summary."""
    conn = get_db()
    result = get_book_summary(conn, book)
    if isinstance(result, dict) and "error" in result:
        return _teaching_404(
            result["error"],
            hint=("Book ids are short (gen, matt, psa, dc121) — list: /api/v1/books. "
                  "Books with no verses yet report available:false there."),
        )
    return result


@router.get("/connections/density")
def density_clusters(book: str = None, min_density: float = 0.3):
    """Find passage clusters above a density threshold."""
    conn = get_db()
    results = get_density_clusters(conn, book=book, min_density=min_density)
    return {"count": len(results), "clusters": results}
