"""Hebrew learning + grammar reference routes."""
import datetime
import json
import math
import random
import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter()

# ── FSRS-5 Implementation (Hebrew learning) ──
# Ported from go-srs/internal/fsrs which is verified against Rust fsrs-rs test vectors.
# 21 W-parameters, default retention 0.9, max interval 36500 days.

FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
          1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
          1.8729, 0.5425, 0.0912, 0.0658, 0.1542]


def fsrs_initial_stability(rating):
    """Initial stability (in days) based on rating 1-4."""
    if rating < 1 or rating > 4:
        rating = 3
    return FSRS_W[rating - 1]


def fsrs_next_interval(stability, request_retention=0.9):
    """Next review interval in days."""
    if stability <= 0:
        return 0
    return max(1, round(stability * (math.log(request_retention) / math.log(0.9)) ** (1.0 / FSRS_W[10])))


def fsrs_stability_after_success(stability, difficulty, rating):
    """Calculate new stability after a successful recall."""
    difficulty_weight = math.pow(FSRS_W[7], difficulty - 1)
    retrieval_strength = math.pow(stability, -FSRS_W[9])
    # Rating multiplier
    rating_mult = FSRS_W[8]
    if rating == 2:  # Hard
        rating_mult = FSRS_W[8] * FSRS_W[15]
    elif rating == 4:  # Easy
        rating_mult = FSRS_W[8] * FSRS_W[16]

    new_s = stability * (1 + rating_mult * retrieval_strength * difficulty_weight)
    return new_s


def fsrs_stability_after_failure(stability, difficulty, _rating):
    """Calculate new stability after a failed recall."""
    difficulty_pow = math.pow(difficulty, FSRS_W[12])
    stability_factor = math.pow(stability, -FSRS_W[13])
    new_s = FSRS_W[11] * difficulty_pow * stability_factor * (stability + 1)
    return new_s


def fsrs_next_difficulty(difficulty, rating):
    """Calculate next difficulty after a review."""
    delta = -FSRS_W[6] if rating >= 3 else FSRS_W[6]
    mean_reversion = FSRS_W[7] * (FSRS_W[4] - difficulty)
    new_d = difficulty + delta + mean_reversion
    # Clamp to [1, 10]
    return max(1.0, min(10.0, new_d))


def fsrs_retrievability(stability, days_since):
    """Probability of recall after elapsed days."""
    if stability <= 0:
        return 0
    return math.exp(-days_since / stability * math.log(1.0 / (1.0 - FSRS_W[20])) if FSRS_W[20] > 0
                    else math.pow(1 + days_since / (stability * FSRS_W[19]), 1 - FSRS_W[18]))


def fsrs_schedule(stability, difficulty, rating):
    """Full FSRS schedule: given current state + rating, return new state + interval."""
    if rating <= 2:  # Failed (Again or Hard)
        new_s = fsrs_stability_after_failure(stability, difficulty, rating)
        new_d = fsrs_next_difficulty(difficulty, rating)
    else:  # Passed (Good or Easy)
        new_s = fsrs_stability_after_success(stability, difficulty, rating)
        new_d = fsrs_next_difficulty(difficulty, rating)

    interval = fsrs_next_interval(new_s)
    return new_s, new_d, interval


# ── Student-Topic Learning Speeds (Math Academy Ch. 29) ──
# learning_speed = speedup_due_to_ability / slowdown_due_to_difficulty
# ability = user's weighted accuracy across all topics
# difficulty = 1 - average accuracy of all users on this topic

def _get_all_user_accuracy(user_id="default"):
    """Get all accuracy data for a specific user across all Hebrew nodes."""
    if not MEM_DB.exists(): return {}, 0, 0
    conn = sqlite3.connect(str(MEM_DB))
    rows = conn.execute(
        "SELECT node_id, attempts, correct FROM hebrew_progress WHERE user_id=?",
        (user_id,)).fetchall()
    conn.close()
    total_attempts = sum(r[1] for r in rows)
    total_correct = sum(r[2] for r in rows)
    user_acc = {r[0]: r[2] / max(r[1], 1) for r in rows if r[1] > 0}
    return user_acc, total_attempts, total_correct


def _get_topic_difficulty():
    """Compute difficulty for each topic: 1 - avg accuracy across all users."""
    if not MEM_DB.exists(): return {}
    conn = sqlite3.connect(str(MEM_DB))
    rows = conn.execute(
        "SELECT node_id, AVG(CAST(correct AS FLOAT) / CAST(MAX(attempts, 1) AS FLOAT)) as avg_acc "
        "FROM hebrew_progress WHERE attempts > 0 GROUP BY node_id"
    ).fetchall()
    conn.close()
    return {r[0]: 1.0 - r[1] for r in rows}


def compute_learning_speed(user_id="default"):
    """Compute ability/difficulty ratio for each topic.

    Returns: {node_id: learning_speed, ...}
    Also returns overall_ability and topic_difficulties for transparency.
    """
    user_acc, total_attempts, total_correct = _get_all_user_accuracy(user_id)
    topic_diff = _get_topic_difficulty()

    # User ability = overall accuracy (weighted toward recent via exponential decay is ideal,
    # but simple ratio works well for now — Math Academy uses weighted recent accuracy)
    overall_ability = total_correct / max(total_attempts, 1) if total_attempts > 0 else 0.5

    speeds = {}
    for node_id in topic_diff:
        diff = topic_diff[node_id]
        # Avoid division by zero: minimum difficulty of 0.1
        diff = max(0.1, diff)
        speed = overall_ability / diff
        speeds[node_id] = round(speed, 3)

    return speeds, round(overall_ability, 3), {k: round(v, 3) for k, v in topic_diff.items()}


# ── FIRe (Fractional Implicit Repetition) ──

def fire_process(graph, node_id, correct, weight=0.3):
    """Process FIRe: implicit repetition credit flows through the knowledge graph.

    When a node is practiced, connected prerequisite nodes get partial credit.
    This implements repetition compression (Math Academy Ch. 18, 29).
    """
    if not graph:
        return {}
    results = {}
    # Get prerequisites (nodes that this node depends on)
    prereqs = graph.get(node_id, [])
    for prereq_id in prereqs:
        # Credit = weight * correctness
        credit = weight * (1.0 if correct else 0.0)
        results[prereq_id] = credit
        # Recursive: propagate to prerequisites of prerequisites
        sub_results = fire_process(graph, prereq_id, correct, weight * 0.5)
        for k, v in sub_results.items():
            results[k] = results.get(k, 0) + v
    return results

BASE_DIR = Path(__file__).parent.parent.parent
MEM_DB = BASE_DIR / "data" / "memorize.db"
SCRIPTURE_DB = BASE_DIR / "data" / "processed" / "scripture.db"


def get_db():
    """Get scripture database connection."""
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()


# ── Hebrew Knowledge Graph (for FIRe) ──

def _build_hebrew_graph():
    if not MEM_DB.exists(): return {}
    conn = sqlite3.connect(str(MEM_DB))
    edges = conn.execute("SELECT source_id, target_id FROM hebrew_edges").fetchall()
    conn.close()
    graph = {}
    for src, tgt in edges:
        if tgt not in graph: graph[tgt] = []
        graph[tgt].append(src)
    return graph


HEBREW_GRAPH = _build_hebrew_graph()


# ── Targeted Remediation ──

