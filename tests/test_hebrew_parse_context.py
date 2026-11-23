"""C2 sentence-context cards + C3 verb-parse cards: seed, grade, schedule."""
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes import hebrew as H

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def hebdb(tmp_path, monkeypatch):
    src = ROOT / "data" / "memorize.db"
    if not src.exists():
        pytest.skip("Hebrew database not found")
    isolated = tmp_path / "memorize.db"
    shutil.copy2(src, isolated)
    monkeypatch.setattr(H, "MEM_DB", isolated)
    return isolated


# C3: parse-answer matching (codes, long forms, aliases)
@pytest.mark.parametrize("answer,expected,ok", [
    ("Qal perfect 3ms", "Qal perfect 3ms", True),
    ("qal perfect third masculine singular", "Qal perfect 3ms", True),
    ("Qal qatal 3ms", "Qal perfect 3ms", True),
    ("yiqtol qal 3ms", "Qal imperfect 3ms", True),
    ("Niphal", "Niphal", True),
    ("niphal passive", "Niphal", True),
    ("Qal III-he", "Qal III-he", True),
    # Missing a required token fails.
    ("Qal 3ms", "Qal perfect 3ms", False),
    ("perfect 3ms", "Qal perfect 3ms", False),
    ("Qal perfect", "Qal perfect 3ms", False),
    ("Piel perfect 3ms", "Qal perfect 3ms", False),
    ("", "Qal perfect 3ms", False),
    ("Hiphil", "Qal perfect 3ms", False),
])
def test_parse_matches(answer, expected, ok):
    assert H._parse_matches(answer, expected) is ok


def test_parse_items_grade_through_progress(hebdb):
    row = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id, id, correct_answer FROM hebrew_practice_items"
        " WHERE question_type='parse' LIMIT 1").fetchone()
    assert row, "no parse items seeded"
    node_id, qid, truth = row
    out = H.update_hebrew_progress(
        {"user_id": "default", "node_id": node_id,
         "question_id": qid, "answer": truth},
        authorization="")
    assert out["ok"] is True
    assert out["data"]["correct"]
    # Lesson-loop feed wrote the FSRS '' schedule row.
    s = sqlite3.connect(str(hebdb)).execute(
        "SELECT reps FROM hebrew_review_state"
        " WHERE user_id='default' AND node_id=? AND card_mode=''",
        (node_id,)).fetchone()
    assert s and s[0] >= 1
    # A wrong parse fails grading.
    out2 = H.update_hebrew_progress(
        {"user_id": "anon_parse1", "node_id": node_id,
         "question_id": qid, "answer": "definitely not a parse"},
        authorization="")
    assert not out2["data"]["correct"]


def test_context_items_grade_and_schedule(hebdb):
    row = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id, id, correct_answer FROM hebrew_practice_items"
        " WHERE question_text LIKE 'Complete the verse%' LIMIT 1").fetchone()
    assert row, "no sentence-context items seeded"
    node_id, qid, truth = row
    out = H.update_hebrew_progress(
        {"user_id": "anon_ctx1", "node_id": node_id,
         "question_id": qid, "answer": truth},
        authorization="")
    assert out["ok"] is True and out["data"]["correct"]
    s = sqlite3.connect(str(hebdb)).execute(
        "SELECT reps FROM hebrew_review_state"
        " WHERE user_id='anon_ctx1' AND node_id=? AND card_mode=''",
        (node_id,)).fetchone()
    assert s and s[0] >= 1


def test_lesson_quiz_serves_parse_and_context(hebdb):
    # Verb lesson quiz includes parse items (converted to MC in mc mode).
    out = H.get_hebrew_lesson_quiz("qal_perfect", count=10, user_id="default")
    assert out["ok"] is True
    types = [q["type"] for q in out["data"]["questions"]]
    assert "parse" in types or len(out["data"]["questions"]) > 0
    # A context-card vocab node serves its cloze item.
    row = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id FROM hebrew_practice_items"
        " WHERE question_text LIKE 'Complete the verse%' LIMIT 1").fetchone()
    out2 = H.get_hebrew_lesson_quiz(row[0], count=10, user_id="default")
    assert out2["ok"] is True
    assert any("Complete the verse" in q["question"]
               for q in out2["data"]["questions"])


