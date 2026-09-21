"""Memorization queue and verse review system.

Lets users add verses/chapters to a memorize queue, then reviews them
using spaced repetition (FSRS-5, same algorithm as Hebrew learning).

Endpoints:
  GET  /api/v1/memorize/queue          — list queued verses
  POST /api/v1/memorize/queue           — add a verse to the queue
  DELETE /api/v1/memorize/queue/{id}   — remove from queue
  GET  /api/v1/memorize/review          — get due reviews
  POST /api/v1/memorize/review/{id}    — submit a review rating
"""
import contextlib
import datetime
import hashlib
import logging
import math
import os
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request

from lib.api.fsrs import (
    FSRS_W,
    initial_stability as _fsrs_initial_stability,
    next_difficulty as _fsrs_next_difficulty,
    next_interval as _fsrs_next_interval,
    schedule as _fsrs_schedule,
    stability_after_failure as _fsrs_stability_after_failure,
    stability_after_success as _fsrs_stability_after_success,
    humanize_interval as _humanize_interval,
)

router = APIRouter()
log = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


def _memorize_db_path() -> Path:
    """Resolve the learning database, honoring MEMORIZE_DB_PATH for isolation."""
    override = os.environ.get("MEMORIZE_DB_PATH")
    return Path(override) if override else BASE_DIR / "data" / "memorize.db"


def _require_review_user(
    user_id: str = "default", session_token: str = "", authorization: str = ""
) -> str:
    """Bind aggregate review reads to a session owner."""
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() != "bearer" or not value.strip():
            raise HTTPException(401, "Invalid authorization header")
        session_token = value.strip()
    if session_token:
        from web.routes.auth import _resolve_user_from_token
        resolved = _resolve_user_from_token(session_token)
        if not resolved:
            raise HTTPException(401, "Invalid or expired session token")
        return resolved
    if user_id not in ("", "default", "anonymous"):
        raise HTTPException(401, "session_token required for a user-scoped review")
    return "default"


def _ensure_memorize_schema(conn):
    """Create memorize tables + additive migrations. Idempotent; extracted
    so tests can build the identical schema on an isolated DB."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memorize_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            verse_id TEXT NOT NULL,
            chapter_id TEXT DEFAULT '',
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, verse_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memorize_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            verse_id TEXT NOT NULL,
            mastery REAL DEFAULT 0.0,
            attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            stability REAL DEFAULT 1.0,
            difficulty REAL DEFAULT 5.0,
            fi_re_credit REAL DEFAULT 0.0,
            last_review TEXT,
            next_review TEXT,
            PRIMARY KEY (user_id, verse_id)
        )
    """)
    # Add fi_re_credit column if missing (for existing DBs)
    with contextlib.suppress(Exception):
        conn.execute("ALTER TABLE memorize_progress ADD COLUMN fi_re_credit REAL DEFAULT 0.0")
    # Preview tracking: what help the user used on their last review
    # (first-letter hints vs full text), so confidence ratings can be weighted.
    with contextlib.suppress(Exception):
        conn.execute("ALTER TABLE memorize_progress ADD COLUMN last_preview_mode TEXT DEFAULT 'none'")
    with contextlib.suppress(Exception):
        conn.execute("ALTER TABLE memorize_progress ADD COLUMN last_preview_level INTEGER DEFAULT 0")
    # Queue source: which mode queued the verse ('manual', 'daily_maintenance',
    # ...). Lets per-mode ratings stay auditable via queue+reviews join.
    with contextlib.suppress(Exception):
        conn.execute("ALTER TABLE memorize_queue ADD COLUMN source TEXT DEFAULT 'manual'")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memorize_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            verse_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            effective_rating INTEGER NOT NULL,
            preview_mode TEXT NOT NULL DEFAULT 'none',
            preview_level INTEGER NOT NULL DEFAULT 0,
            reviewed_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    # Per-attempt source: which mode surface produced this rating. Queue rows
    # outlive their source (shared queue), so audit lives on the attempt.
    # (After the CREATE: on a fresh DB the table does not exist yet above.)
    with contextlib.suppress(Exception):
        conn.execute("ALTER TABLE memorize_reviews ADD COLUMN rating_source TEXT DEFAULT 'manual'")


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_memorize_schema(conn)
    return conn


# ── FSRS-5 core lives in lib/api/fsrs.py (single implementation shared
# with the Hebrew scheduler) — imported at the top of this file. ──

def compute_learning_speed(conn, user_id, verse_id):
    """Compute student-topic learning speed from performance history.

    Formula (per Math Academy Ch 29):
      speed = correct_ratio / avg_difficulty_penalty

    Where:
      correct_ratio = correct / max(attempts, 1)
      avg_difficulty_penalty = avg_difficulty / 5.0  (centered at default)

    Returns a float where:
      > 1.0 = fast learning (longer intervals)
      = 1.0 = average learning
      < 1.0 = slow learning (shorter intervals needed)
    """
    prog = conn.execute(
        "SELECT attempts, correct, difficulty FROM memorize_progress WHERE user_id=? AND verse_id=?",
        (user_id, verse_id)
    ).fetchone()

    if not prog or prog["attempts"] < 2:
        return 1.0  # Not enough data — default to average

    correct_ratio = prog["correct"] / max(prog["attempts"], 1)
    difficulty_penalty = prog["difficulty"] / 5.0

    # Speed: higher accuracy = faster; higher difficulty = slower
    speed = (correct_ratio * 1.5) / max(difficulty_penalty, 0.5)

    # Clamp to reasonable range
    return max(0.3, min(3.0, speed))


# ── Preview-aware review (first-letter hints vs full text) ──
# A review card shows the reference plus an optional preview:
#   first_letters — only the first letter of N% of words (levels 25/50/75/100)
#   fade_words    — N% of words shown in FULL, the rest as first letters
#                   (levels 25/50/75/100); the graduated middle stage between
#                   full text and first-letters-only
#   full_text     — the whole verse text
#   none          — reference only, pure recall
# More help = less scheduling credit (Anki honesty: if you read the answer,
# you didn't recall it).

PREVIEW_LEVELS = (0, 25, 50, 75, 100)
PREVIEW_MODES = ("none", "first_letters", "fade_words", "full_text")


def auto_preview_level(mastery: float = 0.0, attempts: int = 0) -> int:
    """Automated first-letter progression: less help as mastery grows."""
    if attempts <= 0:
        return 100
    if mastery < 0.3:
        return 100
    if mastery < 0.5:
        return 75
    if mastery < 0.7:
        return 50
    if mastery < 0.9:
        return 25
    return 0


def next_preview_level(current_level: int = 100, effective_rating: int = 3) -> int:
    """Step the hint level after a review: recall well → less help next time."""
    levels = list(PREVIEW_LEVELS)
    try:
        idx = levels.index(current_level)
    except ValueError:
        idx = len(levels) - 1
    if effective_rating >= 3 and idx > 0:
        return levels[idx - 1]
    if effective_rating <= 2 and idx < len(levels) - 1:
        return levels[idx + 1]
    return levels[idx]


def effective_rating(rating: int, preview_mode: str = "none",
                     preview_level: int = 0) -> int:
    """Weight an Anki-style confidence rating (1-4) by the help used.

    - full_text: seeing the answer caps the rating at Hard (2).
    - fade_words at 100% (≈ full text): caps at Hard (2); any fade level
      shows more than first-letters, so Easy (4) caps down to Good (3).
    - first_letters at 75-100%: heavy hints cap Easy (4) down to Good (3).
    - 0-50% first letters or no preview: full credit.
    """
    rating = max(1, min(4, int(rating or 3)))
    if preview_mode == "full_text":
        return min(rating, 2)
    if preview_mode == "fade_words":
        return min(rating, 2 if (preview_level or 0) >= 100 else 3)
    if preview_mode == "first_letters" and (preview_level or 0) >= 75:
        return min(rating, 3)
    return rating


