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
import json, sqlite3, time, datetime, math, random
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
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
            last_review TEXT,
            next_review TEXT,
            PRIMARY KEY (user_id, verse_id)
        )
    """)
    return conn


# ── FSRS-5 (copied from hebrew.py for independence) ──
FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
          1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
          1.8729, 0.5425, 0.0912, 0.0658, 0.1542]

def _fsrs_initial_stability(rating):
    return FSRS_W[max(0, min(3, rating - 1))]

def _fsrs_next_interval(stability, request_retention=0.9):
    if stability <= 0: return 0
    return max(1, round(stability * (math.log(request_retention) / math.log(0.9)) ** (1.0 / FSRS_W[10])))

def _fsrs_stability_after_success(stability, difficulty, rating):
    difficulty_weight = math.pow(FSRS_W[7], difficulty - 1)
    retrieval_strength = math.pow(stability, -FSRS_W[9])
    rating_mult = FSRS_W[8]
    if rating == 2: rating_mult = FSRS_W[8] * FSRS_W[15]
    elif rating == 4: rating_mult = FSRS_W[8] * FSRS_W[16]
    return stability * (1 + rating_mult * retrieval_strength * difficulty_weight)

def _fsrs_stability_after_failure(stability, difficulty, _rating):
    return FSRS_W[11] * math.pow(difficulty, FSRS_W[12]) * math.pow(stability, -FSRS_W[13]) * (stability + 1)

def _fsrs_next_difficulty(difficulty, rating):
    delta = -FSRS_W[6] if rating >= 3 else FSRS_W[6]
    mean_reversion = FSRS_W[7] * (FSRS_W[4] - difficulty)
    return max(1.0, min(10.0, difficulty + delta + mean_reversion))

def _fsrs_schedule(stability, difficulty, rating):
    if rating <= 2:
        new_s = _fsrs_stability_after_failure(stability, difficulty, rating)
        new_d = _fsrs_next_difficulty(difficulty, rating)
    else:
        new_s = _fsrs_stability_after_success(stability, difficulty, rating)
        new_d = _fsrs_next_difficulty(difficulty, rating)
    return new_s, new_d, _fsrs_next_interval(new_s)


@router.get("/api/v1/memorize/queue")
def list_queue(user_id: str = "default"):
    """List all verses in the memorize queue with progress."""
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
        vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
        verses.append({
            "id": r["id"],
            "verse_id": r["verse_id"],
            "text": vt[0][:300] if vt and vt[0] else "",
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
def add_to_queue(body: dict):
    """Add a verse to the memorize queue."""
    conn = get_conn()
    verse_id = body.get("verse_id", "")
    user_id = body.get("user_id", "default")
    
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
        # Initialize progress
        conn.execute("""
            INSERT OR IGNORE INTO memorize_progress (user_id, verse_id, mastery, attempts, correct)
            VALUES (?, ?, 0, 0, 0)
        """, (user_id, verse_id))
        conn.commit()
        added = True
    except:
        added = False
    
    conn.close()
    return {"ok": True, "data": {"verse_id": verse_id, "added": added}}


@router.delete("/api/v1/memorize/queue/{item_id}")
def remove_from_queue(item_id: int, user_id: str = "default"):
    """Remove a verse from the memorize queue."""
    conn = get_conn()
    conn.execute("DELETE FROM memorize_queue WHERE id=? AND user_id=?", (item_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "data": {"removed": True}}


@router.post("/api/v1/memorize/queue/batch")
def add_chapter_to_queue(body: dict):
    """Add all verses in a chapter to the memorize queue."""
    conn = get_conn()
    book = body.get("book", "")
    chapter = body.get("chapter", 0)
    user_id = body.get("user_id", "default")
    
    if not book or not chapter:
        conn.close()
        raise HTTPException(400, "book and chapter required")
    
    verses = conn.execute(
        "SELECT id FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
        (book, chapter)
    ).fetchall()
    
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
        except:
            pass
    
    conn.commit()
    conn.close()
    return {"ok": True, "data": {"chapter": f"{book}.{chapter}", "verses_added": added_count}}


@router.get("/api/v1/memorize/review")
def get_due_reviews(user_id: str = "default", limit: int = 10):
    """Get due reviews from the memorize queue, ordered by urgency."""
    conn = get_conn()
    now = datetime.datetime.now()
    
    rows = conn.execute("""
        SELECT q.id, q.verse_id,
               COALESCE(p.mastery, 0) as mastery,
               COALESCE(p.attempts, 0) as attempts,
               COALESCE(p.correct, 0) as correct,
               COALESCE(p.stability, 1.0) as stability,
               COALESCE(p.difficulty, 5.0) as difficulty,
               p.last_review
        FROM memorize_queue q
        LEFT JOIN memorize_progress p ON p.user_id=q.user_id AND p.verse_id=q.verse_id
        WHERE q.user_id=?
        ORDER BY p.last_review ASC
        LIMIT ?
    """, (user_id, limit)).fetchall()
    
    reviews = []
    for r in rows:
        # Compute retrievability
        if r["last_review"]:
            try:
                last = datetime.datetime.strptime(r["last_review"], "%Y-%m-%d %H:%M:%S")
                days = (now - last).total_seconds() / 86400.0
                ret = math.exp(-days / r["stability"]) if r["stability"] > 0 else 1.0
            except:
                ret = 0.5
        else:
            ret = 0.0  # Never reviewed — most urgent
        
        vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (r["verse_id"],)).fetchone()
        text = vt[0] if vt else ""
        
        reviews.append({
            "queue_id": r["id"],
            "verse_id": r["verse_id"],
            "text": text[:300] if text else "",
            "mastery": r["mastery"],
            "attempts": r["attempts"],
            "stability": r["stability"],
            "difficulty": r["difficulty"],
            "retrievability": round(ret, 3),
        })
    
    # Sort by retrievability (most forgotten first)
    reviews.sort(key=lambda x: x["retrievability"])
    
    conn.close()
    return {"ok": True, "data": {"reviews": reviews, "due": len(reviews)}}


@router.post("/api/v1/memorize/review/{queue_id}")
def submit_review(queue_id: int, body: dict):
    """Submit a rating for a review (1=Again, 2=Hard, 3=Good, 4=Easy)."""
    user_id = body.get("user_id", "default")
    rating = max(1, min(4, body.get("rating", 3)))
    
    conn = get_conn()
    item = conn.execute(
        "SELECT verse_id FROM memorize_queue WHERE id=? AND user_id=?",
        (queue_id, user_id)
    ).fetchone()
    
    if not item:
        conn.close()
        raise HTTPException(404, "Queue item not found")
    
    verse_id = item["verse_id"]
    
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
        stability = _fsrs_initial_stability(rating)
        difficulty = 5.0
    
    # FSRS update
    new_s, new_d, interval = _fsrs_schedule(stability, difficulty, rating)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    next_review = (datetime.datetime.now() + datetime.timedelta(days=interval)).strftime("%Y-%m-%d")
    
    a += 1
    c += 1 if rating >= 3 else 0
    mastery = min(1.0, c / max(a, 1))
    
    conn.execute("""
        INSERT OR REPLACE INTO memorize_progress 
            (user_id, verse_id, mastery, attempts, correct, stability, difficulty, last_review, next_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, verse_id, round(mastery, 3), a, c, round(new_s, 2), round(new_d, 2), now_str, next_review))
    conn.commit()
    conn.close()
    
    return {"ok": True, "data": {
        "verse_id": verse_id, "mastery": round(mastery, 3),
        "stability": round(new_s, 2), "difficulty": round(new_d, 2),
        "interval": interval, "next_review": next_review,
    }}
