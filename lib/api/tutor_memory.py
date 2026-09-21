"""Layered Hebrew Tutor memory (plan hebrew-tutor-phase2, Track P2-A).

Layers:
  working     — recent turns of the live request (already in the message
                list; no storage — see chat._prepare_chat_messages).
  transcript  — raw turn archive per session (tutor_transcripts).
  summary     — per-session rollup, explicitly written (tutor_session_summary).
  durable     — learner preferences/goals/pedagogical state (tutor_memory),
                written only via staging + promote with conflict rules:
                an explicit learner correction always beats tutor inference;
                within one source, the latest write wins. Every durable row
                carries evidence + date so long-context answers can cite it.

SQLite + stdlib only. Functions take an explicit conn (unit-testable);
callers open short-lived connections via connect().
"""
import datetime
import sqlite3

try:
    from lib.config import MEMORIZE_DB_PATH as _DEFAULT_MEM_PATH
except ImportError:  # lib.config must never break this module's import
    _DEFAULT_MEM_PATH = None

MEM_DB_PATH = _DEFAULT_MEM_PATH  # monkeypatchable in tests

SOURCES = ("learner", "tutor", "system")
_SOURCE_RANK = {"learner": 3, "tutor": 2, "system": 1}

MAX_CONTENT_CHARS = 2000
MAX_BLOCK_ITEMS = 12


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.datetime.now(datetime.timezone.utc).date().isoformat()