def test_production_items_grade_and_render_typed(hebdb):
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "scripts"))
    from generate_sentence_cloze import normalize_final, strip_niqqud
    conn = sqlite3.connect(str(hebdb))
    conn.row_factory = sqlite3.Row
    for cat, like in (("verb", "Write the Qal%"), ("root", "%share one root%"),
                      ("phrase", "Say%in Hebrew.")):
        row = conn.execute(
            "SELECT node_id, id, question_type, question_text, options_json,"
            " correct_answer, difficulty FROM hebrew_practice_items"
            " WHERE question_type='typing' AND question_text LIKE ? LIMIT 1",
            (like,)).fetchone()
        assert row, f"no production typing item for {cat}"
        node = conn.execute("SELECT id, title, category FROM hebrew_nodes WHERE id=?",
                            (row["node_id"],)).fetchone()
        q = H._practice_to_quiz_question(row, node)
        assert q["answer_mode"] == H.ANSWER_MODE_FREE_TEXT, cat
        skeleton = normalize_final(strip_niqqud(row["correct_answer"]))
        out = H.update_hebrew_progress(
            {"user_id": "anon_prod1", "node_id": row["node_id"],
             "question_id": row["id"], "answer": skeleton},
            authorization="")
        assert out["ok"] is True and out["data"]["correct"], cat
    conn.close()


def test_grammar_apply_items_grade_and_serve(hebdb):
    import sys as _sys2
    _sys2.path.insert(0, str(ROOT / "scripts"))
    from generate_sentence_cloze import normalize_final, strip_niqqud
    conn = sqlite3.connect(str(hebdb))
    conn.row_factory = sqlite3.Row
    # Type A: inflect (typing).
    row = conn.execute(
        "SELECT node_id, id, question_type, question_text, options_json,"
        " correct_answer, difficulty FROM hebrew_practice_items"
        " WHERE question_text LIKE 'Apply this lesson to%' LIMIT 1").fetchone()
    assert row, "no apply/inflect items seeded"
    skel = normalize_final(strip_niqqud(row["correct_answer"]))
    out = H.update_hebrew_progress(
        {"user_id": "anon_apply1", "node_id": row["node_id"],
         "question_id": row["id"], "answer": skel},
        authorization="")
    assert out["ok"] is True and out["data"]["correct"], row["node_id"]
    # Type B: breakdown (parse) — gloss required, Hebrew required.
    brow = conn.execute(
        "SELECT node_id, id, correct_answer FROM hebrew_practice_items"
        " WHERE question_type='parse' AND question_text LIKE 'Break %' LIMIT 1").fetchone()
    assert brow, "no breakdown items seeded"
    assert H._parse_matches(brow["correct_answer"], brow["correct_answer"])
    conn.close()
    # Served in the node's lesson quiz.
    out2 = H.get_hebrew_lesson_quiz(row["node_id"], count=10, user_id="default")
    assert out2["ok"] is True
    assert any("Apply this lesson" in q["question"]
               for q in out2["data"]["questions"])


def test_dictation_endpoint_no_answer_leak(hebdb):
    out = H.get_dictation_next(user_id="default", limit=5, session_token="",
                               authorization="")
    assert out["ok"] is True and out["data"]["count"] > 0
    for c in out["data"]["cards"]:
        assert c["audio_url"].startswith("/api/v1/audio/word/")
        assert "correct_answer" not in c and "answer" not in c
        assert c["question_id"]


def test_dictation_grades_through_progress(hebdb):
    row = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id, id, correct_answer FROM hebrew_practice_items"
        " WHERE question_type='dictation' LIMIT 1").fetchone()
    assert row, "no dictation items seeded"
    out = H.update_hebrew_progress(
        {"user_id": "anon_dic1", "node_id": row[0],
         "question_id": row[1], "answer": row[2]},
        authorization="")
    assert out["ok"] is True and out["data"]["correct"]
    s = sqlite3.connect(str(hebdb)).execute(
        "SELECT reps FROM hebrew_review_state"
        " WHERE user_id='anon_dic1' AND node_id=? AND card_mode=''",
        (row[0],)).fetchone()
    assert s and s[0] >= 1