# ── Scripture Mastery (LDS 100) ──
import json as _json

_MASTERY_CACHE = None


def load_mastery_list() -> list:
    """Load the 100 LDS scripture-mastery passages from data file."""
    global _MASTERY_CACHE
    if _MASTERY_CACHE is None:
        path = BASE_DIR / "data" / "scripture_mastery.json"
        try:
            _MASTERY_CACHE = _json.loads(path.read_text())["passages"]
        except Exception:
            _MASTERY_CACHE = []
    return _MASTERY_CACHE


def parse_verse_spec(spec: str) -> list:
    """Expand '26-27' → [26, 27], '23,26' → [23, 26], '15,20-21' → [15, 20, 21]."""
    verses: set = set()
    for part in str(spec or "").split(","):
        part = part.strip()
        m = part.split("-")
        try:
            if len(m) == 2 and m[0].strip() and m[1].strip():
                for v in range(int(m[0]), int(m[1]) + 1):
                    verses.add(v)
            elif part:
                verses.add(int(part))
        except ValueError:
            continue
    return sorted(verses)


def expand_mastery_entry(entry: dict) -> list:
    """Map a mastery entry to verse ids (<book>.<chapter>.<verse>)."""
    return [
        f"{entry['book']}.{entry['chapter']}.{v}"
        for v in parse_verse_spec(entry.get("verses", ""))
    ]


# ── FIRe (Fractional Implicit Repetition) ──

def get_connected_verses(conn, verse_id, limit=30):
    """Get all verses connected to verse_id via the connection graph."""
    return conn.execute("""
        SELECT target_verse as connected, strength, confidence
        FROM connections WHERE source_verse=? AND deprecated=0 AND target_verse LIKE '%.%.%'
        UNION
        SELECT source_verse as connected, strength, confidence
        FROM connections WHERE target_verse=? AND deprecated=0 AND source_verse LIKE '%.%.%'
        LIMIT ?
    """, (verse_id, verse_id, limit)).fetchall()


def compute_fire_credit(conn, verse_id, rating, decay_days=7):
    """Compute FIRe credit (success) or penalty (failure) and propagate.

    TWO-WAY FIRe:
    SUCCESS (rating >= 3): credit flows DOWNWARD from complex → simpler
      - Reviewing John 1:1 gives credit to Gen 1:1 (simpler, quoted verse)
      - When fi_re_credit >= 1.0, next review is skipped (knocked out)

    FAILURE (rating < 3): penalty flows UPWARD from simpler → complex
      - Failing Gen 1:1 penalizes John 1:1 (complex, depends on Gen 1:1)
      - Stability is reduced, credit is reduced

    Connection strength: from graph (0.0-1.0)
    Complexity proxy: verses with MORE connections are MORE complex
    """
    # Get connections
    connections = get_connected_verses(conn, verse_id)

    # Count connections of the reviewed verse (complexity proxy)
    reviewed_count = conn.execute("""
        SELECT COUNT(*) as c FROM connections
        WHERE (source_verse=? OR target_verse=?) AND deprecated=0
    """, (verse_id, verse_id)).fetchone()["c"]

    now = datetime.datetime.now()

    for c in connections:
        cv = c["connected"]
        if cv == verse_id:
            continue

        conn_strength = (c["strength"] or 0.5) * (c["confidence"] or 0.5)
        if conn_strength < 0.01:
            continue

        # Determine direction: is reviewed verse simpler or more complex?
        cv_count = conn.execute("""
            SELECT COUNT(*) as c FROM connections
            WHERE (source_verse=? OR target_verse=?) AND deprecated=0
        """, (cv, cv)).fetchone()["c"]

        # Get existing progress for connected verse
        prog = conn.execute(
            "SELECT fi_re_credit, stability, difficulty, last_review FROM memorize_progress WHERE user_id='default' AND verse_id=?",
            (cv,)
        ).fetchone()

        if not prog:
            continue

        existing_credit = prog["fi_re_credit"] or 0.0
        existing_stability = prog["stability"] or 1.0

        # Decay existing credit (summer slide: accelerate if overdue)
        if prog["last_review"]:
            try:
                last = datetime.datetime.strptime(prog["last_review"], "%Y-%m-%d %H:%M:%S")
                days_since = (now - last).total_seconds() / 86400.0
                # Summer slide: decay accelerates exponentially with time
                # Base decay is 10%/day, but doubles every 30 days overdue
                slide_factor = 1.0 + (days_since / 30.0)  # 1x at 0 days, 2x at 30 days, etc.
                decay_rate = math.pow(0.9, days_since * slide_factor)
                existing_credit *= decay_rate
            except Exception:
                log.warning("silent_exception", exc_info=True)
                pass

        if rating >= 3:
            # ── SUCCESS: Credit flow complex → simpler ──
            rating_factor = 0.3 if rating == 3 else 0.5
            credit = min(0.5, conn_strength * rating_factor * 0.3)
            if credit < 0.01:
                continue

            new_credit = min(1.0, existing_credit + credit)
            conn.execute(
                "UPDATE memorize_progress SET fi_re_credit=? WHERE user_id='default' AND verse_id=?",
                (round(new_credit, 3), cv)
            )
        else:
            # ── FAILURE: Penalty flow simpler → complex ──
            # Only penalize if the connected verse is MORE complex
            # (has more connections than the reviewed verse)
            if cv_count <= reviewed_count:
                continue  # Don't penalize simpler verses when failing complex ones

            penalty_factor = 1.0 if rating == 1 else 0.3  # Again=full, Hard=partial
            penalty = min(0.5, conn_strength * penalty_factor * 0.5)
            if penalty < 0.01:
                continue

            # Reduce stability: stability /= (1 + penalty)
            new_stability = existing_stability / (1.0 + penalty)

            # Reduce credit
            new_credit = max(0.0, existing_credit - penalty)

            conn.execute(
                "UPDATE memorize_progress SET stability=?, fi_re_credit=? WHERE user_id='default' AND verse_id=?",
                (round(new_stability, 2), round(new_credit, 3), cv)
            )


def get_connection_difficulty(conn, verse_id):
    """Estimate verse difficulty from graph centrality.

    Verses with more connections are more memorable (lower difficulty).
    Verses with fewer connections are harder to remember (higher difficulty).
    Returns a difficulty value (1.0-10.0).
    """
    count = conn.execute("""
        SELECT COUNT(*) as c FROM connections
        WHERE (source_verse=? OR target_verse=?) AND deprecated=0
    """, (verse_id, verse_id)).fetchone()["c"]

    # Map: 0 connections → difficulty 8.0 (very hard)
    #       100+ connections → difficulty 2.0 (very easy)
    if count >= 100:
        return 2.0
    elif count >= 50:
        return 3.0
    elif count >= 20:
        return 4.0
    elif count >= 10:
        return 5.0
    elif count >= 5:
        return 6.0
    elif count >= 2:
        return 7.0
    else:
        return 8.0


def get_graph_centrality(conn, limit=5):
    """Find the most central (best-connected) verses not yet memorized.
    Used for automatic verse selection.
    """
    rows = conn.execute("""
        SELECT source_verse as verse_id, COUNT(*) as conn_count
        FROM connections
        WHERE deprecated=0 AND source_verse LIKE '%.%.%'
        GROUP BY source_verse
        ORDER BY conn_count DESC
        LIMIT ?
    """, (limit,)).fetchall()

    # Filter to verses not already in queue
    results = []
    for r in rows:
        in_queue = conn.execute(
            "SELECT 1 FROM memorize_queue WHERE verse_id=? AND user_id='default'",
            (r["verse_id"],)
        ).fetchone()
        if not in_queue:
            vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
            results.append({
                "verse_id": r["verse_id"],
                "connections": r["conn_count"],
                "text": vt[0][:150] if vt and vt[0] else "",
            })
    return results


