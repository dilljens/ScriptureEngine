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