REMEDIATION_DRILLS = {
    "can't_start": {
        "title": "Starting Cue Drill",
        "description": "Focus on the first word or phrase — use the reference as your trigger.",
        "exercises": [
            "Cover the verse and try to recall just the first word from the reference.",
            "Say the reference out loud, then immediately say the first word.",
            "Practice the transition: Reference → First word, repeatedly.",
        ]
    },
    "mid_verse_loss": {
        "title": "Transition Drill",
        "description": "Practice the middle transition — where your recall breaks down.",
        "exercises": [
            "Split the verse into parts. Practice just the transition between part 1 and part 2.",
            "Say part 1 aloud, pause, then say part 2. Repeat 3 times.",
            "Write out the verse and circle the transition point. Practice that spot specifically.",
        ]
    },
    "ending_loss": {
        "title": "Ending Focus Drill",
        "description": "Strengthen the ending — the most commonly forgotten part.",
        "exercises": [
            "Practice the last few words in isolation: start from the middle and go to the end.",
            "Say the whole verse but emphasize (shout) the last word.",
            "Write the verse without the ending, then fill in the ending from memory.",
        ]
    },
    "confusion": {
        "title": "Discrimination Drill",
        "description": "This item is often confused with similar concepts. Practice telling them apart.",
        "exercises": [
            "Compare this item with its similar counterpart side by side.",
            "Quiz yourself: 'Which one is [A] and which is [B]?'",
            "Create a mnemonic that highlights the difference between them.",
        ]
    },
}


