"""Passage-level connection routes."""

from fastapi import APIRouter
from lib.db import get_db
from lib.api.passage import (
    get_passage_connections,
    get_chapter_connections,
    get_book_summary,
    get_density_clusters,
)

router = APIRouter(prefix="/api/v1")


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
    return result


@router.get("/connections/density")
def density_clusters(book: str = None, min_density: float = 0.3):
    """Find passage clusters above a density threshold."""
    conn = get_db()
    results = get_density_clusters(conn, book=book, min_density=min_density)
    return {"count": len(results), "clusters": results}