@router.get("/api/v1/memorize/queue")
def list_queue(
    user_id: str = "default", session_token: str = "", authorization: str = Header("")
):
    """List all verses in the memorize queue with progress."""
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.id, m.verse_id, m.added_at,
               COALESCE(p.mastery, 0) as mastery,
               COALESCE(p.attempts, 0) as attempts,
               p.last_review, p.next_review,
               p.stability, p.difficulty
        FROM memorize_queue m
        LEFT JOIN memorize_progress p ON p.user_id=m.user_id AND p.verse_id=m.verse_id
        WHERE m.user_id=?
        ORDER BY m.added_at DESC
    """, (user_id,)).fetchall()

    # Fetch verse text for each
    verses = []
    for r in rows:
        vt = conn.execute("SELECT text_english, text_hebrew, text_greek FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
        verses.append({
            "id": r["id"],
            "verse_id": r["verse_id"],
            "text_english": vt["text_english"][:300] if vt and vt["text_english"] else "",
            "text_hebrew": vt["text_hebrew"][:300] if vt and vt["text_hebrew"] else "",
            "text_greek": vt["text_greek"][:300] if vt and vt["text_greek"] else "",
            "added_at": r["added_at"],
            "mastery": r["mastery"],
            "attempts": r["attempts"],
            "last_review": r["last_review"],
            "next_review": r["next_review"],
            "stability": r["stability"],
            "difficulty": r["difficulty"],
        })

    conn.close()
    return {"ok": True, "data": {"verses": verses, "total": len(verses)}}


@router.post("/api/v1/memorize/queue")
def add_to_queue(body: dict, request: Request):
    """Add a verse to the memorize queue."""
    user_id = _require_review_user(
        (body or {}).get("user_id", "default"),
        (body or {}).get("session_token", ""),
        request.headers.get("authorization", ""),
    )
    conn = get_conn()
    verse_id = body.get("verse_id", "")

    if not verse_id:
        conn.close()
        raise HTTPException(400, "verse_id required")

    # Verify verse exists
    vt = conn.execute("SELECT id FROM verses WHERE id=?", (verse_id,)).fetchone()
    if not vt:
        conn.close()
        raise HTTPException(404, f"Verse not found: {verse_id}")

    try:
        conn.execute("""
            INSERT OR IGNORE INTO memorize_queue (user_id, verse_id)
            VALUES (?, ?)
        """, (user_id, verse_id))
        conn.commit()
        # Initialize progress with connection-aware difficulty
        difficulty = get_connection_difficulty(conn, verse_id)
        conn.execute("""
            INSERT OR IGNORE INTO memorize_progress (user_id, verse_id, mastery, attempts, correct, difficulty)
            VALUES (?, ?, 0, 0, 0, ?)
        """, (user_id, verse_id, difficulty))
        conn.commit()
        added = True
    except Exception:
        added = False

    conn.close()
    return {"ok": True, "data": {"verse_id": verse_id, "added": added, "initial_difficulty": difficulty if 'difficulty' in dir() else 5.0}}


@router.delete("/api/v1/memorize/queue/{item_id}")
def remove_from_queue(
    item_id: int, user_id: str = "default", session_token: str = "",
    authorization: str = Header("")
):
    """Remove a verse from the memorize queue."""
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    conn.execute("DELETE FROM memorize_queue WHERE id=? AND user_id=?", (item_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "data": {"removed": True}}


@router.post("/api/v1/memorize/queue/delete-batch")
def delete_batch_from_queue(body: dict, request: Request):
    """Remove multiple verses from the memorize queue in one call.

    Body: { ids: [queue row ids], user_id?, session_token? }.
    Ids are sanitized to positive ints and capped at 500 per call.
    """
    conn = get_conn()
    user_id = _require_review_user(
        body.get("user_id", "default"), body.get("session_token", ""),
        request.headers.get("authorization", ""),
    )
    raw = body.get("ids", [])
    if not isinstance(raw, list):
        conn.close()
        raise HTTPException(400, "ids must be a list")
    clean = []
    for i in raw:
        if isinstance(i, bool):
            continue
        try:
            n = int(i)
        except (TypeError, ValueError):
            continue
        if n > 0:
            clean.append(n)
    clean = clean[:500]
    removed = 0
    if clean:
        placeholders = ",".join("?" for _ in clean)
        cur = conn.execute(
            f"DELETE FROM memorize_queue WHERE id IN ({placeholders}) AND user_id=?",
            (*clean, user_id),
        )
        removed = cur.rowcount
        conn.commit()
    conn.close()
    return {"ok": True, "data": {"removed": removed}}


@router.post("/api/v1/memorize/queue/batch")
def add_chapter_to_queue(body: dict, request: Request):
    """Add verses to the memorize queue — by chapter or by verse range.

    For a full chapter: send { book: "gen", chapter: 1 }
    For a verse range:  send { book: "gen", chapter: 1, verse_start: 1, verse_end: 5 }
    For a single verse: send { book: "gen", chapter: 1, verse_start: 1 }
    """
    conn = get_conn()
    book = body.get("book", "")
    chapter = body.get("chapter", 0)
    verse_start = body.get("verse_start")
    verse_end = body.get("verse_end")
    user_id = _require_review_user(
        body.get("user_id", "default"), body.get("session_token", ""),
        request.headers.get("authorization", ""),
    )

    if not book or not chapter:
        conn.close()
        raise HTTPException(400, "book and chapter required")

    if verse_start:
        # Add a specific verse range
        sql = "SELECT id FROM verses WHERE book_id=? AND chapter=? AND verse>=?"
        params = [book, chapter, verse_start]
        if verse_end:
            sql += " AND verse<=?"
            params.append(verse_end)
        sql += " ORDER BY verse"
    else:
        sql = "SELECT id FROM verses WHERE book_id=? AND chapter=? ORDER BY verse"
        params = [book, chapter]

    verses = conn.execute(sql, params).fetchall()

    added_count = 0
    for v in verses:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO memorize_queue (user_id, verse_id)
                VALUES (?, ?)
            """, (user_id, v["id"]))
            conn.execute("""
                INSERT OR IGNORE INTO memorize_progress (user_id, verse_id)
                VALUES (?, ?)
            """, (user_id, v["id"]))
            added_count += 1
        except Exception:
            log.warning("silent_exception", exc_info=True)
            pass

    conn.commit()
    conn.close()
    return {"ok": True, "data": {
        "book": book, "chapter": chapter,
        "verse_start": verse_start, "verse_end": verse_end,
        "verses_added": added_count,
    }}


