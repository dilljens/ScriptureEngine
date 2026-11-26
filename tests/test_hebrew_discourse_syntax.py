"""First-class discourse_function / syntax_parse item types.

Guards the expert-audit promotion: aspect judgments and verse-syntax parses
are graded as choice-index, staged as recall (not recognition), and servable
from the lesson-quiz paths.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.hebrew import (
    HEBREW_CHOICE_TYPES,
    MC_ANSWERABLE_TYPES,
    _hebrew_quiz_answer_matches,
    build_kp_stages,
    practice_stage,
)


def test_new_types_are_choice_graded():
    assert "discourse_function" in HEBREW_CHOICE_TYPES
    assert "syntax_parse" in HEBREW_CHOICE_TYPES


def test_new_types_stage_as_recall():
    assert practice_stage("discourse_function") == "recall"
    assert practice_stage("syntax_parse") == "recall"
    assert practice_stage("multiple_choice") == "recognition"


def test_new_types_in_recall_stage_group():
    items = [
        {"id": 1, "question_type": "multiple_choice", "difficulty": 0.5},
        {"id": 2, "question_type": "discourse_function", "difficulty": 0.5},
        {"id": 3, "question_type": "syntax_parse", "difficulty": 0.5},
        {"id": 4, "question_type": "typing", "difficulty": 0.5},
    ]
    stages = {s["stage"]: [i["id"] for i in s["items"]] for s in build_kp_stages(items)}
    assert stages["recognition"] == [1]
    assert sorted(stages["recall"]) == [2, 3]
    assert stages["production"] == [4]


def test_new_types_convert_to_mc_lesson_quiz():
    # Default lesson quizzes run in mc mode: choice-format analytic items
    # must convert like classification, never hit the None-drop contract.
    assert "discourse_function" in MC_ANSWERABLE_TYPES
    assert "syntax_parse" in MC_ANSWERABLE_TYPES


def test_choice_index_grading_for_new_types():
    opts = ["Past — completed event in narrative", "Present", "Future"]
    assert _hebrew_quiz_answer_matches(
        "Past — completed event in narrative",
        "Past — completed event in narrative",
        "discourse_function", opts) is True
    assert _hebrew_quiz_answer_matches(
        "Present", "Past — completed event in narrative",
        "discourse_function", opts) is False
    assert _hebrew_quiz_answer_matches(0, "יִלָּחֵם", "syntax_parse",
                                       ["יִלָּחֵם", "יְהוָה", "אֵת"]) is True


def test_mc_distractor_pool_stable_across_shuffles():
    """Convertibility must not flip per process: the script filter runs before
    shuffle+truncate, so a bank with enough same-script distractors always
    converts (deploy-gate flake: _distractor_pool truncated first, then the
    script filter sometimes left <4 options and dropped the item)."""
    import random as _random
    import sqlite3 as _sqlite3

    from web.routes.hebrew import _to_mc_question

    conn = _sqlite3.connect(":memory:")
    conn.row_factory = _sqlite3.Row
    conn.execute("CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY, title TEXT, category TEXT)")
    conn.execute("CREATE TABLE hebrew_practice_items (id INTEGER PRIMARY KEY, node_id TEXT,"
                 " question_type TEXT, question_text TEXT, options_json TEXT,"
                 " correct_answer TEXT, difficulty REAL)")
    conn.execute("INSERT INTO hebrew_nodes VALUES ('target','T','verb')")
    heb = ["\u05d0\u05b8\u05de\u05b7\u05e8", "\u05d4\u05b8\u05dc\u05b7\u05da",
           "\u05e9\u05b8\u05de\u05b7\u05e2", "\u05e8\u05b8\u05d0\u05b8\u05d4",
           "\u05d9\u05b8\u05d3\u05b7\u05e2", "\u05d1\u05b8\u05e8\u05b8\u05d0"]
    nid = 1
    for h in heb:
        conn.execute("INSERT INTO hebrew_nodes VALUES (?,?,?)", (f"s{nid}", "S", "verb"))
        conn.execute("INSERT INTO hebrew_practice_items VALUES (?,?,?,?,?,?,?)",
                     (nid, f"s{nid}", "multiple_choice", "q", "[]", h, 0.5))
        nid += 1
    for i in range(20):
        conn.execute("INSERT INTO hebrew_nodes VALUES (?,?,?)", (f"s{nid}", "S", "verb"))
        conn.execute("INSERT INTO hebrew_practice_items VALUES (?,?,?,?,?,?,?)",
                     (nid, f"s{nid}", "multiple_choice", "q", "[]", f"gloss-{i}", 0.5))
        nid += 1
    node = {"id": "target", "title": "T", "category": "verb"}
    for seed in range(200):
        _random.seed(seed)
        q = {"question_id": 999, "type": "typing",
             "question": "Apply this lesson to 'he will fall'",
             "options": [], "category": "verb", "difficulty": 0.5,
             "_correct": "\u05d9\u05b4\u05e4\u05bb\u05dc"}
        out = _to_mc_question(conn, q, node)
        assert out is not None, f"seed {seed}: convertible item dropped"
        assert out["options"].count("\u05d9\u05b4\u05e4\u05bb\u05dc") == 1
