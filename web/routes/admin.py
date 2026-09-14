"""Admin/debug/staging/truth-score routes — extracted from server.py."""

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def get_db():
    from lib.db import get_db as _get_db
    return _get_db()


@router.get("/api/v1/staging/connections")
def staging_list_connections(status: str = "pending", layer: str = "", limit: int = 50):
    """List staging connections (proposed by LLM/UI)."""
    try:
        from lib.api.staging import list_staging_connections
        conn = get_db()
        kwargs = {"status": status, "limit": limit}
        if layer:
            kwargs["layer"] = layer
        items = list_staging_connections(conn, **kwargs)
        conn.close()
        return {"ok": True, "data": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/v1/staging/studies")
def staging_list_studies(status: str = "submitted", limit: int = 20):
    """List staging studies (proposed by LLM/UI)."""
    try:
        from lib.api.staging import list_staging_studies
        conn = get_db()
        items = list_staging_studies(conn, status, limit)
        conn.close()
        return {"ok": True, "data": items, "count": len(items)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post("/api/v1/debug/log",
             description="Authenticated client crash reports only. Requires a valid session_token in the body (same session the rest of the user surface uses); anonymous calls get 401. Fields are truncated server-side.")
def client_error_log(data: dict):
    """Store client-side error logs for debugging (authenticated)."""
    try:
        from web.routes.auth import _resolve_user_from_token
        if not _resolve_user_from_token(data.get("session_token") or ""):
            raise HTTPException(status_code=401, detail="Invalid session token")
        conn = get_db()
        conn.execute('CREATE TABLE IF NOT EXISTS client_logs ('
            'id INTEGER PRIMARY KEY AUTOINCREMENT,'
            'level TEXT DEFAULT "error",'
            'message TEXT,'
            'stack TEXT DEFAULT "",'
            'url TEXT DEFAULT "",'
            'user_agent TEXT DEFAULT "",'
            'created_at TEXT DEFAULT (datetime("now"))'
        ')')
        # Truncate: unbounded third-party inserts are a disk/lock problem
        # on a 1.4GB SQLite file before they are anything else.
        msg = str(data.get("message", ""))[:2000]
        stack = str(data.get("stack", "") or data.get("componentStack", ""))[:8000]
        url = str(data.get("url", ""))[:512]
        ua = str(data.get("user_agent", ""))[:512]
        conn.execute(
            "INSERT INTO client_logs (level, message, stack, url, user_agent) VALUES (?,?,?,?,?)",
            (str(data.get("level", "error"))[:20], msg, stack, url, ua)
        )
        conn.commit()
        conn.close()
        return {"ok": True}
    except HTTPException:
        raise
    except Exception:
        return {"ok": False}


@router.get("/api/v1/debug/logs",
              description="Read recent client error logs (may contain URLs/user agents). Requires a valid session_token query param.")
def get_client_logs(limit: int = 50, session_token: str = ""):
    """Get recent client-side error logs (authenticated)."""
    from web.routes.auth import _resolve_user_from_token
    if not _resolve_user_from_token(session_token or ""):
        raise HTTPException(status_code=401, detail="Invalid session token")
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM client_logs ORDER BY created_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return {"ok": True, "data": [dict(r) for r in logs]}


@router.get("/api/v1/debug/check")
def debug_check():
    """Debug endpoint — health summary for development."""
    import os
    import sys
    conn = get_db()
    try:
        verse_count = conn.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
        conn_count = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
        audio_count = 0
        for _root, _dirs, files in os.walk("data/audio/alignments"):
            audio_count = len(files)
    except Exception:
        verse_count = conn_count = audio_count = 0
    conn.close()
    return {"ok": True, "data": {
        "python": sys.version,
        "platform": __import__("platform").platform(),
        "verses": verse_count,
        "connections": conn_count,
        "audio_alignments": audio_count,
        "assets": os.listdir("frontend/dist/assets/") if os.path.isdir("frontend/dist/assets/") else [],
    }}


@router.get("/api/v1/truth-score")
def truth_score(
    q: str = Query("", description="Topic or search term"),
    verse: str = Query("", description="Specific verse to analyze"),
    limit: int = Query(20, description="Max verses per work"),
):
    """Cross-canon consensus scoring.

    For a given topic/verse, shows how each canon treats it:
    - Number of relevant verses per work (FTS5 trigram search)
    - Connection counts, tradition distribution, hermeneutic breakdown
    - Consensus score across canons based on connection graph
    """
    import json
    conn = get_db()

    # If verse specified, analyze it
    if verse:
        # Get connections for this verse
        conns = conn.execute("""
            SELECT layer, type, subtype, strength, confidence, discovered_by,
                   hermeneutic, tradition, source_verse, target_verse
            FROM connections
            WHERE (source_verse = ? OR target_verse = ?) AND deprecated = 0
            ORDER BY strength DESC LIMIT 200
        """, (verse, verse)).fetchall()

        # Tradition distribution
        traditions = {}
        for c in conns:
            t = c["tradition"] or "unknown"
            traditions[t] = traditions.get(t, 0) + 1

        # Hermeneutic breakdown
        hermeneutics = {}
        for c in conns:
            h = c["hermeneutic"] or "linguistic"
            hermeneutics[h] = hermeneutics.get(h, 0) + 1

        conn.close()
        return {"ok": True, "data": {
            "verse": verse,
            "total_connections": len(conns),
            "traditions": traditions,
            "hermeneutics": hermeneutics,
        }}

    # Topic search — find verses mentioning the topic across works
    if q:
        sanitized = q.replace('"', '""')
        # Search across all works using FTS5 trigram
        from lib.api.search import _trigram_search

        ot_results = _trigram_search(conn, sanitized, limit) or []
        # Count per work
        from collections import Counter
        work_counts = Counter()
        for r in ot_results:
            work_counts[r.get("work_id", "unknown")] += 1

        conn.close()
        return {"ok": True, "data": {
            "query": q,
            "total": len(ot_results),
            "per_work": dict(work_counts),
        }}

    conn.close()
    return {"ok": True, "data": {"message": "Specify ?q= or ?verse="}}
