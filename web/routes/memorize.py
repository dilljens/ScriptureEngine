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
            fi_re_credit REAL DEFAULT 0.0,
            last_review TEXT,
            next_review TEXT,
            PRIMARY KEY (user_id, verse_id)
        )
    """)
    # Add fi_re_credit column if missing (for existing DBs)
    try:
        conn.execute("ALTER TABLE memorize_progress ADD COLUMN fi_re_credit REAL DEFAULT 0.0")
    except Exception:
        pass
    return conn


# ── FSRS-5 (copied from hebrew.py for independence) ──
FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
          1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
          1.8729, 0.5425, 0.0912, 0.0658, 0.1542]

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

def _fsrs_initial_stability(rating):
    return FSRS_W[max(0, min(3, rating - 1))]

def _fsrs_next_interval(stability, request_retention=0.9, learning_speed=1.0):
    """Compute next review interval, adjusted for student-topic learning speed.
    
    Per Math Academy Ch 29: speed governs how quickly the student moves
    through the spaced repetition process.
    - Fast learner (speed > 1.0): longer intervals
    - Slow learner (speed < 1.0): shorter intervals
    """
    if stability <= 0: return 0
    base = stability * (math.log(request_retention) / math.log(0.9)) ** (1.0 / FSRS_W[10])
    return max(1, round(base * learning_speed))

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
            except:
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
        # Initialize progress with connection-aware difficulty
        difficulty = get_connection_difficulty(conn, verse_id)
        conn.execute("""
            INSERT OR IGNORE INTO memorize_progress (user_id, verse_id, mastery, attempts, correct, difficulty)
            VALUES (?, ?, 0, 0, 0, ?)
        """, (user_id, verse_id, difficulty))
        conn.commit()
        added = True
    except:
        added = False
    
    conn.close()
    return {"ok": True, "data": {"verse_id": verse_id, "added": added, "initial_difficulty": difficulty if 'difficulty' in dir() else 5.0}}


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
def get_due_reviews(user_id: str = "default", limit: int = 10, compress: bool = False, palace_order: bool = False):
    """Get due reviews from the memorize queue, ordered by urgency.
    
    Features:
    - FIRe knock-out: cards with fi_re_credit >= 1.0 are skipped (extend interval)
    - Connection-aware difficulty: shown in response
    - Repetition compression (if compress=True): connected cards grouped together
    - Palace-guided ordering (if palace_order=True): ordered by memory palace loci
    """
    conn = get_conn()
    now = datetime.datetime.now()
    
    rows = conn.execute("""
        SELECT q.id, q.verse_id,
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
            "fi_re_credit": round(fire_credit, 3),
            "retrievability": round(ret, 3),
        })
    
    # Sort by retrievability (most forgotten first)
    reviews.sort(key=lambda x: x["retrievability"])
    
    # Palace-guided ordering: if enabled, order by memory palace loci
    if palace_order:
        try:
            MEM_PATH = Path(__file__).parent.parent.parent / "data" / "memorize.db"
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
    
    # FSRS update with student-topic learning speed
    learning_speed = compute_learning_speed(conn, user_id, verse_id)
    
    # Adjust difficulty by learning speed (Math Academy Ch 29):
    # Fast learners get lower effective difficulty, slow learners higher
    speed_adjusted_diff = difficulty / max(learning_speed, 0.3)
    
    new_s, new_d, base_interval = _fsrs_schedule(stability, speed_adjusted_diff, rating)
    
    # Apply learning speed to interval
    interval = max(1, round(base_interval * learning_speed))
    
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    next_review = (datetime.datetime.now() + datetime.timedelta(days=interval)).strftime("%Y-%m-%d")
    
    a += 1
    c += 1 if rating >= 3 else 0
    mastery = min(1.0, c / max(a, 1))
    
    conn.execute("""
        INSERT OR REPLACE INTO memorize_progress 
            (user_id, verse_id, mastery, attempts, correct, stability, difficulty, fi_re_credit, last_review, next_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?)
    """, (user_id, verse_id, round(mastery, 3), a, c, round(new_s, 2), round(new_d, 2), now_str, next_review))
    
    # FIRe credit propagation: successful reviews give credit to connected verses
    try:
        compute_fire_credit(conn, verse_id, rating)
    except Exception:
        pass  # FIRe is non-critical
    
    conn.commit()
    conn.close()
    
    return {"ok": True, "data": {
        "verse_id": verse_id, "mastery": round(mastery, 3),
        "stability": round(new_s, 2), "difficulty": round(new_d, 2),
        "interval": interval, "next_review": next_review,
        "fi_re_credit_propagated": True,
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


# ── Macro-Interleaving ──

@router.get("/api/v1/review/interleaved")
def get_interleaved_reviews(user_id: str = "default", limit: int = 15):
    """Get interleaved reviews from ALL areas: memorize + hebrew + learn.
    
    Implements Math Academy's macro-interleaving (Ch 19):
    - Pulls due cards from memorize queue, hebrew review queue, and learn review
    - Interleaves them: no more than 2 consecutive from same area
    - Returns a mixed session for maximum retention
    """
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
            except:
                retro = 0.5
        all_cards.append({
            "id": f"mem_{r['id']}", "verse_id": r["verse_id"],
            "text": (vt[0] or "")[:200] if vt else "",
            "source": "memorize", "retrievability": round(retro, 3),
        })
    
    # 2. Hebrew review cards (from memorize.db)
    try:
        MEM_PATH = Path(__file__).parent.parent.parent / "data" / "memorize.db"
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
        MEM_PATH = Path(__file__).parent.parent.parent / "data" / "memorize.db"
        mconn = sqlite3.connect(str(MEM_PATH))
        row = mconn.execute(
            "SELECT strength FROM hebrew_confusability WHERE (node_a=? AND node_b=?) OR (node_a=? AND node_b=?)",
            (verse_a, verse_b, verse_b, verse_a)
        ).fetchone()
        mconn.close()
        if row:
            return row[0]
    except Exception:
        pass
    
    return 0.0


@router.get("/api/v1/review/next")
def get_next_review(user_id: str = "default", last_verse: str = ""):
    """Get the next review card, respecting non-interference.
    
    Ensures the next card doesn't interfere with the last one reviewed.
    Avoids scheduling confusable pairs consecutively.
    """
    conn = get_conn()
    
    # Get next due card from memorize queue
    rows = conn.execute("""
        SELECT q.id, q.verse_id, COALESCE(p.fi_re_credit, 0.0) as fire,
               COALESCE(p.stability, 1.0) as stability, p.last_review
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
    }}}


# ── Targeted Remediation ──

@router.get("/api/v1/review/weakest")
def get_weakest_reviews(user_id: str = "default", limit: int = 5):
    """Get cards where the user is weakest for targeted remediation.
    
    Implements Math Academy's targeted remediation (Ch 21):
    - Identifies verses with lowest accuracy rates
    - Prioritizes verses with most failed attempts
    - Returns targeted mini-session for weak areas
    """
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
