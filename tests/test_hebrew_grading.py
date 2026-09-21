"""Hebrew answer grading: sofit-insensitive, niqqud-insensitive matching."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.hebrew import (
    _grade_verb_answer,
    _hebrew_free_text_matches,
    _normalize_hebrew_answer,
)


def test_sofit_folding():
    # Final (sofit) vs non-final forms must match both directions.
    assert _normalize_hebrew_answer("שלום") == _normalize_hebrew_answer("שלומ")
    assert _normalize_hebrew_answer("מלך") == _normalize_hebrew_answer("מלכ")
    assert _normalize_hebrew_answer("אף") == _normalize_hebrew_answer("אפ")
    assert _normalize_hebrew_answer("עץ") == _normalize_hebrew_answer("עצ")
    assert _normalize_hebrew_answer("בן") == _normalize_hebrew_answer("בנ")


def test_niqqud_stripped():
    # Vowel points, dagesh, shin/sin dots must not fail grading.
    assert _normalize_hebrew_answer("מֶלֶךְ") == _normalize_hebrew_answer("מלך")
    assert _normalize_hebrew_answer("שָׁלוֹם") == _normalize_hebrew_answer("שלום")


def test_distinct_words_stay_distinct():
    assert _normalize_hebrew_answer("שלום") != _normalize_hebrew_answer("מלך")
    assert _normalize_hebrew_answer("אב") != _normalize_hebrew_answer("אם")
    assert _normalize_hebrew_answer("") == ""
    assert _normalize_hebrew_answer(None) == ""


def test_free_text_matches_sofit():
    assert _hebrew_free_text_matches("שלומ", "שלום") is True
    assert _hebrew_free_text_matches("מלך", "מלכ") is True
    assert _hebrew_free_text_matches("חתול", "כלב") is False
    assert _hebrew_free_text_matches("", "שלום") is False


def test_verb_grader_sofit():
    drill = {"correct": "שלום", "options": '["שלום", "מלך"]'}
    assert _grade_verb_answer(drill, "שלומ") is True
    assert _grade_verb_answer(drill, "מלך") is False
    assert _grade_verb_answer(drill, "A") is True
    assert _grade_verb_answer({"correct": ""}, "שלום") is False