@router.get("/api/v1/memorize/review")
def get_due_reviews(
    user_id: str = "default", limit: int = 10, compress: bool = False,
    palace_order: bool = False, session_token: str = "",
    authorization: str = Header("")
):
    """Get due reviews from the memorize queue, ordered by urgency.

    Features:
    - FIRe knock-out: cards with fi_re_credit >= 1.0 are skipped (extend interval)
    - Connection-aware difficulty: shown in response
    - Repetition compression (if compress=True): connected cards grouped together
    - Palace-guided ordering (if palace_order=True): ordered by memory palace loci
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    now = datetime.datetime.now()

    rows = conn.execute("""
        SELECT q.id, q.verse_id, q.source,
               COALESCE(p.mastery, 0) as mastery,
               COALESCE(p.attempts, 0) as attempts,
               COALESCE(p.correct, 0) as correct,
               COALESCE(p.stability, 1.0) as stability,
               COALESCE(p.difficulty, 5.0) as difficulty,
               COALESCE(p.fi_re_credit, 0.0) as fi_re_credit,
               p.last_review
        FROM memorize_queue q
        LEFT JOIN memorize_progress p ON p.user_id=q.user_id AND p.verse_id=q.verse_id
        WHERE q.user_id=?
        ORDER BY p.last_review ASC
        LIMIT ?
    """, (user_id, limit * 2)).fetchall()  # Fetch extra for FIRe knock-out filtering

    reviews = []
    knocked_out = 0
    for r in rows:
        # FIRe knock-out: skip if credit >= 1.0
        fire_credit = r["fi_re_credit"] or 0.0
        if fire_credit >= 1.0:
            knocked_out += 1
            # Extend due date (pretend a 'Good' review happened)
            prog = conn.execute(
                "SELECT stability FROM memorize_progress WHERE user_id=? AND verse_id=?",
                (user_id, r["verse_id"])
            ).fetchone()
            if prog and prog["stability"] > 0:
                interval = _fsrs_next_interval(prog["stability"])
                next_review = (now + datetime.timedelta(days=interval)).strftime("%Y-%m-%d")
                conn.execute(
                    "UPDATE memorize_progress SET fi_re_credit=0.0, last_review=datetime('now'), next_review=? WHERE user_id=? AND verse_id=?",
                    (next_review, user_id, r["verse_id"])
                )
            continue

        # Compute retrievability
        if r["last_review"]:
            try:
                last = datetime.datetime.strptime(r["last_review"], "%Y-%m-%d %H:%M:%S")
                days = (now - last).total_seconds() / 86400.0
                ret = math.exp(-days / r["stability"]) if r["stability"] > 0 else 1.0
            except Exception:
                ret = 0.5
        else:
            ret = 0.0  # Never reviewed — most urgent

        vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
        text = vt[0] if vt else ""

        reviews.append({
            "queue_id": r["id"],
            "verse_id": r["verse_id"],
            "source": r["source"] or "manual",
            "text": text[:300] if text else "",
            "mastery": r["mastery"],
            "attempts": r["attempts"],
            "stability": r["stability"],
            "difficulty": r["difficulty"],
            "fi_re_credit": round(fire_credit, 3),
            "retrievability": round(ret, 3),
            "suggested_preview": auto_preview_level(r["mastery"] or 0.0, r["attempts"] or 0),
        })

    # Sort by retrievability (most forgotten first)
    reviews.sort(key=lambda x: x["retrievability"])

    # Palace-guided ordering: if enabled, order by memory palace loci
    if palace_order:
        try:
            MEM_PATH = _memorize_db_path()
            mconn = sqlite3.connect(str(MEM_PATH))
            mconn.row_factory = sqlite3.Row
            loci_rows = mconn.execute("""
                SELECT l.verse_id, p.name as palace_name, l.label as locus_label
                FROM loci l JOIN palaces p ON p.id=l.palace_id
                WHERE l.verse_id IS NOT NULL
            """).fetchall()
            palace_map = {r["verse_id"]: r for r in loci_rows}
            mconn.close()

            # Add palace info and sort: palace-ordered first, then retrievability
            for r in reviews:
                pi = palace_map.get(r["verse_id"])
                if pi:
                    r["palace"] = pi["palace_name"]
                    r["locus"] = pi["locus_label"]
            # Sort: palace verses first (by palace order), then non-palace by retrievability
            reviews.sort(key=lambda x: (
                0 if x.get("palace") else 1,
                x.get("palace", ""),
                x.get("locus", ""),
                x["retrievability"],
            ))
        except Exception:
            pass  # Palace ordering is optional
    if compress and len(reviews) > 2:
        compressed = []
        used = set()
        for i, r in enumerate(reviews):
            if i in used: continue
            # Find connected cards
            group = [r]
            used.add(i)
            for j in range(i + 1, len(reviews)):
                if j in used: continue
                # Check if connected via graph
                conn_check = conn.execute("""
                    SELECT 1 FROM connections
                    WHERE (source_verse=? AND target_verse=?) OR (source_verse=? AND target_verse=?)
                    LIMIT 1
                """, (r["verse_id"], reviews[j]["verse_id"], reviews[j]["verse_id"], r["verse_id"])).fetchone()
                if conn_check:
                    group.append(reviews[j])
                    used.add(j)
            compressed.append(group)
        # Flatten: connected cards appear consecutively
        reviews = [c for g in compressed for c in g]

    conn.commit()  # Save FIRe knock-out updates
    conn.close()
    return {"ok": True, "data": {"reviews": reviews, "due": len(reviews), "knocked_out": knocked_out}}


@router.get("/api/v1/memorize/review/{queue_id}/intervals")
def preview_intervals(
    queue_id: int, preview_mode: str = "none", preview_level: int = 0,
    user_id: str = "default", session_token: str = "",
    authorization: str = Header(""),
):
    """Preview the next-review interval behind each rating (1-4) for a card.

    Uses the exact FSRS computation submit_review will apply, including the
    preview-help weighting (effective rating), so the labels on Again/Hard/
    Good/Easy are truthful for every preview mode and level.
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    if preview_mode not in PREVIEW_MODES:
        preview_mode = "none"
    try:
        preview_level = int(preview_level or 0)
    except (TypeError, ValueError):
        preview_level = 0
    if preview_level not in PREVIEW_LEVELS:
        preview_level = 0

    conn = get_conn()
    item = conn.execute(
        "SELECT verse_id FROM memorize_queue WHERE id=? AND user_id=?",
        (queue_id, user_id)
    ).fetchone()
    if not item:
        conn.close()
        raise HTTPException(404, "Queue item not found")
    verse_id = item["verse_id"]

    prog = conn.execute(
        "SELECT attempts, stability, difficulty FROM memorize_progress WHERE user_id=? AND verse_id=?",
        (user_id, verse_id)
    ).fetchone()
    learning_speed = compute_learning_speed(conn, user_id, verse_id)

    out = {}
    for rating in (1, 2, 3, 4):
        eff = effective_rating(rating, preview_mode, preview_level)
        if prog:
            stability = max(1.0, prog["stability"])
            difficulty = prog["difficulty"]
        else:
            stability = _fsrs_initial_stability(eff)
            difficulty = 5.0
        speed_adjusted_diff = difficulty / max(learning_speed, 0.3)
        _, _, base_interval = _fsrs_schedule(stability, speed_adjusted_diff, eff)
        interval = max(1, round(base_interval * learning_speed))
        out[str(rating)] = {
            "days": interval,
            "label": _humanize_interval(interval),
            "effective": eff,
        }
    conn.close()
    return {"ok": True, "data": {"queue_id": queue_id, "intervals": out}}


