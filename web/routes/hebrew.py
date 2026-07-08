"""Hebrew learning + grammar reference routes."""
import json
import os
import random
import re
import sqlite3
import datetime
import math
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
MEM_DB = BASE_DIR / "data" / "memorize.db"
SCRIPTURE_DB = BASE_DIR / "data" / "processed" / "scripture.db"


def get_db():
    """Get scripture database connection."""
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()


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
    total = len(result_nodes)
    mastered = sum(1 for n in result_nodes if n['mastery'] >= 0.8)
    in_progress = sum(1 for n in result_nodes if 0 < n['mastery'] < 0.8)
    locked = sum(1 for n in result_nodes if not n['unlocked'])
    return {"ok": True, "data": {
        "nodes": result_nodes, "total": total, "mastered": mastered,
        "in_progress": in_progress, "locked": locked,
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
        except:
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
            except:
                continue
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
        except:
            continue
        days = (now - last_time).total_seconds() / 86400.0
        m = r['mastery']
        stab = 1.0
        if m >= 0.9: stab = 21.0
        elif m >= 0.8: stab = 14.0
        elif m >= 0.6: stab = 7.0
        elif m >= 0.4: stab = 3.0
        stab *= min(r['attempts'], 10) / 3.0
        stab = min(stab, 90.0)
        ret = math.exp(-days / stab) if stab > 0 else 0
        if ret < 0.9:
            due.append({
                "node_id": r['node_id'], "title": r['title'], "level": r['level'],
                "category": r['category'], "description": r['description'],
                "mastery": m, "attempts": r['attempts'], "correct": r['correct'],
                "days_since": round(days, 1), "stability": round(stab, 1),
                "retrievability": round(ret, 3), "last_practiced": last_str,
            })
    due.sort(key=lambda x: x['retrievability'])
    conn.close()
    return {"ok": True, "data": {"reviews": due[:limit], "due_count": len(due), "total_practiced": len(rows)}}


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
        except:
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
        "SELECT n.id,n.title,n.category FROM hebrew_edges e JOIN hebrew_nodes n ON n.id=e.source_id WHERE e.target_id=?",
        (node_id,)).fetchall()
    conn.close()
    result = dict(node)
    if lesson:
        try:
            c = lesson['content_json']
            result["lesson"] = json.loads(c) if c.startswith("{") else c
        except:
            result["lesson"] = lesson['content_json']
    result["practice_items"] = [dict(p) for p in practices]
    result["prerequisites"] = [dict(p) for p in prereqs]
    return {"ok": True, "data": result}


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
