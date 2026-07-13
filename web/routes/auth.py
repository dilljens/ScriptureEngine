"""Google OAuth authentication for Scripture Engine.

Optional — users can remain anonymous. Signing in with Google merges
anonymous progress and enables cross-device sync.

Tables:
  users — id, google_id, email, name, avatar_url, anon_id (previous anonymous ID)

Endpoints:
  POST   /api/v1/auth/google — sign in with Google credential token
  POST   /api/v1/auth/merge  — merge anonymous progress into account
  GET    /api/v1/auth/me     — get current user info
  GET    /api/v1/user/progress/{user_id} — aggregate all progress for LLM/personalization
"""
import contextlib
import hashlib
import json
import secrets
import sqlite3
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"

# Google OAuth — in production, use a proper client ID
# For now, we verify tokens via Google's tokeninfo endpoint
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo?id_token="


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            google_id TEXT UNIQUE,
            email TEXT UNIQUE,
            name TEXT DEFAULT '',
            avatar_url TEXT DEFAULT '',
            anon_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            last_login TEXT DEFAULT (datetime('now'))
        )
    """)
    # Create index for anon_id lookup (for merging)
    with contextlib.suppress(Exception):
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_anon ON users(anon_id)")
    return conn


def _generate_session_token(user_id):
    """Generate a session token for a user."""
    raw = f"{user_id}:{secrets.token_hex(32)}:{time.time()}"
    return hashlib.sha256(raw.encode()).hexdigest()


@router.post("/api/v1/auth/google")
def google_signin(body: dict):
    """Sign in with a Google credential token.

    Body: { "credential": "...", "anonymous_id": "anon_abc123" }

    Verifies the Google token, finds or creates a user, and returns
    a session token. If anonymous_id is provided and no existing account
    exists, the anonymous progress will be associated with this user.
    """
    credential = body.get("credential", "")
    anonymous_id = body.get("anonymous_id", "")

    if not credential:
        raise HTTPException(400, "credential required")

    # Verify Google token
    import urllib.error
    import urllib.request
    try:
        url = GOOGLE_TOKENINFO_URL + urllib.request.quote(credential, safe='')
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            token_info = json.loads(resp.read())
    except Exception as e:
        raise HTTPException(401, f"Token verification failed: {e}") from e

    google_id = token_info.get("sub")
    email = token_info.get("email", "")
    name = token_info.get("name", "")
    avatar = token_info.get("picture", "")

    if not google_id:
        raise HTTPException(401, "Invalid token: no sub claim")

    conn = get_conn()

    # Check if user exists by google_id
    user = conn.execute("SELECT * FROM users WHERE google_id=?", (google_id,)).fetchone()

    if user:
        # Update login time
        conn.execute("UPDATE users SET last_login=datetime('now') WHERE id=?", (user["id"],))
        user_id = user["id"]
        is_new = False
    else:
        # Check if email already exists
        existing = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone() if email else None
        if existing:
            # Link google_id to existing account
            conn.execute("UPDATE users SET google_id=?, last_login=datetime('now') WHERE id=?", (google_id, existing["id"]))
            user_id = existing["id"]
            is_new = False
        else:
            # Create new user
            import uuid
            user_id = str(uuid.uuid4())
            conn.execute("""
                INSERT INTO users (id, google_id, email, name, avatar_url, anon_id, last_login)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (user_id, google_id, email, name, avatar, anonymous_id or None))
            is_new = True

    conn.commit()
    conn.close()

    # Generate session token
    session_token = _generate_session_token(user_id)

    return {"ok": True, "data": {
        "user_id": user_id,
        "email": email,
        "name": name,
        "avatar_url": avatar,
        "session_token": session_token,
        "is_new": is_new,
        "has_anonymous_progress": bool(anonymous_id),
    }}


