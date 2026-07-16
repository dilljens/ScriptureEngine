"""Learning modules — structured courses with lessons, practice, and mastery tracking.

Follows The Math Academy Way:
- Knowledge Graph: modules have prerequisites and encompassings
- Mastery Learning: must pass each module before advancing
- Direct Instruction: lesson content with explanations and worked examples
- Retrieval Practice: questions test understanding
- Spaced Repetition: FSRS-5 schedules reviews
- Layering: advanced modules reinforce prerequisites

Endpoints:
  GET  /api/v1/learn/modules         — list all modules with progress
  GET  /api/v1/learn/modules/{id}    — full module with lessons + practice
  POST /api/v1/learn/modules/{id}/practice — submit practice answer
  GET  /api/v1/learn/review          — due reviews
  POST /api/v1/learn/review/{id}    — submit review rating
"""
import contextlib
import datetime
import json
import math
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Learning modules
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_modules (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT '',
            icon TEXT DEFAULT '📖',
            difficulty INTEGER DEFAULT 1,
            prerequisite_ids TEXT DEFAULT '[]',
            lesson_content TEXT DEFAULT '',
            worked_examples TEXT DEFAULT '[]',
            estimated_minutes INTEGER DEFAULT 10,
            sort_order INTEGER DEFAULT 0
        )
    """)

    # Module-to-question mapping
    conn.execute("""
        CREATE TABLE IF NOT EXISTS module_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id TEXT NOT NULL REFERENCES learning_modules(id),
            question_id INTEGER NOT NULL REFERENCES assessment_items(id),
            is_required INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        )
    """)

    # Per-user progress per module
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learning_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            module_id TEXT NOT NULL REFERENCES learning_modules(id),
            mastery REAL DEFAULT 0.0,
            attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            stability REAL DEFAULT 1.0,
            difficulty REAL DEFAULT 5.0,
            last_review TEXT,
            next_review TEXT,
            PRIMARY KEY (user_id, module_id)
        )
    """)

    # Learn gamification: XP, streak tracking
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learn_gamification (
            user_id TEXT NOT NULL DEFAULT 'default' PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_review_date TEXT,
            best_streak INTEGER DEFAULT 0,
            modules_completed INTEGER DEFAULT 0
        )
    """)

    return conn


# ── FSRS-5 (same as hebrew.py) ──
FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
          1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
          1.8729, 0.5425, 0.0912, 0.0658, 0.1542]

def _fsrs_next(d, r):
    if r <= 2: return max(1.0, d * 0.5), 5.0, 1
    new_s = d * (1 + 0.5 * math.pow(d, -0.5))
    new_d = max(1.0, min(10.0, d + (-0.3 if r >= 3 else 0.3)))
    interval = max(1, round(new_s))
    return new_s, new_d, interval


def seed_modules():
    """Seed learning modules from existing hub notes and assessment items."""
    conn = get_conn()
    existing = conn.execute("SELECT COUNT(*) FROM learning_modules").fetchone()[0]
    if existing > 0:
        conn.close()
        return

    # Hub notes → learning modules
    conn.execute("SELECT id, title, description, icon FROM hub_notes").fetchall()
    hub_order = [
        "covenant", "temple", "exodus", "atonement", "lamb_of_god",
        "angel_of_the_lord", "wisdom", "son_of_man",
        "zion", "priesthood", "faith_unto_salvation",
        "restoration", "garden_to_city", "dispensations",
    ]

    for i, hid in enumerate(hub_order):
        hub = conn.execute(
            "SELECT id, title, description, icon FROM hub_notes WHERE id=?", (hid,)
        ).fetchone()
        if not hub:
            continue

        # Build lesson content from hub note steps
        steps = conn.execute(
            "SELECT verse_id, title, explanation, connection_type FROM hub_note_steps WHERE hub_id=? ORDER BY step_number",
            (hid,)
        ).fetchall()

        lesson_parts = [f"# {hub['title']}\n\n{hub['description']}\n"]
        for s in steps:
            vt = conn.execute("SELECT text_english FROM verses WHERE id=?", (s["verse_id"],)).fetchone()
            text = vt[0][:300] if vt and vt[0] else ""
            lesson_parts.append(f"\n## {s['title']} ({s['verse_id']})\n\n{text}\n\n{s['explanation']}")

        # Worked examples from TG topic
        tg_links = conn.execute("""
            SELECT t.name, t.slug FROM hub_topic_links h
            JOIN topical_guide t ON t.slug = h.topic_id
            WHERE h.hub_id = ? LIMIT 3
        """, (hid,)).fetchall()

        examples = []
        for tg in tg_links:
            verses = conn.execute("""
                SELECT v.id, v.text_english FROM tg_verse_references tg
                JOIN verses v ON v.id = tg.verse_id
                WHERE tg.topic_id = ? AND v.text_english IS NOT NULL
                LIMIT 2
            """, (tg["slug"],)).fetchall()
            for v in verses:
                examples.append({
                    "title": f"Example: {tg['name']}",
                    "verse": v["id"],
                    "text": v["text_english"][:200] if v["text_english"] else "",
                })

        # Find practice questions for this module (by TG topic links)
        q_ids = conn.execute("""
            SELECT a.id FROM assessment_items a
            WHERE a.tier = 'analysis'
            ORDER BY RANDOM() LIMIT 5
        """).fetchall()

        conn.execute("""
            INSERT INTO learning_modules (id, title, description, icon, difficulty, lesson_content, worked_examples, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hid, hub["title"], hub["description"], hub["icon"] or "📖",
            min(i + 1, 5),
            "\n".join(lesson_parts),
            json.dumps(examples[:4]),
            i + 1,
        ))

        for q in q_ids:
            conn.execute("INSERT OR IGNORE INTO module_questions (module_id, question_id) VALUES (?, ?)", (hid, q[0]))

        # Also link a couple open-ended questions
        open_ids = conn.execute("""
            SELECT id FROM assessment_items WHERE question_type_open = 1
            ORDER BY RANDOM() LIMIT 2
        """).fetchall()
        for q in open_ids:
            conn.execute("INSERT OR IGNORE INTO module_questions (module_id, question_id) VALUES (?, ?)", (hid, q[0]))

    # Add TG-based modules (doctrinal topics)
    tg_topics = conn.execute("""
        SELECT slug, name, description, verse_count FROM topical_guide
        WHERE verse_count >= 20 AND slug NOT IN (
            'jesus-christ-prophecies-about', 'god-spirit-of',
            'jesus-christ-authority-of', 'walking-with-god',
            'god-omniscience-of', 'remission-of-sins'
        )
        ORDER BY verse_count DESC LIMIT 12
    """).fetchall()

    base_order = len(hub_order) + 1
    for i, t in enumerate(tg_topics):
        slug, name, desc, vc = t
        desc_text = desc or f"Study the theme of {name} across scripture — {vc} verses reference this topic."

        examples = conn.execute("""
            SELECT v.id, v.text_english FROM tg_verse_references tg
            JOIN verses v ON v.id = tg.verse_id
            WHERE tg.topic_id = ? AND v.text_english IS NOT NULL
            LIMIT 3
        """, (slug,)).fetchall()

        w_examples = [{"title": f"{name} — {v[0]}", "verse": v[0], "text": v[1][:200]} for v in examples]

        q_ids = conn.execute("""
            SELECT id FROM assessment_items WHERE tier = 'consistency'
            ORDER BY RANDOM() LIMIT 4
        """).fetchall()

        conn.execute("""
            INSERT INTO learning_modules (id, title, description, icon, difficulty, lesson_content, worked_examples, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            f"tg_{slug}", name, desc_text, "📚",
            min(i + 2, 5),
            f"# {name}\n\nThis topic appears in {vc} verses across scripture.\n\n{desc_text}",
            json.dumps(w_examples),
            base_order + i,
        ))

        for q in q_ids:
            conn.execute("INSERT OR IGNORE INTO module_questions (module_id, question_id) VALUES (?, ?)",
                        (f"tg_{slug}", q[0]))

        open_ids = conn.execute("""
            SELECT id FROM assessment_items WHERE question_type_open = 1
            ORDER BY RANDOM() LIMIT 2
        """).fetchall()
        for q in open_ids:
            conn.execute("INSERT OR IGNORE INTO module_questions (module_id, question_id) VALUES (?, ?)",
                        (f"tg_{slug}", q[0]))

    conn.commit()
    conn.close()


# ── API Endpoints ──

@router.get("/api/v1/learn/modules")
def list_modules(user_id: str = "default"):
    """List all learning modules with user progress and due review count."""
    seed_modules()
    conn = get_conn()
    now = datetime.datetime.now()

    modules = conn.execute("""
        SELECT m.*,
               COALESCE(p.mastery, 0) as mastery,
               COALESCE(p.attempts, 0) as attempts,
               COALESCE(p.correct, 0) as correct,
               COALESCE(p.stability, 1.0) as stability,
               p.last_review,
               p.next_review,
               (SELECT COUNT(*) FROM module_questions WHERE module_id=m.id) as question_count
        FROM learning_modules m
        LEFT JOIN learning_progress p ON p.module_id=m.id AND p.user_id=?
        ORDER BY m.sort_order
    """, (user_id,)).fetchall()

    due_count = 0
    results = []
    # Pre-load all prerequisite IDs for quick lookup
    prereq_map = {}
    for m in modules:
        try:
            prereq_map[m["id"]] = json.loads(m["prerequisite_ids"]) if m["prerequisite_ids"] else []
        except (json.JSONDecodeError, TypeError):
            prereq_map[m["id"]] = []

    # Build mastery lookup for prerequisite checking
    mastery_map = {m["id"]: m["mastery"] for m in modules}

    for m in modules:
        mastered = m["mastery"] >= 0.8
        in_progress = m["mastery"] > 0 and m["mastery"] < 0.8

        # Check prerequisites
        prereqs = prereq_map.get(m["id"], [])
        prereq_satisfied = True
        prereq_details = []
        for pid in prereqs:
            p_mastery = mastery_map.get(pid, 0)
            satisfied = p_mastery >= 0.8
            if not satisfied:
                prereq_satisfied = False
            prereq_details.append({
                "id": pid,
                "satisfied": satisfied,
                "mastery": p_mastery,
            })

        # Compute retrievability for FSRS scheduling
        is_due = False
        if m["last_review"] and not mastered:
            try:
                last = datetime.datetime.strptime(m["last_review"], "%Y-%m-%d %H:%M:%S")
                days = (now - last).total_seconds() / 86400.0
                ret = math.exp(-days / max(m["stability"], 0.5))
                is_due = ret < 0.8
            except Exception:
                is_due = False

        if is_due:
            due_count += 1

        # Determine status with prerequisite gating
        if mastered:
            status = "mastered"
        elif not prereq_satisfied:
            status = "locked"
        elif in_progress:
            status = "learning"
        else:
            status = "available"

        results.append({
            "id": m["id"],
            "title": m["title"],
            "description": m["description"],
            "icon": m["icon"] or "📖",
            "difficulty": m["difficulty"],
            "mastery": m["mastery"],
            "attempts": m["attempts"],
            "question_count": m["question_count"],
            "status": status,
            "is_due": is_due,
            "prerequisites": prereq_details,
        })

    conn.close()

    return {"ok": True, "data": {
        "modules": results,
        "total": len(results),
        "due_count": due_count,
    }}


@router.get("/api/v1/learn/modules/{module_id}")
def get_module(module_id: str, user_id: str = "default"):
    """Get a full learning module with lesson content, worked examples, and practice questions."""
    seed_modules()
    conn = get_conn()

    mod = conn.execute("SELECT * FROM learning_modules WHERE id=?", (module_id,)).fetchone()
    if not mod:
        conn.close()
        raise HTTPException(404, f"Module not found: {module_id}")

    # Get practice questions — adaptive: weakest first, mix of MC and open-ended
    questions = conn.execute("""
        SELECT a.id, a.question_type, a.question_text, a.options_json, a.correct_answer,
               a.bloom_level, a.tier, a.explanation, a.question_type_open,
               COALESCE(qp.correct, 0) as user_correct,
               COALESCE(qp.attempts, 0) as user_attempts
        FROM module_questions mq
        JOIN assessment_items a ON a.id = mq.question_id
        LEFT JOIN quiz_progress qp ON qp.question_id=a.id AND qp.user_id=?
        WHERE mq.module_id=?
        ORDER BY
            CASE WHEN qp.attempts IS NULL THEN 0 ELSE 1 END,
            CAST(qp.correct AS REAL) / NULLIF(qp.attempts, 1) ASC NULLS FIRST,
            mq.sort_order
    """, (user_id, module_id)).fetchall()

    # Also fetch related wiki articles to enrich the lesson
    wiki_content = ""
    try:
        wiki_rows = conn.execute("""
            SELECT title, summary FROM wiki_articles
            WHERE title LIKE ? OR summary LIKE ?
            LIMIT 3
        """, (f'%{mod["title"][:20]}%', f'%{mod["title"][:20]}%')).fetchall()
        if wiki_rows:
            wiki_parts = ["\n\n## Related Wiki Articles\n"]
            for w in wiki_rows:
                wiki_parts.append(f"\n**{w['title']}**: {w['summary'][:300] if w['summary'] else ''}")
            wiki_content = "\n".join(wiki_parts)
    except Exception:
        pass

    q_list = []
    for q in questions:
        opts = []
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            opts = json.loads(q["options_json"]) if q["options_json"] else []
        q_list.append({
            "id": q["id"],
            "type": q["question_type"],
            "question": q["question_text"],
            "options": opts,
            "correct_answer": q["correct_answer"],
            "bloom_level": q["bloom_level"],
            "tier": q["tier"],
            "explanation": q["explanation"] or "",
            "is_open": bool(q["question_type_open"]),
            "user_correct": q["user_correct"],
            "user_attempts": q["user_attempts"],
        })

    worked_examples = []
    with contextlib.suppress(json.JSONDecodeError, ValueError):
        worked_examples = json.loads(mod["worked_examples"]) if mod["worked_examples"] else []

    # Get user progress
    prog = conn.execute(
        "SELECT mastery, attempts, correct, stability, difficulty, last_review, next_review FROM learning_progress WHERE user_id=? AND module_id=?",
        (user_id, module_id)
    ).fetchone()

    conn.close()

    return {"ok": True, "data": {
        "id": mod["id"],
        "title": mod["title"],
        "description": mod["description"],
        "icon": mod["icon"],
        "difficulty": mod["difficulty"],
        "lesson_content": mod["lesson_content"] + wiki_content if wiki_content else mod["lesson_content"],
        "worked_examples": worked_examples,
        "questions": q_list,
        "related_wiki": wiki_content[:500] if wiki_content else "",
        "progress": {
            "mastery": prog["mastery"] if prog else 0,
            "attempts": prog["attempts"] if prog else 0,
            "correct": prog["correct"] if prog else 0,
            "stability": prog["stability"] if prog else 1.0,
            "difficulty": prog["difficulty"] if prog else 5.0,
        } if prog else {"mastery": 0, "attempts": 0, "correct": 0},
    }}


@router.post("/api/v1/learn/modules/{module_id}/practice")
def submit_practice(module_id: str, body: dict):
    """Submit a practice answer for a module question.

    Uses FSRS-5 for spaced repetition scheduling.
    Rating mapping: Again(1), Hard(2), Good(3), Easy(4).
    """
    user_id = body.get("user_id", "default")
    question_id = body.get("question_id", 0)
    correct = body.get("correct", False)
    rating = body.get("rating", 3 if correct else 1)

    conn = get_conn()

    # Record in quiz_progress
    existing = conn.execute(
        "SELECT correct, attempts FROM quiz_progress WHERE user_id=? AND question_id=?",
        (user_id, question_id)
    ).fetchone()

    if existing:
        conn.execute("""
            UPDATE quiz_progress SET correct=correct+?, attempts=attempts+1, last_seen=datetime('now')
            WHERE user_id=? AND question_id=?
        """, (1 if correct else 0, user_id, question_id))
    else:
        conn.execute("""
            INSERT INTO quiz_progress (user_id, question_id, correct, attempts, last_seen)
            VALUES (?, ?, ?, 1, datetime('now'))
        """, (user_id, question_id, 1 if correct else 0))

    # ── FSRS-5 update ──
    now = datetime.datetime.now()

    prog = conn.execute(
        "SELECT stability, difficulty, last_review, attempts, correct FROM learning_progress WHERE user_id=? AND module_id=?",
        (user_id, module_id)
    ).fetchone()

    if prog and prog["last_review"]:
        # Existing progression — update with FSRS
        stability = prog["stability"]
        difficulty = prog["difficulty"]
        prev_attempts = prog["attempts"]
        prev_correct = prog["correct"]

        if correct:
            new_s = stability * (1 + 0.5 * math.pow(max(difficulty, 1.0), -0.5))
            new_d = max(1.0, min(10.0, difficulty + (-0.3 if rating >= 3 else 0.3)))
        else:
            new_s = max(1.0, stability * 0.5)
            new_d = max(1.0, min(10.0, difficulty + 0.3))

        last = datetime.datetime.strptime(prog["last_review"], "%Y-%m-%d %H:%M:%S")
        days_elapsed = (now - last).total_seconds() / 86400.0
        retrievability = math.exp(-days_elapsed / max(stability, 0.5))

        mastery = min(1.0, max(0.05,
            0.7 * retrievability +
            0.3 * (1.0 if correct else 0.0) +
            0.1 * (rating - 1) / 3.0
        ))
    else:
        # First practice — init FSRS values
        new_s = FSRS_W[0] if rating == 1 else FSRS_W[rating - 1] if 1 <= rating <= 4 else 1.0
        new_d = 5.0
        prev_attempts = 0
        prev_correct = 0
        mastery = 0.8 if correct else 0.3

    interval = max(1, round(new_s))
    next_review = now + datetime.timedelta(days=interval)

    conn.execute("""
        INSERT OR REPLACE INTO learning_progress
            (user_id, module_id, mastery, attempts, correct, stability, difficulty, last_review, next_review)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, module_id,
        round(mastery, 3),
        prev_attempts + 1,
        prev_correct + (1 if correct else 0),
        round(new_s, 2),
        round(new_d, 2),
        now.strftime("%Y-%m-%d %H:%M:%S"),
        next_review.strftime("%Y-%m-%d %H:%M:%S"),
    ))

    # ── Gamification: XP + streak ──
    xp_gained = 10 + (5 if rating >= 3 else 0) + (5 if correct else 0)
    today = now.strftime("%Y-%m-%d")

    # Check if this is the first time reaching mastery >= 0.8
    prior_mastery = conn.execute(
        "SELECT COALESCE(mastery, 0) FROM learning_progress WHERE user_id=? AND module_id=?",
        (user_id, module_id)
    ).fetchone()
    was_not_mastered = prior_mastery is None or prior_mastery[0] < 0.8
    just_completed = mastery >= 0.8 and was_not_mastered

    gam = conn.execute(
        "SELECT xp, streak_count, last_review_date, best_streak, modules_completed FROM learn_gamification WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if gam:
        new_xp = gam["xp"] + xp_gained
        new_streak = gam["streak_count"]
        if gam["last_review_date"]:
            try:
                last_date = datetime.datetime.strptime(gam["last_review_date"], "%Y-%m-%d")
                delta = (now - last_date).days
                if delta == 1:
                    new_streak += 1
                elif delta > 1:
                    new_streak = 1
                # delta == 0: same day, streak unchanged
            except Exception:
                new_streak = 1
        else:
            new_streak = 1 if not gam["last_review_date"] else new_streak
        best = max(gam["best_streak"], new_streak)
        new_completed = gam["modules_completed"] + (1 if just_completed else 0)
    else:
        new_xp = xp_gained
        new_streak = 1
        best = 1
        new_completed = 1 if mastery >= 0.8 else 0

    conn.execute("""
        INSERT OR REPLACE INTO learn_gamification
            (user_id, xp, streak_count, last_review_date, best_streak, modules_completed)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, new_xp, new_streak, today, best, new_completed))

    conn.commit()
    conn.close()

    return {"ok": True, "data": {
        "mastery": round(mastery, 3),
        "stability": round(new_s, 2),
        "difficulty": round(new_d, 2),
        "interval_days": interval,
        "next_review": next_review.strftime("%Y-%m-%d"),
        "xp_gained": xp_gained,
        "total_xp": new_xp,
        "streak": new_streak,
    }}


@router.get("/api/v1/learn/review")
def get_learn_reviews(user_id: str = "default", limit: int = 10):
    """Get due module reviews with actual practice questions for interleaved review."""
    conn = get_conn()
    now = datetime.datetime.now()

    rows = conn.execute("""
        SELECT p.module_id, m.title, p.mastery, p.stability, p.difficulty, p.last_review,
               (SELECT COUNT(*) FROM module_questions WHERE module_id=p.module_id) as qcount
        FROM learning_progress p
        JOIN learning_modules m ON m.id = p.module_id
        WHERE p.user_id = ? AND p.mastery > 0 AND p.mastery < 0.95
        ORDER BY p.last_review ASC, p.stability ASC
        LIMIT ?
    """, (user_id, limit)).fetchall()

    reviews = []
    seen_modules = set()

    for r in rows:
        if r["last_review"]:
            try:
                last = datetime.datetime.strptime(r["last_review"], "%Y-%m-%d %H:%M:%S")
                days = (now - last).total_seconds() / 86400.0
                ret = math.exp(-days / max(r["stability"], 0.5))
            except Exception:
                ret = 0.5
        else:
            ret = 0.0

        if ret < 0.8 and r["module_id"] not in seen_modules:
            seen_modules.add(r["module_id"])

            # Get 2-3 practice questions from this module
            questions = conn.execute("""
                SELECT a.id, a.question_type, a.question_text, a.options_json, a.correct_answer,
                       a.explanation, a.tier, a.bloom_level
                FROM module_questions mq
                JOIN assessment_items a ON a.id = mq.question_id
                WHERE mq.module_id = ?
                ORDER BY RANDOM()
                LIMIT 3
            """, (r["module_id"],)).fetchall()

            qs = []
            for q in questions:
                opts = []
                with contextlib.suppress(json.JSONDecodeError, ValueError):
                    opts = json.loads(q["options_json"]) if q["options_json"] else []
                qs.append({
                    "id": q["id"],
                    "type": q["question_type"],
                    "question": q["question_text"],
                    "options": opts,
                    "correct_answer": q["correct_answer"],
                    "explanation": q["explanation"] or "",
                    "tier": q["tier"],
                })

            reviews.append({
                "module_id": r["module_id"],
                "title": r["title"],
                "mastery": r["mastery"],
                "retrievability": round(ret, 3),
                "questions": qs,
            })

    conn.close()
    return {"ok": True, "data": {"reviews": reviews, "due": len(reviews)}}


@router.get("/api/v1/learn/gamification")
def get_learn_gamification(user_id: str = "default"):
    """Get gamification stats for LearnView."""
    from lib.db import get_db as _get_db
    conn = _get_db()
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # Ensure table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS learn_gamification (
            user_id TEXT NOT NULL DEFAULT 'default' PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_review_date TEXT,
            best_streak INTEGER DEFAULT 0,
            modules_completed INTEGER DEFAULT 0
        )
    """)

    row = conn.execute(
        "SELECT xp, streak_count, last_review_date, best_streak, modules_completed FROM learn_gamification WHERE user_id=?",
        (user_id,)
    ).fetchone()

    total_modules = conn.execute("SELECT COUNT(*) as c FROM learning_modules").fetchone()["c"]

    conn.close()

    if row:
        return {"ok": True, "data": {
            "xp": row["xp"],
            "streak": row["streak_count"],
            "best_streak": row["best_streak"],
            "last_review_date": row["last_review_date"],
            "modules_completed": row["modules_completed"],
            "total_modules": total_modules,
        }}
    return {"ok": True, "data": {
        "xp": 0, "streak": 0, "best_streak": 0,
        "last_review_date": None, "modules_completed": 0,
        "total_modules": total_modules,
    }}