def _get_remediation_for_pattern(node_id, pattern, conn=None):
    """Get targeted remediation content for a failure pattern."""
    drill = REMEDIATION_DRILLS.get(pattern, REMEDIATION_DRILLS["confusion"])

    # Get node info for personalized drill
    node_title = node_id
    node_desc = ""
    if conn:
        row = conn.execute(
            "SELECT title, description FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
        if row:
            node_title = row['title']
            node_desc = row['description'] or ""

    return {
        "pattern": pattern,
        "node_id": node_id,
        "node_title": node_title,
        "drill_title": drill["title"],
        "description": drill["description"],
        "exercises": drill["exercises"],
        "node_description": node_desc,
    }


@router.get("/api/v1/hebrew/remediate/{node_id}")
def get_hebrew_remediation(node_id: str, pattern: str = "confusion", user_id: str = "default"):
    """Get targeted remediation drill for a specific failure pattern.

    Patterns: can't_start, mid_verse_loss, ending_loss, confusion
    Returns exercises and explanations tailored to the failure point.
    """
    if pattern not in REMEDIATION_DRILLS:
        pattern = "confusion"

    if not MEM_DB.exists():
        return {"ok": True, "data": _get_remediation_for_pattern(node_id, pattern)}

    conn = sqlite3.connect(str(MEM_DB))
    remediation = _get_remediation_for_pattern(node_id, pattern, conn)
    conn.close()

    return {"ok": True, "data": remediation}


@router.get("/api/v1/hebrew/fsrs/review")
def get_hebrew_fsrs_review(node_id: str, rating: int = 3, user_id: str = "default",
                            hint_level: int = 0, failure_location: str = ""):
    """Process an FSRS-5 review with FIRe, learning speed, and failure tracking.

    Rating: 1=Again, 2=Hard, 3=Good, 4=Easy.
    hint_level: which hint level was used (0=no hint, 1=first letters, 2=image, etc.)
    failure_location: 'start', 'middle', 'end', 'confusion', or '' for no failure.
    Learning speed adjusts the interval: faster learners → longer intervals.
    If learning_speed < 0.5, FIRe credit is skipped (force explicit reviews).
    """
    if not MEM_DB.exists():
        raise HTTPException(404, "Hebrew DB not found")
    rating = max(1, min(4, rating))
    conn = sqlite3.connect(str(MEM_DB))
    row = conn.execute(
        "SELECT mastery, attempts, correct FROM hebrew_progress WHERE user_id=? AND node_id=?",
        (user_id, node_id)).fetchone()
    if row and row[1] > 0 and row[2] > 0:
        a, c, m = row[1], row[2], row[0]
        stability = max(1.0, a * m * 7.0)
        difficulty = max(1.0, min(10.0, 5.0 - m * 3.0))
    else:
        a, c, m = 0, 0, 0.0
        stability = fsrs_initial_stability(rating)
        difficulty = 5.0

    # Compute student-topic learning speed
    speeds, ability, diffs = compute_learning_speed(user_id)
    learning_speed = speeds.get(node_id, 1.0)
    learning_speed = max(0.2, min(5.0, learning_speed))

    new_s, new_d, interval = fsrs_schedule(stability, difficulty, rating)
    adjusted_interval = max(1, round(interval * learning_speed))

    a += 1
    c += 1 if rating >= 3 else 0
    m = min(1.0, c / max(a, 1))
    conn.execute(
        "INSERT OR REPLACE INTO hebrew_progress (user_id,node_id,mastery,attempts,correct,last_practiced) VALUES (?,?,?,?,?,datetime('now'))",
        (user_id, node_id, m, a, c))

    # Track failure pattern for targeted remediation
    failure_pattern = None
    if rating <= 2 and hint_level > 0:
        # Infer failure pattern from hint level and location
        if failure_location:
            failure_pattern = failure_location
        elif hint_level >= 4:
            failure_pattern = "can't_start"
        elif hint_level >= 2:
            failure_pattern = "mid_verse_loss"
        else:
            failure_pattern = "confusion"

        # Store failure pattern for remediation
        remediation_hint = _get_remediation_for_pattern(node_id, failure_pattern, conn)
    else:
        remediation_hint = None

    # FIRe: only if learning speed >= 0.5
    fire_results = {}
    if learning_speed >= 0.5:
        fire_results = fire_process(HEBREW_GRAPH, node_id, rating >= 3, weight=0.3)
        for prereq_id, credit in fire_results.items():
            if credit > 0:
                pr = conn.execute("SELECT mastery FROM hebrew_progress WHERE user_id=? AND node_id=?",
                                  (user_id, prereq_id)).fetchone()
                if pr:
                    conn.execute("UPDATE hebrew_progress SET mastery=?,last_practiced=datetime('now') WHERE user_id=? AND node_id=?",
                                 (min(1.0, pr[0] + credit * 0.05), user_id, prereq_id))

    # ── Gamification: XP + Streak + Badge check ──
    streak_count = _update_streak(user_id)
    # Base XP: 10 per review, bonus if streak > 0
    xp_base = 10
    streak_multiplier = min(3.0, 1.0 + streak_count * 0.05)  # up to 3x for 40 day streak
    xp_earned = round(xp_base * streak_multiplier)
    new_xp, new_badges = _award_xp(user_id, xp_earned, f"Review: {node_id}")

    # Insight XP: discover connections through the graph
    insight_amount = 0
    insight_new_connections = 0
    if rating >= 3:
        ins_result = _award_insight_xp(user_id, node_id, amount=3)
        ins_amount, ins_badges, ins_new = ins_result if len(ins_result) == 3 else (ins_result[0], ins_result[1], 0)
        insight_amount = ins_amount
        insight_new_connections = ins_new
        if ins_badges:
            new_badges.extend(ins_badges)

    conn.commit()
    conn.close()
    return {"ok": True, "data": {
        "node_id": node_id, "stability": round(new_s, 2), "difficulty": round(new_d, 2),
        "interval": adjusted_interval, "mastery": round(m, 3), "attempts": a, "correct": c,
        "learning_speed": round(learning_speed, 3),
        "user_ability": ability,
        "failure_pattern": failure_pattern,
        "remediation": remediation_hint,
        "xp_earned": xp_earned,
        "total_xp": new_xp,
        "streak": streak_count,
        "insight_xp": insight_amount,
        "new_connections": insight_new_connections,
        "new_badges": new_badges,
        "fire_credits": {k: round(v, 3) for k, v in sorted(fire_results.items(), key=lambda x: -x[1])[:10]},
    }}


@router.get("/api/v1/hebrew/learning-speeds")
def get_hebrew_learning_speeds(user_id: str = "default"):
    """Get student-topic learning speeds for all practiced nodes.

    Returns ability, difficulty per topic, and the ratio (learning speed).
    Higher speed = learner is faster on this topic → longer intervals.
    """
    speeds, ability, diffs = compute_learning_speed(user_id)
    # Sort by speed ascending (slowest first — needs most review)
    sorted_speeds = sorted(speeds.items(), key=lambda x: x[1])
    return {"ok": True, "data": {
        "user_ability": ability,
        "learning_speeds": {k: v for k, v in sorted_speeds},
        "topic_difficulties": diffs,
        "slowest": [{"node_id": k, "speed": v} for k, v in sorted_speeds[:10]],
        "fastest": [{"node_id": k, "speed": v} for k, v in sorted_speeds[-10:]],
    }}


# ── Vocabulary ──

@router.get("/api/v1/vocabulary")
def get_vocabulary(top: int = 100, cutoff: int = 47, by_root: bool = False):
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT
            l.lemma, l.hebrew_plain as hebrew_word, l.transliteration,
            l.part_of_speech, l.root_letters as root, l.definition,
            l.morphology, l.frequency as lex_freq,
            lg.english_gloss, lg.frequency as gloss_freq,
            COALESCE(lg.english_gloss, l.lemma, '') as gloss
        FROM lexicon l
        LEFT JOIN lemma_gloss lg ON l.lemma = lg.lemma
        WHERE l.lemma NOT IN ('b','c','d','H','G','l','m','k')
          AND l.frequency > ? AND l.hebrew_plain IS NOT NULL AND l.hebrew_plain != ''
        ORDER BY l.frequency DESC LIMIT ?
    """, (cutoff, top * 3)).fetchall()
    conn.close()
    words = []
    rank = 0
    for r in rows:
        freq = r['lex_freq'] or 0
        gloss = (r['gloss'] or '').strip()
        word = (r['hebrew_word'] or '').strip()
        if not word or not gloss or len(word) <= 1 or gloss.replace(' ', '').isdigit():
            continue
        rank += 1
        words.append({
            'rank': rank, 'hebrew': word,
            'transliteration': (r['transliteration'] or '').strip(),
            'gloss': gloss, 'root': (r['root'] or '').strip(),
            'pos': (r['part_of_speech'] or '').strip(),
            'frequency': freq, 'definition': (r['definition'] or '').strip()[:200],
        })
        if rank >= top:
            break
    if by_root:
        from collections import defaultdict
        groups = defaultdict(list)
        for w in words:
            rk = w.get('root') or 'UNKNOWN'
            groups[rk].append(w)
        result = [{'root': r, 'total_frequency': sum(w['frequency'] for w in g), 'words': g}
                  for r, g in sorted(groups.items(), key=lambda x: -sum(w['frequency'] for w in x[1]))]
        return {"ok": True, "data": {"total": len(words), "groups": result}}
    return {"ok": True, "data": {"total": len(words), "words": words, "cutoff": cutoff, "coverage": "~90% of OT text"}}


# ── Hebrew Lessons ──

@router.get("/api/v1/hebrew/lessons")
def list_hebrew_lessons(category: str = ""):
    if not MEM_DB.exists():
        return {"ok": True, "data": {"lessons": [], "total": 0}}
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    if category:
        rows = conn.execute(
            "SELECT n.id, n.title, n.category, n.level, n.description, COUNT(e.source_id) as prereq_count "
            "FROM hebrew_nodes n LEFT JOIN hebrew_edges e ON e.target_id=n.id "
            "WHERE n.category=? GROUP BY n.id ORDER BY n.level", (category,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT n.id, n.title, n.category, n.level, n.description, COUNT(e.source_id) as prereq_count "
            "FROM hebrew_nodes n LEFT JOIN hebrew_edges e ON e.target_id=n.id "
            "GROUP BY n.id ORDER BY n.level").fetchall()
    conn.close()
    lessons = [dict(r) for r in rows]
    return {"ok": True, "data": {"lessons": lessons, "total": len(lessons),
                                  "categories": ["letter", "vowel", "word", "grammar", "phrase", "reading", "root_concept"]}}


@router.get("/api/v1/hebrew/diagnostic")
def get_hebrew_diagnostic(user_id: str = "default", count_per_category: int = 2):
    """Generate a diagnostic pre-assessment covering all categories.

    Returns 2-3 sample questions per category to determine what
    the learner already knows. Results can skip mastered categories.
    """
    if not MEM_DB.exists():
        return {"ok": True, "data": {"questions": [], "categories": []}}

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    random.seed()

    # Get all categories
    cats = conn.execute("SELECT DISTINCT category FROM hebrew_nodes ORDER BY category").fetchall()
    categories = [c['category'] for c in cats if c['category'] not in ('root_concept',)]

    # Check if user already has progress
    existing_progress = conn.execute(
        "SELECT COUNT(*) FROM hebrew_progress WHERE user_id=?", (user_id,)).fetchone()[0]
    has_progress = existing_progress > 0

    questions = []
    cat_info = []

    for cat in categories:
        # Get nodes in this category
        nodes = conn.execute(
            "SELECT n.id, n.title FROM hebrew_nodes n WHERE n.category=? ORDER BY RANDOM() LIMIT ?",
            (cat, count_per_category)).fetchall()

        if not nodes:
            continue

        cat_questions = []
        for n in nodes:
            # Get a practice item for this node
            item = conn.execute(
                "SELECT * FROM hebrew_practice_items WHERE node_id=? AND question_type IN ('multiple_choice','true_false') LIMIT 1",
                (n['id'],)).fetchone()
            if not item:
                continue

            opts = json.loads(item['options_json']) if item['options_json'] else []
            cat_questions.append({
                "node_id": n['id'],
                "node_title": n['title'],
                "question": item['question_text'],
                "options": opts,
                "correct_answer": item['correct_answer'],
                "question_type": item['question_type'],
            })

        if cat_questions:
            questions.extend(cat_questions)
            cat_info.append({
                "category": cat,
                "count": len(cat_questions),
                "nodes": len(nodes),
                "node_ids": [n['id'] for n in nodes],
            })

    conn.close()

    return {"ok": True, "data": {
        "questions": questions,
        "total": len(questions),
        "categories": cat_info,
        "has_progress": has_progress,
        "message": "Answer these questions to determine your starting level. "
                   "Categories where you score 100% will be skipped."
    }}


@router.post("/api/v1/hebrew/diagnostic/apply")
def apply_diagnostic_results(body: dict):
    """Apply diagnostic results — mark mastered categories as complete.

    Body: {
        "user_id": "default",
        "results": { "category_name": { "correct": N, "total": N }, ... }
    }
    """
    if not MEM_DB.exists():
        raise HTTPException(404, "Hebrew DB not found")

    user_id = body.get("user_id", "default")
    results = body.get("results", {})

    conn = sqlite3.connect(str(MEM_DB))

    for cat, stats in results.items():
        correct = stats.get("correct", 0)
        total = stats.get("total", 0)
        if total == 0:
            continue
        pct = correct / total

        if pct >= 1.0:
            # 100% → skip all nodes in this category
            nodes = conn.execute("SELECT id FROM hebrew_nodes WHERE category=?", (cat,)).fetchall()
            for n in nodes:
                conn.execute(
                    "INSERT OR REPLACE INTO hebrew_progress (user_id, node_id, mastery, attempts, correct, last_practiced) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                    (user_id, n[0], 1.0, 1, 1))
        elif pct >= 0.6:
            # 60-80% → partial credit
            nodes = conn.execute("SELECT id FROM hebrew_nodes WHERE category=?", (cat,)).fetchall()
            for n in nodes:
                conn.execute(
                    "INSERT OR REPLACE INTO hebrew_progress (user_id, node_id, mastery, attempts, correct, last_practiced) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                    (user_id, n[0], 0.7, 1, 1))
        # Below 60% → no credit, full curriculum

    conn.commit()
    conn.close()

    return {"ok": True, "data": {"message": "Diagnostic applied. Categories with 100% accuracy were skipped."}}


@router.get("/api/v1/hebrew/curriculum")
def get_hebrew_curriculum(user_id: str = "default"):
    if not MEM_DB.exists():
        return {"ok": True, "data": {"nodes": [], "total": 0}}
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    nodes = conn.execute("""
        SELECT n.*, COUNT(DISTINCT e.source_id) as prereq_count,
               COUNT(DISTINCT e2.source_id) as dependent_count,
               COALESCE(p.mastery,0) as mastery, COALESCE(p.attempts,0) as attempts,
               COALESCE(p.correct,0) as correct, COALESCE(l.content_json,'') as has_content
        FROM hebrew_nodes n
        LEFT JOIN hebrew_edges e ON e.target_id=n.id
        LEFT JOIN hebrew_edges e2 ON e2.source_id=n.id
        LEFT JOIN hebrew_progress p ON p.node_id=n.id AND p.user_id=?
        LEFT JOIN hebrew_lessons l ON l.node_id=n.id
        GROUP BY n.id ORDER BY n.level, n.id
    """, (user_id,)).fetchall()
    result_nodes = []
    for n in nodes:
        prereqs = conn.execute("""
            SELECT e.source_id, n.title, n.level, COALESCE(p.mastery,0) as mastery
            FROM hebrew_edges e JOIN hebrew_nodes n ON n.id=e.source_id
            LEFT JOIN hebrew_progress p ON p.node_id=e.source_id AND p.user_id=?
            WHERE e.target_id=?
        """, (user_id, n['id'])).fetchall()
        prereq_list = [dict(r) for r in prereqs]
        all_mastered = all(r['mastery'] >= 0.8 for r in prereq_list) if prereq_list else True
        result_nodes.append({
            "id": n['id'], "title": n['title'], "category": n['category'],
            "level": n['level'], "description": n['description'],
            "mastery": n['mastery'], "attempts": n['attempts'], "correct": n['correct'],
            "prerequisite_count": n['prereq_count'], "dependent_count": n['dependent_count'],
            "prerequisites": prereq_list, "unlocked": all_mastered, "has_content": bool(n['has_content']),
        })
    conn.close()

    # ── Add per-node learning speeds from student-topic calibration ──
    try:
        speeds, overall_ability, _ = compute_learning_speed(user_id)
    except Exception:
        speeds, overall_ability = {}, 0.5

    for n in result_nodes:
        n['learning_speed'] = round(speeds.get(n['id'], 1.0), 3)

    # ── Non-Interference: reorder to separate confusable pairs ──
    # Load confusability pairs from DB
    try:
        conn2 = sqlite3.connect(str(MEM_DB))
        confusable = conn2.execute(
            "SELECT node_a, node_b FROM hebrew_confusability").fetchall()
        conn2.close()
    except Exception:
        confusable = []

    if confusable:
        # Build a set of confusable pairs for O(1) lookup
        conf_set = set()
        for a, b in confusable:
            conf_set.add((a, b))
            conf_set.add((b, a))

        # Reorder: scan through nodes, if adjacent pair is confusable,
        # swap the second node with the next non-confusable node
        ordered = list(result_nodes)
        i = 0
        max_attempts = len(ordered) * 3  # prevent infinite loops
        attempts = 0
        while i < len(ordered) - 1 and attempts < max_attempts:
            attempts += 1
            current_id = ordered[i]['id']
            next_id = ordered[i + 1]['id']
            if (current_id, next_id) in conf_set:
                # Swap i+1 with the first non-confusable node later in the list
                swapped = False
                for j in range(i + 2, len(ordered)):
                    candidate_id = ordered[j]['id']
                    if (current_id, candidate_id) not in conf_set:
                        ordered[i + 1], ordered[j] = ordered[j], ordered[i + 1]
                        swapped = True
                        break
                if not swapped:
                    # Can't avoid — confusable pair is unavoidable
                    pass
            i += 1
        result_nodes = ordered

    total = len(result_nodes)
    mastered = sum(1 for n in result_nodes if n['mastery'] >= 0.8)
    in_progress = sum(1 for n in result_nodes if 0 < n['mastery'] < 0.8)
    locked = sum(1 for n in result_nodes if not n['unlocked'])
    # Compute speed distribution for summary
    if speeds:
        speed_values = [speeds.get(n['id'], 1.0) for n in result_nodes if n['id'] in speeds]
        avg_speed = round(sum(speed_values) / len(speed_values), 3) if speed_values else 1.0
    else:
        avg_speed = 1.0

    return {"ok": True, "data": {
        "nodes": result_nodes, "total": total, "mastered": mastered,
        "in_progress": in_progress, "locked": locked,
        "overall_ability": overall_ability,
        "avg_learning_speed": avg_speed,
        "categories": ["consonant","vowel","syllable","word","verb","noun","grammar","syntax","reading","root","phrase"],
    }}


@router.post("/api/v1/hebrew/progress")
def update_hebrew_progress(body: dict):
    if not MEM_DB.exists():
        raise HTTPException(404, "Hebrew DB not found")
    user_id = body.get("user_id", "default")
    node_id = body.get("node_id", "")
    correct = body.get("correct", False)
    if not node_id:
        raise HTTPException(400, "node_id required")
    conn = sqlite3.connect(str(MEM_DB))
    row = conn.execute(
        "SELECT mastery, attempts, correct FROM hebrew_progress WHERE user_id=? AND node_id=?",
        (user_id, node_id)).fetchone()
    if row:
        attempts = row[1] + 1
        correct_count = row[2] + (1 if correct else 0)
        mastery = min(1.0, correct_count / max(attempts, 1) * (1 - 1 / (attempts + 2)))
        conn.execute(
            "UPDATE hebrew_progress SET mastery=?, attempts=?, correct=?, last_practiced=datetime('now') WHERE user_id=? AND node_id=?",
            (round(mastery, 3), attempts, correct_count, user_id, node_id))
    else:
        attempts = 1
        correct_count = 1 if correct else 0
        mastery = 0.8 if correct else 0.0
        conn.execute(
            "INSERT INTO hebrew_progress (user_id, node_id, mastery, attempts, correct, last_practiced) VALUES (?,?,?,?,?, datetime('now'))",
            (user_id, node_id, round(mastery, 3), attempts, correct_count))
    conn.commit()
    conn.close()
    return {"ok": True, "data": {"node_id": node_id, "mastery": round(mastery, 3),
                                  "attempts": attempts, "correct": correct_count}}


@router.get("/api/v1/hebrew/practice/{node_id}")
def get_hebrew_practice(node_id: str):
    if not MEM_DB.exists():
        return {"ok": True, "data": {"items": [], "total": 0}}
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    items = conn.execute(
        "SELECT * FROM hebrew_practice_items WHERE node_id=? ORDER BY RANDOM()", (node_id,)).fetchall()
    conn.close()
    result = []
    for item in items:
        result.append({
            "id": item['id'], "question_type": item['question_type'],
            "question_text": item['question_text'], "options_json": item['options_json'],
            "correct_answer": item['correct_answer'], "explanation": item['explanation'] or '',
            "difficulty": item['difficulty'],
        })
    random.shuffle(result)
    return {"ok": True, "data": {"items": result, "total": len(result)}}


@router.get("/api/v1/hebrew/audio/{word:path}")
def get_hebrew_audio(word: str):
    word_clean = word.strip()
    if not word_clean:
        raise HTTPException(400, "Word required")
    conn = get_db()
    rows = conn.execute(
        "SELECT verse_id, word_timestamps, source_file FROM audio_timestamps WHERE word_timestamps LIKE ? LIMIT 10",
        (f'%{word_clean}%',)).fetchall()
    conn.close()
    for r in rows:
        try:
            wts = json.loads(r['word_timestamps'])
            for wt in wts:
                wt_word = wt.get('word', '')
                def norm(w):
                    w = w.strip().replace('/','')
                    w = re.sub(r'[\u0591-\u05AF]','',w)
                    return w.replace('ך','כ').replace('ם','מ').replace('ן','נ').replace('ף','פ').replace('ץ','צ')
                if norm(wt_word) == norm(word_clean):
                    return {"ok": True, "data": {
                        "audio_url": f"/api/v1/audio/play-raw/{r['source_file']}?start={wt['start']}&end={wt['end']}",
                        "word": word_clean, "source": r['source_file'],
                        "start": wt['start'], "end": wt['end'],
                    }}
        except Exception:
            continue
    align_dir = BASE_DIR / "data" / "audio" / "alignments"
    if align_dir.exists():
        for af in sorted(align_dir.glob("*.json")):
            try:
                with open(af) as f:
                    data = json.load(f)
                for wt in data.get('words', []):
                    ww = wt.get('word','') if isinstance(wt, dict) else ''
                    if word_clean in ww or ww in word_clean:
                        return {"ok": True, "data": {
                            "audio_url": f"/api/v1/audio/play-raw/gen_1.wav?start={wt['start']}&end={wt['end']}",
                            "word": word_clean, "source": "gen_1.wav",
                            "start": wt['start'], "end": wt['end'],
                        }}
            except Exception:
                continue
    # Fallback: check pre-generated letter audio files
    letter_path = BASE_DIR / "data" / "audio" / "letters" / f"{word_clean}.wav"
    if letter_path.exists():
        return {"ok": True, "data": {
            "audio_url": f"/api/v1/audio/letter/{word_clean}",
            "word": word_clean,
            "source": "letters",
            "start": 0, "end": 0,
        }}
    raise HTTPException(404, f"No audio found for: {word_clean}")


@router.get("/api/v1/hebrew/review-queue")
def get_hebrew_review_queue(user_id: str = "default", limit: int = 10):
    if not MEM_DB.exists():
        return {"ok": True, "data": {"reviews": [], "due_count": 0}}
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    now = datetime.datetime.now()
    rows = conn.execute("""
        SELECT p.node_id, n.title, n.level, n.category, n.description,
               p.mastery, p.attempts, p.correct, p.last_practiced
        FROM hebrew_progress p JOIN hebrew_nodes n ON n.id=p.node_id
        WHERE p.user_id=? ORDER BY p.last_practiced DESC
    """, (user_id,)).fetchall()
    due = []
    for r in rows:
        last_str = r['last_practiced']
        if not last_str: continue
        try:
            last_time = datetime.datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        days = (now - last_time).total_seconds() / 86400.0
        m = r['mastery']
        a = r['attempts']
        c = r['correct']

        # FSRS-5 based stability estimation from progress data
        if a > 0 and c > 0:
            # Estimate: stability grows with attempts and correctness
            stability = max(1.0, a * m * 7.0)
            max(1.0, min(10.0, 5.0 - m * 3.0))
            ret = fsrs_retrievability(stability, days)
        else:
            stability = 1.0
            ret = math.exp(-days / stability) if stability > 0 else 0

        if ret < 0.9:
            # Get learning speed for this user+node
            try:
                speeds, _, _ = compute_learning_speed(user_id)
                lr = speeds.get(r['node_id'], 1.0)
            except Exception:
                lr = 1.0
            due.append({
                "node_id": r['node_id'], "title": r['title'], "level": r['level'],
                "category": r['category'], "description": r['description'],
                "mastery": m, "attempts": a, "correct": c,
                "days_since": round(days, 1), "stability": round(stability, 1),
                "retrievability": round(ret, 3), "learning_speed": round(lr, 3),
                "last_practiced": last_str,
            })
    # ── Systematic Interleaving + Non-Interference ──
    # 1. Group by category
    from collections import defaultdict
    by_cat = defaultdict(list)
    for item in due:
        by_cat[item['category']].append(item)

    # 2. Load confusability pairs for non-interference enforcement
    confusable_pairs = set()
    try:
        conn2 = sqlite3.connect(str(MEM_DB))
        conf_rows = conn2.execute(
            "SELECT node_a, node_b FROM hebrew_confusability").fetchall()
        conn2.close()
        for a, b in conf_rows:
            confusable_pairs.add((a, b))
            confusable_pairs.add((b, a))
    except Exception:
        pass

    # 3. Sort categories by their lowest retrievability (most urgent first)
    cat_priority = sorted(by_cat.keys(), key=lambda c: min(i['retrievability'] for i in by_cat[c]))

    # 4. Round-robin with strict non-interference
    interleaved = []
    {c: iter(sorted(by_cat[c], key=lambda x: x['retrievability'])) for c in cat_priority}
    remaining = {c: len(by_cat[c]) for c in cat_priority}
    cat_cycle = list(cat_priority)  # mutable copy for cycling

    last_cat = None
    # Non-interference buffer: track recent node_ids to enforce ≥3 spacing for confusable pairs
    recent_nodes = []  # last 3 node_ids added

    for _ in range(len(due)):
        chosen_cat = None

        # Try categories in round-robin order, skipping last_cat and categories
        # whose remaining items are all confusable with recent nodes
        for c in cat_cycle:
            if remaining.get(c, 0) == 0:
                continue
            if c == last_cat:
                continue
            # Check if ALL remaining items in this category would be confusable
            # with any of the recent 3 nodes
            cat_items = sorted(by_cat[c], key=lambda x: x['retrievability'])
            untaken = [it for it in cat_items if it not in interleaved]
            if untaken:
                candidate = untaken[0]
                # Non-interference check: skip if candidate is confusable with recent nodes
                if recent_nodes and any(
                    (candidate['node_id'], recent_nid) in confusable_pairs
                    for recent_nid in recent_nodes[-3:]
                ):
                    continue  # skip this category for now — would cause interference
            chosen_cat = c
            break

        if not chosen_cat:
            # Fallback: pick from any remaining category regardless
            for c in cat_cycle:
                if remaining.get(c, 0) > 0:
                    chosen_cat = c
                    break

        if not chosen_cat:
            break

        # Pick the most urgent item from this category
        cat_items_sorted = sorted(by_cat[chosen_cat], key=lambda x: x['retrievability'])
        item = None
        for candidate in cat_items_sorted:
            if candidate not in interleaved:
                item = candidate
                break

        if not item:
            remaining[chosen_cat] = 0
            continue

        # Check if this specific item is confusable with any of the last 3 items
        if recent_nodes and any(
            (item['node_id'], recent_nid) in confusable_pairs
            for recent_nid in recent_nodes[-3:]
        ):
            # Try to find a different item in the same category that's not confusable
            for alternative in cat_items_sorted:
                if alternative not in interleaved and alternative['node_id'] != item['node_id'] and not any(
                    (alternative['node_id'], recent_nid) in confusable_pairs
                    for recent_nid in recent_nodes[-3:]
                ):
                    item = alternative
                    break

        interleaved.append(item)
        remaining[chosen_cat] -= 1
        last_cat = chosen_cat
        recent_nodes.append(item['node_id'])
        if len(recent_nodes) > 6:
            recent_nodes.pop(0)

        # Rotate cat_cycle for true round-robin
        cat_cycle = cat_cycle[1:] + cat_cycle[:1]

    conn.close()

    # Add confusability_warning to items that have confusable counterparts in the queue
    queued_ids = set(it['node_id'] for it in interleaved[:limit])
    for item in interleaved[:limit]:
        conf_with = [nid for nid in queued_ids if (item['node_id'], nid) in confusable_pairs and nid != item['node_id']]
        item['confusability_warning'] = conf_with if conf_with else []

    # ── Repetition Compression ──
    # Scan for items where one encompasses another (via the knowledge graph)
    compressed = []
    used_in_compression = set()

    for i, item in enumerate(interleaved[:limit]):
        if item['node_id'] in used_in_compression:
            continue

        # Check if any LATER items in the queue are encompassed by this one
        # (encompassing = this item's mastery would give implicit credit to the simpler item)
        compressed_group = [item]

        # Get this item's prerequisites from the graph
        prereqs_of_current = HEBREW_GRAPH.get(item['node_id'], [])

        for j in range(i + 1, min(i + 5, len(interleaved))):
            later_item = interleaved[j]
            if later_item['node_id'] in used_in_compression:
                continue
            # If the later item is a prerequisite (simpler skill), it's encompassed
            if later_item['node_id'] in prereqs_of_current:
                compressed_group.append(later_item)
                used_in_compression.add(later_item['node_id'])
            # Also check if they share the same category and are from the same level family
            # (e.g., qal_perfect + qal_imperfect both in verb category)
            elif (later_item['category'] == item['category']
                  and later_item['level'] == item['level']
                  and len(compressed_group) < 3):
                # Same category+level = likely similar topic, compress
                compressed_group.append(later_item)
                used_in_compression.add(later_item['node_id'])

        if len(compressed_group) > 1:
            compressed.append({
                "type": "compressed",
                "title": f"{compressed_group[0]['category'].title()} Review",
                "items": compressed_group,
                "count": len(compressed_group),
                "primary_node_id": compressed_group[0]['node_id'],
                "question": f"Review {compressed_group[0]['category']}: " +
                           ", ".join(it['title'] for it in compressed_group),
            })
        else:
            compressed.append(item)

    return {"ok": True, "data": {
        "reviews": compressed[:limit],
        "due_count": len(due),
        "total_practiced": len(rows),
        "compression_savings": len(interleaved[:limit]) - len(compressed),
    }}


@router.get("/api/v1/hebrew/verb-drill")
def get_hebrew_verb_drill(count: int = 5, user_id: str = "default"):
    if not MEM_DB.exists():
        return {"ok": True, "data": {"drills": []}}
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    verb_lessons = conn.execute(
        "SELECT n.id, n.title, l.content_json FROM hebrew_nodes n "
        "JOIN hebrew_lessons l ON l.node_id=n.id WHERE n.category='verb'").fetchall()
    drills = []
    for lesson in verb_lessons:
        try:
            content = json.loads(lesson['content_json'])
        except (json.JSONDecodeError, ValueError):
            continue
        title = lesson['title']
        nid = lesson['id']
        expl = content.get('explanation', '')
        if 'perfect' in nid or 'imperfect' in nid:
            tense = 'perfect' if 'perfect' in nid else 'imperfect'
            drills.append({
                "node_id": nid,
                "question": f"What does the {title} verb form express?",
                "type": "multiple_choice",
                "options": json.dumps(["Completed action","Incomplete/future action","Command","Emphasis"]),
                "correct": "Completed action" if tense == 'perfect' else "Incomplete/future action",
                "explanation": expl.split('.')[0][:100] if expl else '',
            })
            drills.append({
                "node_id": nid, "question": f"What is the 3ms form of the {title}?",
                "type": "recall", "options": "", "correct": f"3ms {title}",
                "explanation": f"The 3ms is the base form of {title}.",
            })
        if 'qal' in nid:
            drills.append({"node_id":nid,"question":"Which binyan is the simple active stem?","type":"multiple_choice",
                "options":json.dumps(["Qal","Niphal","Piel","Hiphil"]),"correct":"Qal",
                "explanation":"Qal is the simple active stem (he killed)."})
        if 'niphal' in nid:
            drills.append({"node_id":nid,"question":"Which binyan is the simple passive stem?","type":"multiple_choice",
                "options":json.dumps(["Qal","Niphal","Pual","Hophal"]),"correct":"Niphal",
                "explanation":"Niphal is the simple passive (he was killed)."})
        if 'piel' in nid:
            drills.append({"node_id":nid,"question":"Which binyan is the intensive active stem?","type":"multiple_choice",
                "options":json.dumps(["Qal","Piel","Hiphil","Hithpael"]),"correct":"Piel",
                "explanation":"Piel is the intensive active (he slaughtered)."})
        if 'hiphil' in nid:
            drills.append({"node_id":nid,"question":"Which binyan is the causative active stem?","type":"multiple_choice",
                "options":json.dumps(["Piel","Hiphil","Hophal","Hithpael"]),"correct":"Hiphil",
                "explanation":"Hiphil is the causative active (he caused to kill)."})
    if not drills:
        drills.append({"node_id":"qal_perfect","question":"What is the function of the Qal binyan?","type":"multiple_choice",
            "options":json.dumps(["Simple active","Simple passive","Intensive","Causative"]),"correct":"Simple active",
            "explanation":"Qal is the simple active stem, the most common binyan."})
    random.shuffle(drills)
    conn.close()
    return {"ok": True, "data": {"drills": drills[:count], "total": len(drills)}}


@router.get("/api/v1/hebrew/lesson/{node_id}")
def get_hebrew_lesson(node_id: str):
    if not MEM_DB.exists():
        raise HTTPException(404, "Hebrew lesson DB not found")
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    node = conn.execute("SELECT * FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
    if not node:
        conn.close()
        raise HTTPException(404, f"Lesson not found: {node_id}")
    lesson = conn.execute("SELECT * FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
    practices = conn.execute("SELECT * FROM hebrew_practice_items WHERE node_id=?", (node_id,)).fetchall()
    prereqs = conn.execute(
        "SELECT n.id,n.title,n.category,n.level FROM hebrew_edges e JOIN hebrew_nodes n ON n.id=e.source_id WHERE e.target_id=?",
        (node_id,)).fetchall()

    # Get verse attestations (multiple witnesses)
    try:
        scr_conn = sqlite3.connect(str(SCRIPTURE_DB))
        scr_conn.row_factory = sqlite3.Row
        att_rows = conn.execute("""
            SELECT a.verse_id, a.explanation, a.attestation_type
            FROM hebrew_attestations a
            WHERE a.node_id=?
            ORDER BY a.attestation_type, a.id
            LIMIT 15
        """, (node_id,)).fetchall()

        # Fetch verse text in batch
        att_list = []
        for a in att_rows:
            vid = a['verse_id']
            txt = scr_conn.execute("SELECT text_english, text_hebrew FROM verses WHERE id=?", (vid,)).fetchone()
            att_list.append({
                "verse_id": vid,
                "explanation": a['explanation'] or '',
                "attestation_type": a['attestation_type'] or '',
                "text": txt[0][:200] if txt and txt[0] else '',
                "text_hebrew": txt[1] if txt and txt[1] else '',
            })
        scr_conn.close()
    except Exception:
        att_list = []

    conn.close()

    result = dict(node)
    if lesson:
        try:
            c = lesson['content_json']
            result["lesson"] = json.loads(c) if c.startswith("{") else c
        except (json.JSONDecodeError, ValueError):
            result["lesson"] = lesson['content_json']
    result["practice_items"] = [dict(p) for p in practices]
    result["prerequisites"] = [dict(p) for p in prereqs]
    result["verse_attestations"] = att_list

    return {"ok": True, "data": result}


# ── Gamification: XP, Streaks, Badges, Connection Discovery ──

def _ensure_gamification_table():
    """Create gamification tables if they don't exist."""
    if not MEM_DB.exists():
        return
    conn = sqlite3.connect(str(MEM_DB))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hebrew_gamification (
            user_id TEXT NOT NULL DEFAULT 'default',
            xp INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_review_date TEXT,
            best_streak INTEGER DEFAULT 0,
            insight_xp INTEGER DEFAULT 0,
            PRIMARY KEY (user_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hebrew_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            badge_id TEXT NOT NULL,
            earned_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, badge_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hebrew_seen_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            connection_key TEXT NOT NULL,
            seen_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, connection_key)
        )
    """)
    conn.commit()
    conn.close()


def _get_gamification(user_id="default"):
    """Get current gamification state for a user."""
    _ensure_gamification_table()
    if not MEM_DB.exists():
        return {"xp": 0, "streak": 0, "best_streak": 0, "insight_xp": 0}
    conn = sqlite3.connect(str(MEM_DB))
    row = conn.execute(
        "SELECT xp, streak_count, last_review_date, best_streak, insight_xp "
        "FROM hebrew_gamification WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row:
        return {
            "xp": row[0], "streak": row[1],
            "last_review_date": row[2], "best_streak": row[3], "insight_xp": row[4],
        }
    return {"xp": 0, "streak": 0, "best_streak": 0, "insight_xp": 0}


def _update_streak(user_id="default"):
    """Update streak counter based on consecutive days."""
    _ensure_gamification_table()
    if not MEM_DB.exists():
        return 0
    conn = sqlite3.connect(str(MEM_DB))
    row = conn.execute(
        "SELECT streak_count, best_streak, last_review_date FROM hebrew_gamification WHERE user_id=?",
        (user_id,)).fetchone()

    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    if row:
        _, best, last_date = row
        if last_date == today:
            # Already practiced today — keep streak
            streak = _
            conn.close()
            return streak
        elif last_date == yesterday:
            # Consecutive day — increment
            streak = _ + 1
            best = max(best, streak)
            conn.execute(
                "UPDATE hebrew_gamification SET streak_count=?, best_streak=?, last_review_date=? WHERE user_id=?",
                (streak, best, today, user_id))
        else:
            # Streak broken
            streak = 1
            conn.execute(
                "UPDATE hebrew_gamification SET streak_count=?, last_review_date=? WHERE user_id=?",
                (1, today, user_id))
    else:
        # First review ever
        streak = 1
        conn.execute(
            "INSERT INTO hebrew_gamification (user_id, xp, streak_count, last_review_date, best_streak) VALUES (?, 0, 1, ?, 1)",
            (user_id, today))

    conn.commit()
    conn.close()
    return streak


def _award_xp(user_id="default", amount=10, reason=""):
    """Award XP to a user and return new total."""
    _ensure_gamification_table()
    if not MEM_DB.exists():
        return 0
    conn = sqlite3.connect(str(MEM_DB))
    row = conn.execute(
        "SELECT xp FROM hebrew_gamification WHERE user_id=?", (user_id,)).fetchone()
    if row:
        new_xp = row[0] + amount
        conn.execute("UPDATE hebrew_gamification SET xp=? WHERE user_id=?", (new_xp, user_id))
    else:
        new_xp = amount
        conn.execute(
            "INSERT INTO hebrew_gamification (user_id, xp, streak_count, last_review_date, best_streak) VALUES (?, ?, 0, '', 0)",
            (user_id, new_xp))
    conn.commit()
    conn.close()

    # Check for new badges
    new_badges = _check_badges(user_id)

    return new_xp, new_badges


def _check_badges(user_id="default"):
    """Check and award any newly earned badges. Returns list of new badges."""
    _ensure_gamification_table()
    if not MEM_DB.exists():
        return []

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    # Get user state
    gam = _get_gamification(user_id)

    # Get progress stats
    total_mastered = conn.execute(
        "SELECT COUNT(*) FROM hebrew_progress WHERE user_id=? AND mastery>=0.8",
        (user_id,)).fetchone()[0]
    level1_mastered = conn.execute(
        "SELECT COUNT(*) FROM hebrew_progress p JOIN hebrew_nodes n ON n.id=p.node_id WHERE p.user_id=? AND n.level=1 AND p.mastery>=0.8",
        (user_id,)).fetchone()[0]
    level2_mastered = conn.execute(
        "SELECT COUNT(*) FROM hebrew_progress p JOIN hebrew_nodes n ON n.id=p.node_id WHERE p.user_id=? AND n.level=2 AND p.mastery>=0.8",
        (user_id,)).fetchone()[0]
    verb_count = conn.execute(
        "SELECT COUNT(*) FROM hebrew_progress p JOIN hebrew_nodes n ON n.id=p.node_id WHERE p.user_id=? AND n.category='verb' AND p.mastery>=0.8",
        (user_id,)).fetchone()[0]
    total_items = conn.execute(
        "SELECT COUNT(*) FROM hebrew_practice_items WHERE node_id IN (SELECT node_id FROM hebrew_progress WHERE user_id=? AND attempts>0)",
        (user_id,)).fetchone()[0]
    conn.close()

    # Define badge criteria
    badge_defs = {
        "first_review": {"name": "First Steps", "icon": "👣", "check": lambda: gam['xp'] >= 10},
        "aleph_champion": {"name": "Aleph Champion", "icon": "א", "check": lambda: level1_mastered >= 27},
        "vowel_master": {"name": "Vowel Master", "icon": "ַ", "check": lambda: level2_mastered >= 19},
        "binyan_explorer": {"name": "Binyan Explorer", "icon": "ע", "check": lambda: verb_count >= 5},
        "centurion": {"name": "Centurion", "icon": "💯", "check": lambda: total_items >= 100},
        "week_warrior": {"name": "Weekly Warrior", "icon": "📅", "check": lambda: gam['best_streak'] >= 7},
        "iron_will": {"name": "Iron Will", "icon": "⚔️", "check": lambda: gam['best_streak'] >= 30},
        "quarter_mastery": {"name": "Quarter Master", "icon": "📊", "check": lambda: total_mastered >= 25},
        "half_century": {"name": "Half Century", "icon": "🏛️", "check": lambda: total_mastered >= 50},
        "insight_seeker": {"name": "Insight Seeker", "icon": "🔍", "check": lambda: gam['insight_xp'] >= 50},
    }

    # Check each badge
    earned_ids = set(r['badge_id'] for r in conn.execute(
        "SELECT badge_id FROM hebrew_badges WHERE user_id=?", (user_id,)).fetchall()) if conn else set()

    new_badges = []
    for bid, bdef in badge_defs.items():
        if bid not in earned_ids and bdef["check"]():
            conn.execute(
                "INSERT OR IGNORE INTO hebrew_badges (user_id, badge_id) VALUES (?, ?)",
                (user_id, bid))
            new_badges.append({"badge_id": bid, "name": bdef["name"], "icon": bdef["icon"]})

    if conn:
        conn.commit()
        conn.close()

    return new_badges


def _award_insight_xp(user_id, node_id, amount=5):
    """Award Insight XP for discovering a new connection through the graph."""
    _ensure_gamification_table()
    if not MEM_DB.exists():
        return 0, []

    conn = sqlite3.connect(str(MEM_DB))

    # Get connections for this node from the scripture connection graph
    connections = []
    try:
        scripture_conn = sqlite3.connect(str(SCRIPTURE_DB))
        rows = scripture_conn.execute(
            "SELECT DISTINCT connection_type, target_verse FROM knowledge_items WHERE verse_id=? AND star_rating >= 3 LIMIT 20",
            (f"{node_id}",)).fetchall()
        scripture_conn.close()
        connections = [{"type": r[0], "target": r[1]} for r in rows]
    except Exception:
        pass

    # Count how many are new to this user
    new_connections = 0
    for conn_data in connections:
        key = f"{node_id}:{conn_data['type']}:{conn_data['target']}"
        existing = conn.execute(
            "SELECT 1 FROM hebrew_seen_connections WHERE user_id=? AND connection_key=?",
            (user_id, key)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO hebrew_seen_connections (user_id, connection_key) VALUES (?, ?)",
                (user_id, key))
            new_connections += 1

    if new_connections == 0:
        conn.close()
        return 0, []

    # Award insight XP
    insight_amount = amount * new_connections
    row = conn.execute(
        "SELECT xp, insight_xp FROM hebrew_gamification WHERE user_id=?", (user_id,)).fetchone()
    if row:
        conn.execute(
            "UPDATE hebrew_gamification SET xp=xp+?, insight_xp=insight_xp+? WHERE user_id=?",
            (insight_amount, insight_amount, user_id))
    else:
        conn.execute(
            "INSERT INTO hebrew_gamification (user_id, xp, insight_xp) VALUES (?, ?, ?)",
            (user_id, insight_amount, insight_amount))

    conn.commit()
    conn.close()

    new_badges = _check_badges(user_id)
    return insight_amount, new_badges, new_connections


@router.get("/api/v1/hebrew/gamification")
def get_hebrew_gamification(user_id: str = "default"):
    """Get gamification state: XP, streak, badges, and next achievements."""
    _ensure_gamification_table()
    gam = _get_gamification(user_id)

    # Get earned badges
    badges = []
    if MEM_DB.exists():
        conn = sqlite3.connect(str(MEM_DB))
        rows = conn.execute(
            "SELECT badge_id, earned_at FROM hebrew_badges WHERE user_id=? ORDER BY earned_at",
            (user_id,)).fetchall()
        conn.close()
        for r in rows:
            badges.append({"badge_id": r[0], "earned_at": r[1]})

    # List all possible badges with earned status
    badge_catalog = [
        {"id": "first_review", "name": "First Steps", "icon": "👣", "desc": "Earn your first 10 XP"},
        {"id": "aleph_champion", "name": "Aleph Champion", "icon": "א", "desc": "Master all Level 1 (Aleph-Bet) topics"},
        {"id": "vowel_master", "name": "Vowel Master", "icon": "ַ", "desc": "Master all Level 2 (Vowels)"},
        {"id": "binyan_explorer", "name": "Binyan Explorer", "icon": "ע", "desc": "Master 5+ verb binyanim"},
        {"id": "centurion", "name": "Centurion", "icon": "💯", "desc": "Complete 100 practice items"},
        {"id": "week_warrior", "name": "Weekly Warrior", "icon": "📅", "desc": "Maintain a 7-day streak"},
        {"id": "iron_will", "name": "Iron Will", "icon": "⚔️", "desc": "Maintain a 30-day streak"},
        {"id": "quarter_mastery", "name": "Quarter Master", "icon": "📊", "desc": "Master 25 topics"},
        {"id": "half_century", "name": "Half Century", "icon": "🏛️", "desc": "Master 50 topics"},
        {"id": "insight_seeker", "name": "Insight Seeker", "icon": "🔍", "desc": "Discover 50 connections"},
    ]

    earned_ids = set(b['badge_id'] for b in badges)
    for b in badge_catalog:
        b['earned'] = b['id'] in earned_ids

    return {"ok": True, "data": {
        "xp": gam['xp'],
        "streak": gam['streak'],
        "best_streak": gam['best_streak'],
        "insight_xp": gam['insight_xp'],
        "badges": badges,
        "badge_catalog": badge_catalog,
        "badge_count": len(badges),
        "next_badges": [b for b in badge_catalog if not b['earned']][:3],
    }}


@router.get("/api/v1/hebrew/insight/{node_id}")
def get_hebrew_insight(node_id: str, user_id: str = "default"):
    """Discover connections for a node through the scripture graph and earn Insight XP."""
    result = _award_insight_xp(user_id, node_id)
    amount, new_badges, new_connections = result if len(result) == 3 else (result[0], result[1], 0)

    # Also return the connections that were found
    connections = []
    try:
        scripture_conn = sqlite3.connect(str(SCRIPTURE_DB))
        rows = scripture_conn.execute(
            "SELECT connection_type, target_verse, star_rating FROM knowledge_items WHERE verse_id=? AND star_rating >= 3 ORDER BY star_rating DESC LIMIT 10",
            (f"{node_id}",)).fetchall()
        scripture_conn.close()
        connections = [{"type": r[0], "target": r[1], "quality": r[2]} for r in rows]
    except Exception:
        pass

    return {"ok": True, "data": {
        "node_id": node_id,
        "insight_xp_awarded": amount,
        "new_connections": new_connections,
        "total_connections": len(connections),
        "connections": connections,
        "new_badges": new_badges,
    }}


# ── Grammar Reference ──

@router.get("/api/v1/grammar-reference")
def search_grammar_reference(q: str = "", section: str = "", paragraph_id: int = 0, limit: int = 10):
    if not MEM_DB.exists():
        raise HTTPException(404, "Grammar reference DB not found")
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    if paragraph_id > 0:
        row = conn.execute("SELECT * FROM grammar_reference WHERE paragraph_id=?", (paragraph_id,)).fetchone()
        conn.close()
        if not row:
            raise HTTPException(404, f"Paragraph {paragraph_id} not found")
        return {"ok": True, "data": dict(row)}
    query = "SELECT paragraph_id, section, subsection, summary, hebrew_examples FROM grammar_reference WHERE 1=1"
    params = []
    if q:
        query += " AND (summary LIKE ? OR subsection LIKE ?)"
        params.extend([f'%{q}%', f'%{q}%'])
    if section:
        query += " AND section = ?"
        params.append(section)
    query += " ORDER BY paragraph_id LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"ok": True, "data": {"results": [dict(r) for r in rows], "total": len(rows),
                                  "sections": ["Écriture", "Morphologie", "Syntaxe", "Introduction"]}}