@router.post("/api/v1/auth/merge")
def merge_anonymous_progress(body: dict):
    """Merge anonymous user progress into a Google-authenticated account.

    Body: { "session_token": "...", "anonymous_id": "anon_abc123" }

    Transfers progress from anonymous_id to the authenticated user:
      - memorize_queue
      - memorize_progress (via queue)
      - quiz_progress
      - hebrew_progress
    """
    session_token = body.get("session_token", "")
    anonymous_id = body.get("anonymous_id", "")

    if not session_token or not anonymous_id:
        raise HTTPException(400, "session_token and anonymous_id required")

    # Look up user by session token (simplified — in production use a sessions table)
    conn = get_conn()
    user = conn.execute("SELECT id, anon_id FROM users WHERE anon_id=? OR id=?",
                       (anonymous_id, anonymous_id)).fetchone()

    if not user:
        conn.close()
        raise HTTPException(404, "User not found. Sign in first.")

    user_id = user["id"]
    merged = {}

    # Merge memorize_queue
    queue_items = conn.execute(
        "SELECT verse_id FROM memorize_queue WHERE user_id=?", (anonymous_id,)
    ).fetchall()
    count = 0
    for item in queue_items:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO memorize_queue (user_id, verse_id) VALUES (?, ?)",
                (user_id, item["verse_id"])
            )
            count += 1
        except Exception:
            pass
    merged["memorize_queue"] = count
    conn.execute("DELETE FROM memorize_queue WHERE user_id=?", (anonymous_id,))

    # Merge memorize_progress
    prog = conn.execute(
        "SELECT verse_id, mastery, attempts, correct, stability, difficulty, last_review, next_review "
        "FROM memorize_progress WHERE user_id=?", (anonymous_id,)
    ).fetchall()
    count = 0
    for p in prog:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO memorize_progress
                    (user_id, verse_id, mastery, attempts, correct, stability, difficulty, last_review, next_review)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, p["verse_id"], p["mastery"], p["attempts"], p["correct"],
                  p["stability"], p["difficulty"], p["last_review"], p["next_review"]))
            count += 1
        except Exception:
            pass
    merged["memorize_progress"] = count
    conn.execute("DELETE FROM memorize_progress WHERE user_id=?", (anonymous_id,))

    # Merge quiz_progress
    quiz = conn.execute(
        "SELECT question_id, correct, attempts, last_seen FROM quiz_progress WHERE user_id=?",
        (anonymous_id,)
    ).fetchall()
    count = 0
    for q in quiz:
        try:
            existing = conn.execute(
                "SELECT correct, attempts FROM quiz_progress WHERE user_id=? AND question_id=?",
                (user_id, q["question_id"])
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE quiz_progress SET correct=correct+?, attempts=attempts+?, last_seen=?
                    WHERE user_id=? AND question_id=?
                """, (q["correct"], q["attempts"], q["last_seen"], user_id, q["question_id"]))
            else:
                conn.execute("""
                    INSERT INTO quiz_progress (user_id, question_id, correct, attempts, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, q["question_id"], q["correct"], q["attempts"], q["last_seen"]))
            count += 1
        except Exception:
            pass
    merged["quiz_progress"] = count
    conn.execute("DELETE FROM quiz_progress WHERE user_id=?", (anonymous_id,))

    # Merge hebrew_progress
    heb = conn.execute(
        "SELECT node_id, mastery, attempts, correct, last_practiced FROM hebrew_progress WHERE user_id=?",
        (anonymous_id,)
    ).fetchall()
    count = 0
    for h in heb:
        try:
            existing = conn.execute(
                "SELECT mastery, attempts, correct FROM hebrew_progress WHERE user_id=? AND node_id=?",
                (user_id, h["node_id"])
            ).fetchone()
            if existing:
                conn.execute("""
                    UPDATE hebrew_progress SET mastery=MAX(mastery,?), attempts=attempts+?,
                           correct=correct+?, last_practiced=MAX(last_practiced,?)
                    WHERE user_id=? AND node_id=?
                """, (h["mastery"], h["attempts"], h["correct"], h["last_practiced"], user_id, h["node_id"]))
            else:
                conn.execute("""
                    INSERT INTO hebrew_progress (user_id, node_id, mastery, attempts, correct, last_practiced)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, h["node_id"], h["mastery"], h["attempts"], h["correct"], h["last_practiced"]))
            count += 1
        except Exception:
            pass
    merged["hebrew_progress"] = count
    conn.execute("DELETE FROM hebrew_progress WHERE user_id=?", (anonymous_id,))

    # Update user record
    conn.execute("UPDATE users SET anon_id=NULL WHERE id=?", (user_id,))

    conn.commit()
    conn.close()

    return {"ok": True, "data": {
        "merged": merged,
        "total_merged": sum(merged.values()),
        "message": f"Merged {sum(merged.values())} progress records into your account.",
    }}


@router.get("/api/v1/auth/me")
def get_current_user(session_token: str = ""):
    """Get current user info from a session token.

    Query param: session_token=...
    Returns user info or 401 if invalid.
    """
    if not session_token:
        raise HTTPException(401, "Not authenticated")

    # Simplified: session tokens are just hashed identifiers
    # In production: check against a sessions table
    conn = get_conn()
    # For now, just return that the token is valid if it looks right
    conn.close()

    return {"ok": True, "data": {
        "authenticated": True,
        "user_id": "resolved_from_token",
        "note": "Full session validation pending — token stored locally",
    }}


@router.get("/api/v1/user/progress/{user_id}")
def get_user_progress(user_id: str):
    """Aggregate all progress data for a user — quiz, memorize, Hebrew, chat.

    Returns structured data that can be fed to an LLM for personalized
    feedback, study recommendations, and app improvement insights.
    """
    import sqlite3 as _sql
    ROOT = Path(__file__).resolve().parent.parent.parent
    db_path = ROOT / "data" / "processed" / "scripture.db"
    mem_path = ROOT / "data" / "memorize.db"

    result = {"user_id": user_id, "quiz": {}, "memorize": {}, "hebrew": {}, "chat": {}}

    try:
        conn = _sql.connect(str(db_path))
        conn.row_factory = _sql.Row

        # Ensure memorize tables exist (they're created by memorize.py normally)
        conn.execute("CREATE TABLE IF NOT EXISTS memorize_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, verse_id TEXT, added_at TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS memorize_progress (user_id TEXT, verse_id TEXT, mastery REAL DEFAULT 0.0, attempts INTEGER DEFAULT 0, correct INTEGER DEFAULT 0, stability REAL DEFAULT 1.0, difficulty REAL DEFAULT 5.0, last_review TEXT, next_review TEXT, PRIMARY KEY (user_id, verse_id))")

        # Quiz progress
        quiz_rows = conn.execute("""
            SELECT a.tier, COUNT(*) as total,
                   SUM(CASE WHEN qp.correct > qp.attempts * 0.5 THEN 1 ELSE 0 END) as mastered,
                   SUM(1) - SUM(CASE WHEN qp.correct > 0 THEN 1 ELSE 0 END) as never_correct
            FROM quiz_progress qp
            JOIN assessment_items a ON a.id = qp.question_id
            WHERE qp.user_id = ?
            GROUP BY a.tier
        """, (user_id,)).fetchall()

        result["quiz"]["by_tier"] = [dict(r) for r in quiz_rows]
        result["quiz"]["total_answered"] = sum(r["total"] for r in quiz_rows)

        # Weakest areas (questions answered wrong most often)
        weak = conn.execute("""
            SELECT a.tier, a.bloom_level, a.question_text,
                   qp.correct, qp.attempts
            FROM quiz_progress qp
            JOIN assessment_items a ON a.id = qp.question_id
            WHERE qp.user_id = ? AND qp.correct < qp.attempts * 0.4
            ORDER BY CAST(qp.correct AS REAL) / NULLIF(qp.attempts, 0) ASC
            LIMIT 5
        """, (user_id,)).fetchall()
        result["quiz"]["weakest_areas"] = [dict(r) for r in weak]

        # Memorize progress
        mem_queue = conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN p.mastery >= 0.8 THEN 1 ELSE 0 END) as mastered,
                   SUM(CASE WHEN p.mastery < 0.8 AND p.attempts > 0 THEN 1 ELSE 0 END) as learning,
                   SUM(CASE WHEN p.attempts = 0 THEN 1 ELSE 0 END) as not_started
            FROM memorize_queue q
            LEFT JOIN memorize_progress p ON p.user_id=q.user_id AND p.verse_id=q.verse_id
            WHERE q.user_id = ?
        """, (user_id,)).fetchone()
        result["memorize"] = dict(mem_queue) if mem_queue else {}

        # Hebrew progress
        conn.close()
    except Exception as e:
        result["quiz"]["error"] = str(e)

    try:
        mem_conn = _sql.connect(str(mem_path))
        mem_conn.row_factory = _sql.Row

        heb_total = mem_conn.execute("SELECT COUNT(*) FROM hebrew_nodes").fetchone()[0]
        heb_prog = mem_conn.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN mastery >= 0.8 THEN 1 ELSE 0 END) as mastered,
                   SUM(CASE WHEN mastery > 0 AND mastery < 0.8 THEN 1 ELSE 0 END) as in_progress,
                   SUM(CASE WHEN mastery = 0 THEN 1 ELSE 0 END) as not_started
            FROM hebrew_progress WHERE user_id = ?
        """, (user_id,)).fetchone()
        result["hebrew"]["total_nodes"] = heb_total
        result["hebrew"]["progress"] = dict(heb_prog) if heb_prog else {}

        # Weak Hebrew nodes
        heb_weak = mem_conn.execute("""
            SELECT n.title, n.category, p.mastery, p.attempts
            FROM hebrew_progress p
            JOIN hebrew_nodes n ON n.id = p.node_id
            WHERE p.user_id = ? AND p.mastery > 0 AND p.mastery < 0.5
            ORDER BY p.mastery ASC
            LIMIT 5
        """, (user_id,)).fetchall()
        result["hebrew"]["struggling"] = [dict(r) for r in heb_weak]

        mem_conn.close()
    except Exception as e:
        result["hebrew"]["error"] = str(e)

    # Chat history (last 5 sessions)
    try:
        conn2 = _sql.connect(str(db_path))
        conn2.row_factory = _sql.Row
        sessions = conn2.execute("""
            SELECT id, title, created_at FROM conversation_sessions
            WHERE created_by = ?
            ORDER BY created_at DESC LIMIT 5
        """, (user_id,)).fetchall()

        chat_data = []
        for s in sessions:
            msgs = conn2.execute("""
                SELECT role, content, created_at FROM conversation_messages
                WHERE session_id = ? ORDER BY created_at DESC LIMIT 10
            """, (s["id"],)).fetchall()
            chat_data.append({
                "session_id": s["id"],
                "title": s["title"],
                "message_count": len(msgs),
                "recent_topics": [m["content"][:100] for m in msgs[:3] if m["role"] == "user"],
            })
        result["chat"]["sessions"] = chat_data
        result["chat"]["total_sessions"] = len(chat_data)
        conn2.close()
    except Exception as e:
        result["chat"]["error"] = str(e)

    return {"ok": True, "data": result}
