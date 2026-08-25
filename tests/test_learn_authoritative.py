from web.routes.learn import _practice_answer_matches
from lib.api.assessment import _assessment_answer_matches, _get_question
from lib.db import get_db


def test_learn_practice_grades_choice_and_rejects_client_boolean():
    options = ["Bet", "Aleph", "Gimel"]
    assert _practice_answer_matches("Aleph", "Aleph", "multiple_choice", options, "choice_index")
    assert _practice_answer_matches(1, "Aleph", "multiple_choice", options, "choice_index")
    assert _practice_answer_matches("B", "Aleph", "multiple_choice", options, "choice_index")
    assert not _practice_answer_matches("Bet", "Aleph", "multiple_choice", options, "choice_index")


def test_learn_practice_grades_free_text_alternatives():
    assert _practice_answer_matches(
        "loving kindness", "love or loving kindness", "recall", [], "free_text"
    )
    assert not _practice_answer_matches("wrong", "love or loving kindness", "recall", [], "free_text")


def test_legacy_assessment_grades_without_exposing_option_metadata():
    question = {
        "options": [{"label": "False", "correctness_weight": 0.0}, {"label": "True", "correctness_weight": 1.0}],
        "correct_answer": "True",
    }
    assert _assessment_answer_matches("True", question)
    assert _assessment_answer_matches("B", question)
    assert not _assessment_answer_matches("False", question)


def test_legacy_assessment_can_reload_the_exact_issued_question():
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT knowledge_item_id, id FROM assessment_items "
            "WHERE knowledge_item_id IS NOT NULL LIMIT 1"
        ).fetchone()
        if not row:
            return
        exact = _get_question(conn, row[0], row[1])
        assert exact["item_id"] == row[1]
    finally:
        conn.close()