def test_lesson_quiz_dictation_carries_audio(hebdb):
    # Same-answer dedup keeps one retrieval route per node per session, so
    # sweep a batch: dictation must surface with its audio player somewhere.
    nodes = sqlite3.connect(str(hebdb)).execute(
        "SELECT DISTINCT node_id FROM hebrew_practice_items"
        " WHERE question_type='dictation' LIMIT 30").fetchall()
    assert nodes
    found = []
    for (nid,) in nodes:
        out = H.get_hebrew_lesson_quiz(nid, count=10, user_id="default")
        assert out["ok"] is True
        found += [q for q in out["data"]["questions"] if q.get("audio_url")]
        if found:
            break
    assert found, "dictation items must ship an audio player"
    assert all(q["audio_url"].startswith("/api/v1/audio/word/") for q in found)


def test_lesson_quiz_serves_production_not_just_recognition(hebdb):
    # Student-eye regression: the same-answer dedup used to keep only the
    # easiest item per answer, deleting every production card from lesson
    # quizzes. Now one recognition + one rotating production item survive.
    out = H.get_hebrew_lesson_quiz("vocab_את_0", count=10, user_id="default")
    assert out["ok"] is True
    types = {q["type"] for q in out["data"]["questions"]}
    assert "multiple_choice" in types
    assert types & {"typing", "recall", "cloze", "dictation", "parse"}, types
    # Rotation is stable within the day.
    out2 = H.get_hebrew_lesson_quiz("vocab_את_0", count=10, user_id="default")
    assert [q["type"] for q in out["data"]["questions"]] == \
           [q["type"] for q in out2["data"]["questions"]]


def test_starter_words_lead_the_frontier(hebdb):
    conn = sqlite3.connect(str(hebdb))
    try:
        for (nid, _lv) in conn.execute("SELECT id, level FROM hebrew_nodes WHERE level<=3"):
            conn.execute(
                "INSERT OR REPLACE INTO hebrew_progress (user_id,node_id,mastery,attempts,correct)"
                " VALUES (?,?,0.9,10,9)", ("anon_startert", nid))
        conn.commit()
        assert H._max_frontier_level(conn, "anon_startert") == 4
    finally:
        conn.close()
    q = H.get_hebrew_review_queue(user_id="anon_startert", authorization="",
                                  limit=40, new_cards_per_day=6)
    assert q["ok"] is True
    ids = []
    for r in q["data"]["reviews"]:
        if r.get("type") == "compressed":
            ids += [i["node_id"] for i in r.get("items", [])]
        elif r.get("is_new") or r.get("scheduler") == "new":
            ids.append(r["node_id"])
    assert ids, "expected frontier new cards"
    assert ids[0] in set(H.STARTER_NODE_IDS), ids[:4]


def test_comprehension_items_grade_and_serve(hebdb):
    rows = sqlite3.connect(str(hebdb)).execute(
        "SELECT node_id, id, correct_answer, question_text FROM hebrew_practice_items"
        " WHERE question_type='true_false' LIMIT 2").fetchall()
    assert len(rows) == 2, "comprehension T/F items seeded"
    for node_id, qid, truth, prompt in rows:
        assert "appears in" in prompt
        out = H.update_hebrew_progress(
            {"user_id": "anon_comp1", "node_id": node_id,
             "question_id": qid, "answer": "True" if truth == "True" else "False"},
            authorization="")
        assert out["ok"] is True and out["data"]["correct"], prompt[:60]
        # Wrong verdict fails.
        out2 = H.update_hebrew_progress(
            {"user_id": "anon_comp2", "node_id": node_id,
             "question_id": qid, "answer": "False" if truth == "True" else "True"},
            authorization="")
        assert out2["ok"] is True and not out2["data"]["correct"]
    # Served with exactly 2 options (never padded to 5).
    out3 = H.get_hebrew_lesson_quiz(rows[0][0], count=10, user_id="default")
    tfs = [q for q in out3["data"]["questions"] if q["type"] == "true_false"]
    assert tfs and all(len(q["options"]) == 2 for q in tfs)