@router.post("/api/v1/memorize/review/{queue_id}")
def submit_review(queue_id: int, body: dict, request: Request):
    """Submit a rating for a review (1=Again, 2=Hard, 3=Good, 4=Easy).

    Accepts the preview help the user used:
      preview_mode: 'none' | 'first_letters' | 'fade_words' | 'full_text'
      preview_level: 0 | 25 | 50 | 75 | 100 (coverage %)
    The Anki-style confidence rating is weighted by that help: reading the
    full text caps the rating at Hard, heavy first-letter hints cap Easy at
    Good. The weighted (effective) rating drives FSRS scheduling.
    """
    user_id = _require_review_user(
        (body or {}).get("user_id", "default"),
        (body or {}).get("session_token", ""),
        request.headers.get("authorization", ""),
    )
    rating = max(1, min(4, body.get("rating", 3)))
    preview_mode = body.get("preview_mode", "none")
    if preview_mode not in PREVIEW_MODES:
        preview_mode = "none"
    try:
        preview_level = int(body.get("preview_level", 0) or 0)
    except (TypeError, ValueError):
        preview_level = 0
    if preview_level not in PREVIEW_LEVELS:
        preview_level = 0
    eff = effective_rating(rating, preview_mode, preview_level)

    conn = get_conn()
    item = conn.execute(
        "SELECT verse_id, source FROM memorize_queue WHERE id=? AND user_id=?",
        (queue_id, user_id)
    ).fetchone()

    if not item:
        conn.close()
        raise HTTPException(404, "Queue item not found")

    verse_id = item["verse_id"]
    queue_source = item["source"] or "manual"
    # Rating surface override (e.g. audio UI rating a manually-queued verse):
    # the attempt is audited under the surface that produced it.
    claimed = (body.get("source") or "").strip()
    rating_source = claimed[:64] if claimed else queue_source

    # Get current progress
    prog = conn.execute(
        "SELECT mastery, attempts, correct, stability, difficulty FROM memorize_progress WHERE user_id=? AND verse_id=?",
        (user_id, verse_id)
    ).fetchone()

    if prog:
        a, c = prog["attempts"], prog["correct"]
        stability = max(1.0, prog["stability"])
        difficulty = prog["difficulty"]
    else:
        a, c = 0, 0
        stability = _fsrs_initial_stability(eff)
        difficulty = 5.0

    # FSRS update with student-topic learning speed
    learning_speed = compute_learning_speed(conn, user_id, verse_id)

    # Adjust difficulty by learning speed (Math Academy Ch 29):
    # Fast learners get lower effective difficulty, slow learners higher
    speed_adjusted_diff = difficulty / max(learning_speed, 0.3)

    new_s, new_d, base_interval = _fsrs_schedule(stability, speed_adjusted_diff, eff)

    # Apply learning speed to interval
    interval = max(1, round(base_interval * learning_speed))

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    next_review = (datetime.datetime.now() + datetime.timedelta(days=interval)).strftime("%Y-%m-%d")

    a += 1
    c += 1 if eff >= 3 else 0
    mastery = min(1.0, c / max(a, 1))

    conn.execute("""
        INSERT OR REPLACE INTO memorize_progress
            (user_id, verse_id, mastery, attempts, correct, stability, difficulty, fi_re_credit, last_review, next_review, last_preview_mode, last_preview_level)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?)
    """, (user_id, verse_id, round(mastery, 3), a, c, round(new_s, 2), round(new_d, 2), now_str, next_review, preview_mode, preview_level))
    conn.execute("""
        INSERT INTO memorize_reviews
            (user_id, verse_id, rating, effective_rating, preview_mode, preview_level, rating_source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, verse_id, rating, eff, preview_mode, preview_level, rating_source))

    # Unified FIRe credit propagation: verse review → credit to connected verses,
    # Hebrew concepts in this verse, and related learning modules
    with contextlib.suppress(Exception):
        from lib.api.fire_unified import compute_fire_credit as fire_unified
        fire_unified(conn, "verse", verse_id, eff, user_id)

    conn.commit()
    conn.close()

    return {"ok": True, "data": {
        "verse_id": verse_id, "source": queue_source,
        "rating_source": rating_source,
        "mastery": round(mastery, 3),
        "stability": round(new_s, 2), "difficulty": round(new_d, 2),
        "interval": interval, "next_review": next_review,
        "fi_re_credit_propagated": True,
        "rating": rating, "effective_rating": eff,
        "preview_adjusted": eff != rating,
        "next_preview_level": next_preview_level(
            preview_level if preview_mode == "first_letters" else auto_preview_level(mastery, a),
            eff,
        ),
    }}


@router.get("/api/v1/memorize/suggest")
def suggest_verses(limit: int = 5, user_id: str = "default"):
    """Suggest verses to memorize based on graph centrality.

    Finds well-connected verses not yet in the queue — these are
    high-value verses that will unlock many connections.
    """
    conn = get_conn()
    results = get_graph_centrality(conn, limit=limit)
    conn.close()
    return {"ok": True, "data": {"suggestions": results, "total": len(results)}}


# ── Scripture Mastery (LDS 100) ──

@router.get("/api/v1/memorize/mastery")
def list_mastery(user_id: str = "default", session_token: str = "",
                 authorization: str = Header("")):
    """List the 100 LDS scripture-mastery passages with queue/availability status.

    Some passages span multiple verses (e.g. Exodus 20:3-17); each verse is
    imported individually.
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    passages = []
    for entry in load_mastery_list():
        verse_ids = expand_mastery_entry(entry)
        existing = 0
        queued = 0
        if verse_ids:
            q = f"SELECT id FROM verses WHERE id IN ({','.join('?' * len(verse_ids))})"
            existing = len(conn.execute(q, verse_ids).fetchall())
            q2 = (f"SELECT verse_id FROM memorize_queue WHERE user_id=? AND verse_id "
                  f"IN ({','.join('?' * len(verse_ids))})")
            queued = len(conn.execute(q2, [user_id, *verse_ids]).fetchall())
        passages.append({
            "n": entry["n"], "group": entry["group"],
            "reference": entry["reference"], "verse_ids": verse_ids,
            "verses_total": len(verse_ids), "verses_available": existing,
            "verses_queued": queued,
            "available": existing == len(verse_ids) and len(verse_ids) > 0,
        })
    conn.close()
    groups = {}
    for p in passages:
        groups.setdefault(p["group"], []).append(p)
    return {"ok": True, "data": {
        "passages": passages, "total": len(passages),
        "by_group": {g: len(v) for g, v in groups.items()},
    }}


@router.post("/api/v1/memorize/queue/mastery")
def add_mastery_to_queue(body: dict, request: Request):
    """Bulk-add scripture-mastery passages to the memorize queue.

    Body: { group?: "Old Testament" | "New Testament" | "Book of Mormon" |
                    "Doctrine and Covenants",
            refs?: ["Genesis 1:26-27", ...] (reference strings, optional filter) }
    Omit both to import all 100. Multi-verse passages add each verse
    individually. Reports added vs skipped (already queued / not in library).
    """
    user_id = _require_review_user(
        (body or {}).get("user_id", "default"),
        (body or {}).get("session_token", ""),
        request.headers.get("authorization", ""),
    )
    group = (body or {}).get("group", "")
    refs = set((body or {}).get("refs", []) or [])

    conn = get_conn()
    added_verses = 0
    added_entries = 0
    skipped = []
    for entry in load_mastery_list():
        if group and entry["group"] != group:
            continue
        if refs and entry["reference"] not in refs:
            continue
        verse_ids = expand_mastery_entry(entry)
        found = {r[0] for r in conn.execute(
            f"SELECT id FROM verses WHERE id IN ({','.join('?' * len(verse_ids))})",
            verse_ids,
        ).fetchall()} if verse_ids else set()
        missing = [v for v in verse_ids if v not in found]
        if missing:
            skipped.append({"reference": entry["reference"],
                            "reason": "not in library",
                            "missing": missing})
            continue
        entry_added = 0
        for vid in verse_ids:
            cur = conn.execute(
                "INSERT OR IGNORE INTO memorize_queue (user_id, verse_id) VALUES (?, ?)",
                (user_id, vid),
            )
            if cur.rowcount:
                added_verses += 1
                entry_added += 1
            difficulty = get_connection_difficulty(conn, vid)
            conn.execute("""
                INSERT OR IGNORE INTO memorize_progress (user_id, verse_id, mastery, attempts, correct, difficulty)
                VALUES (?, ?, 0, 0, 0, ?)
            """, (user_id, vid, difficulty))
        if entry_added:
            added_entries += 1
        elif verse_ids:
            skipped.append({"reference": entry["reference"],
                            "reason": "already queued"})
    conn.commit()
    conn.close()
    return {"ok": True, "data": {
        "verses_added": added_verses, "entries_added": added_entries,
        "skipped": skipped,
    }}


# ── Macro-Interleaving ──

@router.get("/api/v1/review/interleaved")
def get_interleaved_reviews(
    user_id: str = "default", limit: int = 15, session_token: str = "",
    authorization: str = Header("")
):
    """Get interleaved reviews from ALL areas: memorize + hebrew + learn.

    Implements Math Academy's macro-interleaving (Ch 19):
    - Pulls due cards from memorize queue, hebrew review queue, and learn review
    - Interleaves them: no more than 2 consecutive from same area
    - Returns a mixed session for maximum retention
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    now = datetime.datetime.now()
    all_cards = []

    # 1. Memorize cards
    conn = get_conn()
    rows = conn.execute("""
        SELECT q.id, q.verse_id, 'memorize' as source,
               COALESCE(p.mastery, 0) as mastery,
               COALESCE(p.attempts, 0) as attempts,
               COALESCE(p.stability, 1.0) as stability,
               COALESCE(p.fi_re_credit, 0.0) as fi_re_credit,
               p.last_review
        FROM memorize_queue q
        LEFT JOIN memorize_progress p ON p.user_id=q.user_id AND p.verse_id=q.verse_id
        WHERE q.user_id=? AND (p.fi_re_credit IS NULL OR p.fi_re_credit < 1.0)
        ORDER BY p.last_review ASC LIMIT ?
    """, (user_id, limit)).fetchall()
    for r in rows:
        vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
        retro = 0.0
        if r["last_review"]:
            try:
                last = datetime.datetime.strptime(r["last_review"], "%Y-%m-%d %H:%M:%S")
                days = (now - last).total_seconds() / 86400.0
                retro = math.exp(-days / r["stability"]) if r["stability"] > 0 else 1.0
            except Exception:
                retro = 0.5
        all_cards.append({
            "id": f"mem_{r['id']}", "verse_id": r["verse_id"],
            "text": (vt[0] or "")[:200] if vt else "",
            "source": "memorize", "retrievability": round(retro, 3),
        })

    # 2. Hebrew review cards (from memorize.db)
    try:
        MEM_PATH = _memorize_db_path()
        mconn = sqlite3.connect(str(MEM_PATH))
        mconn.row_factory = sqlite3.Row
        heb_rows = mconn.execute("""
            SELECT h.id, h.title, h.category, h.level,
                   COALESCE(p.mastery, 0) as mastery,
                   p.last_practiced as last_review
            FROM hebrew_nodes h
            LEFT JOIN hebrew_progress p ON p.node_id=h.id AND p.user_id=?
            WHERE p.mastery < 0.8
            ORDER BY p.last_practiced ASC LIMIT ?
        """, (user_id, limit // 2)).fetchall()
        for r in heb_rows:
            all_cards.append({
                "id": f"heb_{r['id']}", "verse_id": r["id"],
                "text": (r["title"] or "") + f" ({r['category']})",
                "source": "hebrew", "retrievability": 0.5,
            })
        mconn.close()
    except Exception:
        log.warning("silent_exception", exc_info=True)
        pass

    # 3. Learn module review cards
    try:
        lconn = get_conn()
        lrows = lconn.execute("""
            SELECT m.id, m.title, COALESCE(p.mastery, 0) as mastery
            FROM learning_modules m
            LEFT JOIN learning_progress p ON p.module_id=m.id AND p.user_id=?
            WHERE p.mastery < 0.8 AND p.attempts > 0
            ORDER BY p.last_review ASC LIMIT ?
        """, (user_id, limit // 3)).fetchall()
        for r in lrows:
            all_cards.append({
                "id": f"learn_{r['id']}", "verse_id": r["id"],
                "text": r["title"] or "",
                "source": "learning", "retrievability": 0.5,
            })
        lconn.close()
    except Exception:
        log.warning("silent_exception", exc_info=True)
        pass

    # Interleave: no more than 2 consecutive from same source
    # Sort by retrievability first, then interleave by source
    all_cards.sort(key=lambda x: x["retrievability"])

    interleaved = []
    last_source = None
    consecutive = 0

    # Round-robin interleaving with max 2 consecutive
    remaining = all_cards.copy()
    while remaining:
        best_idx = 0
        best_retro = float('inf')
        for i, card in enumerate(remaining):
            if card["source"] == last_source and consecutive >= 2:
                continue
            if card["retrievability"] < best_retro:
                best_retro = card["retrievability"]
                best_idx = i

        chosen = remaining.pop(best_idx)

        if chosen["source"] == last_source:
            consecutive += 1
        else:
            consecutive = 1
            last_source = chosen["source"]

        interleaved.append(chosen)

    conn.close()
    return {"ok": True, "data": {"reviews": interleaved, "total": len(interleaved)}}


# ── Non-Interference ──

def get_non_interference_distance(conn, verse_a, verse_b):
    """Check if two verses would interfere with each other if reviewed near each other.

    Interference occurs when:
    - They share rare words (fewer than 10 occurrences in the canon)
    - They have similar themes (high connection overlap)
    - They are from confusable Hebrew word pairs

    Returns a score 0.0-1.0 where higher = more interference.
    """
    # Check if connected via the graph with high strength
    conn_row = conn.execute("""
        SELECT strength FROM connections
        WHERE ((source_verse=? AND target_verse=?) OR (source_verse=? AND target_verse=?))
        AND strength > 0.7
        LIMIT 1
    """, (verse_a, verse_b, verse_b, verse_a)).fetchone()
    if conn_row:
        return conn_row["strength"] * 0.5  # High similarity = some interference

    # Check hebrew_confusability (from memorize.db)
    try:
        MEM_PATH = _memorize_db_path()
        mconn = sqlite3.connect(str(MEM_PATH))
        row = mconn.execute(
            "SELECT strength FROM hebrew_confusability WHERE (node_a=? AND node_b=?) OR (node_a=? AND node_b=?)",
            (verse_a, verse_b, verse_b, verse_a)
        ).fetchone()
        mconn.close()
        if row:
            return row[0]
    except Exception:
        log.warning("silent_exception", exc_info=True)
        pass

    return 0.0


@router.get("/api/v1/review/next")
def get_next_review(
    user_id: str = "default", last_verse: str = "", session_token: str = "",
    authorization: str = Header("")
):
    """Get the next review card, respecting non-interference.

    Ensures the next card doesn't interfere with the last one reviewed.
    Avoids scheduling confusable pairs consecutively.
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()

    # Get next due card from memorize queue
    rows = conn.execute("""
        SELECT q.id, q.verse_id, COALESCE(p.fi_re_credit, 0.0) as fire,
                COALESCE(p.stability, 1.0) as stability, p.last_review,
                COALESCE(p.mastery, 0) as mastery, COALESCE(p.attempts, 0) as attempts
        FROM memorize_queue q
        LEFT JOIN memorize_progress p ON p.user_id=q.user_id AND p.verse_id=q.verse_id
        WHERE q.user_id=? AND (p.fi_re_credit IS NULL OR p.fi_re_credit < 1.0)
        ORDER BY p.last_review ASC LIMIT 5
    """, (user_id,)).fetchall()

    # Pick the first card that doesn't interfere with last_verse
    chosen = None
    for r in rows:
        if last_verse:
            interference = get_non_interference_distance(conn, last_verse, r["verse_id"])
            if interference > 0.4:
                continue  # Skip this card — would interfere
        chosen = r
        break

    if not chosen:
        conn.close()
        return {"ok": True, "data": {"review": None, "message": "No non-interfering cards due"}}

    vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (chosen["verse_id"],)).fetchone()
    text = vt[0] if vt else ""

    conn.close()
    return {"ok": True, "data": {"review": {
        "queue_id": chosen["id"],
        "verse_id": chosen["verse_id"],
        "text": text[:300] if text else "",
        "suggested_preview": auto_preview_level(chosen["mastery"] or 0.0, chosen["attempts"] or 0),
    }}}