def ensure_tutor_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tutor_memory (
            user_id TEXT NOT NULL DEFAULT 'default',
            key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'tutor',
            evidence TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, key)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tutor_memory_staging (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'tutor',
            evidence TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'staged',
            reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tutor_session_summary (
            session_key TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            summary TEXT NOT NULL DEFAULT '',
            turn_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tutor_transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_key TEXT NOT NULL,
            user_id TEXT NOT NULL DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_tutor_transcripts_session
        ON tutor_transcripts(session_key, id)""")


def connect():
    """Open the tutor store (MEMORIZE_DB_PATH), ensuring schema."""
    if MEM_DB_PATH is None:
        raise RuntimeError("tutor memory store path unavailable")
    conn = sqlite3.connect(str(MEM_DB_PATH))
    conn.row_factory = sqlite3.Row
    ensure_tutor_schema(conn)
    return conn


def _clean_source(source: str) -> str:
    return source if source in SOURCES else "tutor"


def stage_note(conn, user_id: str, key: str, value: str,
               source: str = "tutor", evidence: str = "") -> dict:
    """Stage a candidate memory. Explicit learner corrections auto-promote
    (latest learner word wins immediately); tutor inferences wait for a
    promote call where they face conflict resolution."""
    source = _clean_source(source)
    key = (key or "").strip()[:128]
    if not key or not (value or "").strip():
        raise ValueError("key and value required")
    cur = conn.execute("""
        INSERT INTO tutor_memory_staging
            (user_id, key, value, source, evidence, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'staged', ?)
    """, (user_id or "default", key, value.strip()[:MAX_CONTENT_CHARS],
          source, (evidence or "").strip()[:512], _utcnow()))
    staging_id = cur.lastrowid
    conn.commit()
    if source == "learner":
        promote_note(conn, staging_id, reviewer="auto-learner")
    return {"id": staging_id,
            "status": _staging_status(conn, staging_id)}


def _staging_status(conn, staging_id: int) -> str:
    row = conn.execute("SELECT status FROM tutor_memory_staging WHERE id=?",
                       (staging_id,)).fetchone()
    return row["status"] if row else "missing"


def promote_note(conn, staging_id: int, reviewer: str = "system") -> dict:
    """Resolve one staged note into durable memory.

    Conflict rule: a durable learner-sourced row beats a staged
    tutor/system candidate (rejected as stale/superseded); otherwise the
    candidate wins (latest write per source-priority) and stages to
    'promoted'. Returns {ok, status, reason}."""
    cand = conn.execute(
        "SELECT * FROM tutor_memory_staging WHERE id=?", (staging_id,)).fetchone()
    if not cand:
        return {"ok": False, "status": "missing", "reason": "no such staged note"}
    if cand["status"] != "staged":
        return {"ok": False, "status": cand["status"],
                "reason": "already resolved"}
    existing = conn.execute(
        "SELECT * FROM tutor_memory WHERE user_id=? AND key=?",
        (cand["user_id"], cand["key"])).fetchone()

    if (existing and existing["source"] == "learner"
            and cand["source"] != "learner"):
        reason = (f"superseded by learner correction "
                  f"({existing['updated_at'][:10]}): {reviewer}")
        conn.execute(
            "UPDATE tutor_memory_staging SET status='rejected', reason=? WHERE id=?",
            (reason, staging_id))
        conn.commit()
        return {"ok": True, "status": "rejected",
                "reason": "durable learner correction wins"}

    conn.execute("""
        INSERT INTO tutor_memory (user_id, key, value, source, evidence, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, key) DO UPDATE SET
            value=excluded.value, source=excluded.source,
            evidence=excluded.evidence, updated_at=excluded.updated_at
    """, (cand["user_id"], cand["key"], cand["value"], cand["source"],
          cand["evidence"], _utcnow()))
    conn.execute("UPDATE tutor_memory_staging SET status='promoted', reason=?"
                 " WHERE id=?", (f"promoted by {reviewer}", staging_id))
    conn.commit()
    return {"ok": True, "status": "promoted",
            "reason": "latest write wins"}


def get_memory_block(conn, user_id: str,
                     max_items: int = MAX_BLOCK_ITEMS) -> str:
    """Durable memory rendered for prompt hydration, evidence + date cited."""
    rows = conn.execute("""
        SELECT key, value, source, evidence, updated_at FROM tutor_memory
        WHERE user_id=? ORDER BY updated_at DESC LIMIT ?
    """, (user_id or "default", max_items)).fetchall()
    lines = []
    for r in rows:
        date = (r["updated_at"] or "")[:10]
        ev = f"; evidence: {r['evidence']}" if r["evidence"] else ""
        lines.append(f"[{r['key']}] {r['value']} ({r['source']}, {date}{ev})")
    return "\n".join(lines)


def forget(conn, user_id: str, scope: str = "all") -> dict:
    """'Forget this' surface. scope='all' wipes durable + staging +
    summaries + transcripts; any other scope deletes that one durable key."""
    user_id = user_id or "default"
    if scope == "all":
        counts = {}
        for table, where in (
                ("tutor_memory", "user_id=?"),
                ("tutor_memory_staging", "user_id=?"),
                ("tutor_session_summary", "user_id=?"),
                ("tutor_transcripts", "user_id=?")):
            cur = conn.execute(f"DELETE FROM {table} WHERE {where}", (user_id,))
            counts[table] = cur.rowcount
        conn.commit()
        return {"ok": True, "scope": "all", "deleted": counts}
    cur = conn.execute("DELETE FROM tutor_memory WHERE user_id=? AND key=?",
                       (user_id, scope))
    conn.commit()
    return {"ok": True, "scope": scope, "deleted": {"tutor_memory": cur.rowcount}}


def record_turn(conn, session_key: str, user_id: str,
                role: str, content: str) -> int:
    """Append one raw transcript turn (content truncated)."""
    cur = conn.execute("""
        INSERT INTO tutor_transcripts
            (session_key, user_id, role, content, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_key, user_id or "default", role,
          (content or "")[:MAX_CONTENT_CHARS], _utcnow()))
    conn.commit()
    return cur.lastrowid


def recent_turns(conn, session_key: str, limit: int = 8) -> list:
    rows = conn.execute("""
        SELECT role, content, created_at FROM tutor_transcripts
        WHERE session_key=? ORDER BY id DESC LIMIT ?
    """, (session_key, limit)).fetchall()
    return [dict(r) for r in reversed(rows)]


def write_summary(conn, session_key: str, user_id: str,
                  summary: str, turn_count: int = 0) -> None:
    conn.execute("""
        INSERT INTO tutor_session_summary
            (session_key, user_id, summary, turn_count, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_key) DO UPDATE SET
            summary=excluded.summary, turn_count=excluded.turn_count,
            updated_at=excluded.updated_at
    """, (session_key, user_id or "default", (summary or "")[:MAX_CONTENT_CHARS],
          turn_count, _utcnow()))
    conn.commit()


def get_summary(conn, session_key: str):
    row = conn.execute("SELECT summary, turn_count, updated_at"
                       " FROM tutor_session_summary WHERE session_key=?",
                       (session_key,)).fetchone()
    return dict(row) if row else None


def hydrate(conn, user_id: str, session_key: str = "") -> str:
    """One bounded block for the tutor prompt: durable memory + session
    summary. Empty string when there is nothing to remember."""
    parts = []
    block = get_memory_block(conn, user_id)
    if block:
        parts.append("[TUTOR MEMORY · durable learner state]\n" + block)
    if session_key:
        s = get_summary(conn, session_key)
        if s and s.get("summary"):
            date = (s.get("updated_at") or "")[:10]
            parts.append(f"[SESSION SUMMARY · {date}] {s['summary']}")
    return "\n".join(parts)
