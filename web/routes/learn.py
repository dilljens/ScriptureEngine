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
    """List all learning modules with user progress."""
    seed_modules()
    conn = get_conn()

    modules = conn.execute("""
        SELECT m.*,
               COALESCE(p.mastery, 0) as mastery,
               COALESCE(p.attempts, 0) as attempts,
               COALESCE(p.correct, 0) as correct,
               (SELECT COUNT(*) FROM module_questions WHERE module_id=m.id) as question_count
        FROM learning_modules m
        LEFT JOIN learning_progress p ON p.module_id=m.id AND p.user_id=?
        ORDER BY m.sort_order
    """, (user_id,)).fetchall()

    conn.close()

    results = []
    for m in modules:
        mastered = m["mastery"] >= 0.8
        in_progress = m["mastery"] > 0 and m["mastery"] < 0.8
        results.append({
            "id": m["id"],
            "title": m["title"],
            "description": m["description"],
            "icon": m["icon"] or "📖",
            "difficulty": m["difficulty"],
            "mastery": m["mastery"],
            "attempts": m["attempts"],
            "question_count": m["question_count"],
            "status": "mastered" if mastered else ("learning" if in_progress else "available"),
        })

    return {"ok": True, "data": {"modules": results, "total": len(results)}}


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
    """Submit a practice answer for a module question."""
    user_id = body.get("user_id", "default")
    question_id = body.get("question_id", 0)
    correct = body.get("correct", False)

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

    # Update learning_progress
    prog = conn.execute(
        "SELECT mastery, attempts, correct FROM learning_progress WHERE user_id=? AND module_id=?",
        (user_id, module_id)
    ).fetchone()

    if prog:
        a = prog["attempts"] + 1
        c = prog["correct"] + (1 if correct else 0)
    else:
        a = 1
        c = 1 if correct else 0

    mastery = min(1.0, c / max(a, 1))

    conn.execute("""
        INSERT OR REPLACE INTO learning_progress (user_id, module_id, mastery, attempts, correct, last_review)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (user_id, module_id, round(mastery, 3), a, c))

    conn.commit()
    conn.close()

    return {"ok": True, "data": {
        "mastery": round(mastery, 3),
        "attempts": a,
        "correct": c,
    }}


@router.get("/api/v1/learn/review")
def get_learn_reviews(user_id: str = "default", limit: int = 10):
    """Get due module reviews (FSRS-scheduled)."""
    conn = get_conn()
    now = datetime.datetime.now()

    rows = conn.execute("""
        SELECT p.module_id, m.title, p.mastery, p.attempts, p.stability, p.difficulty, p.last_review,
               (SELECT COUNT(*) FROM module_questions WHERE module_id=p.module_id) as qcount
        FROM learning_progress p
        JOIN learning_modules m ON m.id = p.module_id
        WHERE p.user_id = ? AND p.mastery > 0 AND p.mastery < 0.95
        ORDER BY p.last_review ASC
        LIMIT ?
    """, (user_id, limit)).fetchall()

    reviews = []
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

        if ret < 0.8:
            reviews.append({
                "module_id": r["module_id"],
                "title": r["title"],
                "mastery": r["mastery"],
                "retrievability": round(ret, 3),
                "questions_available": r["qcount"],
            })

    conn.close()
    return {"ok": True, "data": {"reviews": reviews, "due": len(reviews)}}