# ── Targeted Remediation ──

@router.get("/api/v1/review/weakest")
def get_weakest_reviews(
    user_id: str = "default", limit: int = 5, session_token: str = "",
    authorization: str = Header("")
):
    """Get cards where the user is weakest for targeted remediation.

    Implements Math Academy's targeted remediation (Ch 21):
    - Identifies verses with lowest accuracy rates
    - Prioritizes verses with most failed attempts
    - Returns targeted mini-session for weak areas
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()

    rows = conn.execute("""
        SELECT q.id, q.verse_id,
               p.mastery, p.attempts, p.correct, p.stability, p.difficulty,
               (p.attempts - p.correct) as failures,
               CAST(p.correct AS REAL) / NULLIF(p.attempts, 0) as accuracy
        FROM memorize_queue q
        JOIN memorize_progress p ON p.user_id=q.user_id AND p.verse_id=q.verse_id
        WHERE q.user_id=? AND p.attempts > 0
          AND (p.fi_re_credit IS NULL OR p.fi_re_credit < 1.0)
        ORDER BY accuracy ASC, failures DESC, p.stability ASC
        LIMIT ?
    """, (user_id, limit)).fetchall()

    results = []
    for r in rows:
        vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
        text = vt[0] if vt else ""
        results.append({
            "queue_id": r["id"],
            "verse_id": r["verse_id"],
            "text": text[:300] if text else "",
            "accuracy": round(r["accuracy"] * 100, 1) if r["accuracy"] else 0,
            "attempts": r["attempts"],
            "failures": r["failures"],
            "stability": r["stability"],
            "difficulty": r["difficulty"],
        })

    conn.close()
    return {"ok": True, "data": {"reviews": results, "total": len(results)}}


# ── Track E1: single mode registry / capability matrix ─────────────────────
# One discoverable list of every memorization mode, what backs it, and its
# live status, so the dashboard can show all modes with due counts instead of
# users discovering surfaces by accident.

_MODE_STATUSES = ("available", "partial", "planned")


def _mode_registry() -> list:
    """Static capability matrix. Statuses are honest, not aspirational:
      available — route + queue + rating flow all work today
      partial   — backend exists but UI/flow incomplete
      planned   — on the roadmap (see docs/plans/hebrew-tutor-phase2.md)
    """
    return [
        {"id": "scripture_queue", "label": "Scripture verse queue",
         "surface": "/api/v1/memorize/queue", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "interleaved_review", "label": "Interleaved review",
         "surface": "/api/v1/review/interleaved", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "palace_walk", "label": "Memory palace walk",
         "surface": "/api/v1/review/interleaved?palace_order=true",
         "scheduler": "fsrs-5", "status": "available"},
        {"id": "weakest_first", "label": "Weakest-first review",
         "surface": "/api/v1/review/weakest", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "next_best", "label": "Next-best review",
         "surface": "/api/v1/review/next", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "hebrew_review", "label": "Hebrew review queue",
         "surface": "/api/v1/hebrew/review-queue", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "hebrew_quiz_practice",
         "label": "Hebrew quiz-in-lesson practice",
         "surface": "/api/v1/hebrew/lesson/{node_id}/quiz",
         "scheduler": "fsrs-5 (via /hebrew/progress)", "status": "available"},
        {"id": "progressive_hints", "label": "Progressive hints (first-letter 25/50/75/100% + full text)",
         "surface": "/api/v1/memorize/review (preview_mode/preview_level)",
         "scheduler": "fsrs-5", "status": "available"},
        {"id": "audio_mode", "label": "Audio review mode",
         "surface": "/api/v1/memorize/audio/next", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "hebrew_cloze", "label": "Hebrew cloze deletion cards",
         "surface": "/api/v1/hebrew/cloze/next", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "two_way_translation", "label": "Two-way translation cards",
         "surface": "/api/v1/hebrew/translation/next", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "daily_maintenance", "label": "Daily maintenance / verse of day",
         "surface": "/api/v1/memorize/daily", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "audio_first_commute", "label": "Audio-first commute mode",
         "surface": "/api/v1/memorize/commute", "scheduler": "fsrs-5",
         "status": "available"},
        {"id": "hebrew_visual_only", "label": "Hebrew-only visual mode",
         "surface": "/api/v1/hebrew/visual/next", "scheduler": "fsrs-5",
         "status": "available"},
    ]


@router.get("/api/v1/memorize/modes")
def list_memorize_modes():
    """Capability matrix for every memorization mode (plan Track E1)."""
    queued = None
    try:
        # NOTE: the queue lives in DB_PATH (scripture.db) via get_conn() —
        # not in _memorize_db_path(). Counting anywhere else stays null.
        conn = get_conn()
        try:
            queued = conn.execute(
                "SELECT COUNT(*) FROM memorize_queue").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.Error:
        pass  # queue table not created yet — totals stay null, modes still list
    return {
        "ok": True,
        "data": {
            "modes": _mode_registry(),
            "scheduler": "fsrs-5",
            "totals": {"scripture_queued": queued},
        },
    }


# ── Daily maintenance (P2-B: daily_maintenance mode) ────────────────────
# One deterministic verse per calendar day, enqueued with
# source='daily_maintenance' so its ratings stay auditable via the
# queue+reviews join. Rating flows through the unified submit endpoint
# (POST /api/v1/memorize/review/{queue_id}) — no second scheduler.

DAILY_SOURCE = "daily_maintenance"


def daily_verse_offset(day_str: str, count: int) -> int:
    """Deterministic rotation offset: same date → same verse."""
    digest = hashlib.sha256(day_str.encode("utf-8")).hexdigest()
    return int(digest, 16) % max(count, 1)


def _resolve_daily_date(day: str = "") -> str:
    """Accept YYYY-MM-DD (for tests/backfill); garbage falls back to today."""
    if day:
        try:
            return datetime.date.fromisoformat(day).isoformat()
        except ValueError:
            pass
    return datetime.date.today().isoformat()


@router.get("/api/v1/memorize/daily")
def get_daily_verse(user_id: str = "default", day: str = "",
                    session_token: str = "", authorization: str = Header("")):
    """Today's maintenance verse, enqueued for FSRS review.

    Deterministic per calendar day (same date → same verse for everyone;
    per-user queue rows). Returns the queue_id so the client rates it
    through the unified review submit endpoint.
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    day_str = _resolve_daily_date(day)
    conn = get_conn()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM verses WHERE text_hebrew IS NOT NULL"
        ).fetchone()[0]
        if not count:
            raise HTTPException(404, "No verses available for daily maintenance")
        row = conn.execute("""
            SELECT id, book_id, chapter, verse, text_english
            FROM verses WHERE text_hebrew IS NOT NULL
            ORDER BY rowid LIMIT 1 OFFSET ?
        """, (daily_verse_offset(day_str, count),)).fetchone()
        verse_id = row["id"]
        qid, qsource = _ensure_queued(conn, user_id, verse_id, DAILY_SOURCE)
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "data": {
        "date": day_str,
        "verse": {
            "id": verse_id,
            "book_id": row["book_id"],
            "chapter": row["chapter"],
            "verse": row["verse"],
            "text": row["text_english"][:500],
        },
        "queue_id": qid,
        "source": qsource,
    }}


def _ensure_queued(conn, user_id: str, verse_id: str, source: str):
    """Ensure a queue+progress row exists; return (queue_id, source).

    Existing rows keep their original source (a manually-queued verse is
    not rebranded by the mode that happens to serve it)."""
    conn.execute(
        "INSERT OR IGNORE INTO memorize_queue (user_id, verse_id, source)"
        " VALUES (?, ?, ?)",
        (user_id, verse_id, source),
    )
    conn.execute(
        "INSERT OR IGNORE INTO memorize_progress"
        " (user_id, verse_id, mastery, attempts, correct, difficulty)"
        " VALUES (?, ?, 0.0, 0, 0, 5.0)",
        (user_id, verse_id),
    )
    q = conn.execute(
        "SELECT id, source FROM memorize_queue WHERE user_id=? AND verse_id=?",
        (user_id, verse_id),
    ).fetchone()
    return q["id"], (q["source"] or "manual")


# ── Audio review + commute + analytics (P2-B) ──────────────────────────
# Audio modes ride the shared memorize queue filtered to verses that have
# read-along alignment audio (canonical player endpoints live in
# web/routes/audio.py). Ratings flow through the unified submit with a
# source override — no second scheduler.

# Mirrors web/routes/audio.py ALIGN_DIR (kept local: memorize must not
# import route modules at top level).
AUDIO_ALIGN_DIR = BASE_DIR / "data" / "audio" / "alignments"

_AUDIO_VERSE_IDS = None


def _audio_verse_ids():
    """Verse ids with read-along alignment audio. Built once per process."""
    global _AUDIO_VERSE_IDS
    if _AUDIO_VERSE_IDS is None:
        ids = set()
        try:
            import re as _re
            for f in AUDIO_ALIGN_DIR.glob("*.json"):
                base = _re.sub(r"_(cloned|hybrid|ivrit|shmuelof)$", "", f.stem)
                ids.add(base)
        except OSError:
            pass
        _AUDIO_VERSE_IDS = ids
    return _AUDIO_VERSE_IDS


def _audio_urls(verse_id: str) -> dict:
    return {
        "play": f"/api/v1/audio/play/{verse_id}",
        "align": f"/api/v1/audio/align/{verse_id}",
    }


def _due_audio_rows(conn, user_id: str, limit: int):
    """Due queue items (never reviewed or least-recently reviewed first)
    restricted to verses with alignment audio."""
    rows = conn.execute("""
        SELECT q.id, q.verse_id, q.source, v.text_english,
               COALESCE(p.last_review, '') as last_review
        FROM memorize_queue q
        LEFT JOIN memorize_progress p
          ON p.user_id=q.user_id AND p.verse_id=q.verse_id
        JOIN verses v ON v.id=q.verse_id
        WHERE q.user_id=?
        ORDER BY last_review ASC LIMIT ?
    """, (user_id, max(limit * 4, limit))).fetchall()
    audio_ids = _audio_verse_ids()
    return [r for r in rows if r["verse_id"] in audio_ids][:limit]


@router.get("/api/v1/memorize/audio/next")
def get_audio_next(user_id: str = "default", limit: int = 10,
                   session_token: str = "", authorization: str = Header("")):
    """Due queue items that have read-along audio. Rate each through the
    unified submit with {"source": "audio_mode"}."""
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    try:
        items = [{
            "queue_id": r["id"], "verse_id": r["verse_id"],
            "source": r["source"] or "manual",
            "text": (r["text_english"] or "")[:300],
            "audio": _audio_urls(r["verse_id"]),
        } for r in _due_audio_rows(conn, user_id, max(1, min(limit, 50)))]
    finally:
        conn.close()
    return {"ok": True, "data": {"items": items, "count": len(items)}}


@router.get("/api/v1/memorize/commute")
def get_commute_playlist(user_id: str = "default", limit: int = 10,
                         day: str = "", session_token: str = "",
                         authorization: str = Header("")):
    """Audio-first commute playlist: due-with-audio items in review order,
    then today's daily verse. The client auto-advances and rates every
    stop through the unified submit with {"source": "audio_first_commute"};
    each rating lands as a review event (no separate commute scheduler)."""
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    try:
        stops = [{
            "queue_id": r["id"], "verse_id": r["verse_id"],
            "kind": "due", "source": r["source"] or "manual",
            "text": (r["text_english"] or "")[:300],
            "audio": _audio_urls(r["verse_id"]),
        } for r in _due_audio_rows(conn, user_id, max(1, min(limit, 50)))]
        day_str = _resolve_daily_date(day)
        count = conn.execute(
            "SELECT COUNT(*) FROM verses WHERE text_hebrew IS NOT NULL").fetchone()[0]
        if count:
            row = conn.execute("""
                SELECT id, text_english FROM verses
                WHERE text_hebrew IS NOT NULL
                ORDER BY rowid LIMIT 1 OFFSET ?
            """, (daily_verse_offset(day_str, count),)).fetchone()
            has_audio = row["id"] in _audio_verse_ids()
            dqid, dqsource = _ensure_queued(conn, user_id, row["id"], DAILY_SOURCE)
            conn.commit()
            stops.append({
                "queue_id": dqid, "verse_id": row["id"], "kind": "daily",
                "source": dqsource,
                "text": (row["text_english"] or "")[:300],
                "audio": _audio_urls(row["id"]) if has_audio else None,
            })
    finally:
        conn.close()
    return {"ok": True, "data": {"date": day_str, "stops": stops,
                                 "count": len(stops)}}


@router.get("/api/v1/memorize/analytics")
def get_memorize_analytics(user_id: str = "default", session_token: str = "",
                           authorization: str = Header("")):
    """Retention, due workload, per-mode performance (P2-B/P9).

    Per-mode groups by the per-attempt rating_source (falls back to the
    queue row source for ratings recorded before the column existed).
    Success proxy: effective_rating >= 3 (matches FSRS correct counting).
    """
    user_id = _require_review_user(user_id, session_token, authorization)
    conn = get_conn()
    try:
        prog = conn.execute("""
            SELECT COUNT(*) as n, COALESCE(SUM(attempts),0) as attempts,
                   COALESCE(SUM(correct),0) as correct
            FROM memorize_progress WHERE user_id=?
        """, (user_id,)).fetchone()
        recent = conn.execute("""
            SELECT COUNT(*) as n,
                   SUM(CASE WHEN effective_rating >= 3 THEN 1 ELSE 0 END) as ok
            FROM memorize_reviews WHERE user_id=?
              AND reviewed_at >= datetime('now','-30 days')
        """, (user_id,)).fetchone()
        due = conn.execute("""
            SELECT COUNT(*) as n FROM memorize_queue q
            LEFT JOIN memorize_progress p
              ON p.user_id=q.user_id AND p.verse_id=q.verse_id
            WHERE q.user_id=? AND (p.next_review IS NULL
              OR p.next_review <= date('now','localtime'))
        """, (user_id,)).fetchone()
        per_mode = conn.execute("""
            SELECT COALESCE(r.rating_source, q.source, 'manual') as mode,
                   COUNT(*) as ratings,
                   SUM(CASE WHEN r.effective_rating >= 3 THEN 1 ELSE 0 END) as ok,
                   ROUND(AVG(r.effective_rating), 2) as avg_eff
            FROM memorize_reviews r
            LEFT JOIN memorize_queue q
              ON q.user_id=r.user_id AND q.verse_id=r.verse_id
            WHERE r.user_id=? GROUP BY mode ORDER BY ratings DESC
        """, (user_id,)).fetchall()
    finally:
        conn.close()
    attempts = prog["attempts"] or 0
    return {"ok": True, "data": {
        "retention": {
            "attempts": attempts, "correct": prog["correct"] or 0,
            "rate": round((prog["correct"] or 0) / max(attempts, 1), 3),
            "last_30d": {
                "ratings": recent["n"] or 0, "ok": recent["ok"] or 0,
                "rate": round((recent["ok"] or 0) / max(recent["n"] or 0, 1), 3),
            },
        },
        "due_workload": {"due": due["n"] or 0},
        "per_mode": [{
            "mode": m["mode"], "ratings": m["ratings"],
            "success": m["ok"] or 0,
            "success_rate": round((m["ok"] or 0) / max(m["ratings"], 1), 3),
            "avg_effective_rating": m["avg_eff"],
        } for m in per_mode],
    }}
