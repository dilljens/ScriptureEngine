"""Tests for progress-visibility tools: scripture_quiz_progress,
scripture_hebrew_progress, scripture_hebrew_placement, and the chat quiz
answer recording endpoint (POST /api/v1/quiz/record).

These tools let the chat LLM see a user's actual quiz results, Hebrew
learning progress, and placement — so the LLM can personalize teaching.
"""

import json
import sqlite3

import pytest

from lib.api import call_tool, TOOL_REGISTRY
from lib.db import get_db
from web.routes.chat import TOOL_DEFINITIONS, _tool_accepts_user_id, _normalize_user_id


@pytest.fixture(scope="module")
def seeded_quiz():
    """Seed quiz_progress + chat_quiz_answers rows for a test user."""
    conn = get_db()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS quiz_progress (
                user_id TEXT NOT NULL DEFAULT 'default',
                question_id INTEGER NOT NULL,
                correct INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0,
                last_seen TEXT,
                PRIMARY KEY (user_id, question_id))"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS chat_quiz_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL DEFAULT 'default',
                question TEXT NOT NULL,
                user_answer TEXT,
                correct_answer TEXT,
                correct INTEGER NOT NULL DEFAULT 0,
                source TEXT DEFAULT 'chat',
                created_at TEXT NOT NULL DEFAULT (datetime('now')))"""
        )
        conn.execute("DELETE FROM quiz_progress WHERE user_id='testuser'")
        conn.execute("DELETE FROM chat_quiz_answers WHERE user_id='testuser'")
        # assessment_items already exists (real schema) — insert a row with all
        # NOT NULL fields populated; ignore if the row is already there.
        conn.execute(
            """INSERT OR IGNORE INTO assessment_items
               (id, knowledge_item_id, question_type, question_text, options_json,
                correct_answer, layer, bloom_level)
               VALUES (9001, 1, 'true_false', 'Is atonement in Isaiah?', '[]',
                       'True', 'pshat', 'remember')"""
        )
        conn.execute(
            "INSERT OR REPLACE INTO quiz_progress (user_id, question_id, correct, attempts, last_seen) VALUES ('testuser', 9001, 1, 2, '2026-08-14')"
        )
        conn.execute(
            "INSERT INTO chat_quiz_answers (user_id, question, user_answer, correct_answer, correct, source) VALUES "
            "('testuser', 'What does hesed mean?', 'love', 'lovingkindness', 0, 'chat'), "
            "('testuser', 'Which is the divine name?', 'Elohim', 'YHWH', 0, 'chat')"
        )
        conn.commit()
    finally:
        conn.close()


def test_tools_registered():
    for name in (
        "scripture_quiz_progress",
        "scripture_hebrew_progress",
        "scripture_hebrew_placement",
        "scripture_diagnostic_start",
        "scripture_diagnostic_answer",
        "scripture_diagnostic_report",
    ):
        assert name in TOOL_REGISTRY, f"{name} missing from registry"


def test_tools_in_chat_definitions():
    names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    for name in (
        "scripture_quiz_progress",
        "scripture_hebrew_progress",
        "scripture_hebrew_placement",
        "scripture_hebrew_lessons",
        "scripture_hebrew_lesson",
        "scripture_hebrew_quiz",
        "scripture_assess_start",
        "scripture_assess_answer",
        "scripture_assess_progress",
        "scripture_diagnostic_start",
        "scripture_diagnostic_answer",
        "scripture_diagnostic_report",
    ):
        assert name in names, f"{name} missing from chat TOOL_DEFINITIONS"


def test_user_tools_flag():
    assert _tool_accepts_user_id("scripture_hebrew_progress")
    assert _tool_accepts_user_id("scripture_quiz_progress")
    assert _tool_accepts_user_id("scripture_hebrew_placement")
    assert not _tool_accepts_user_id("scripture_verse")
    assert not _tool_accepts_user_id("scripture_search")


def test_normalize_user_id():
    assert _normalize_user_id("") == "default"
    assert _normalize_user_id("anonymous") == "default"
    assert _normalize_user_id("default") == "default"
    assert _normalize_user_id("alice-123") == "alice-123"


def test_quiz_progress_tool(seeded_quiz):
    conn = get_db()
    try:
        result = call_tool("scripture_quiz_progress", conn, user_id="testuser")
        assert result.get("ok") is True
        assert result["user_id"] == "testuser"
        assert result["total_questions_answered"] == 1  # quiz_progress row
        assert result["chat_quiz_count"] == 2  # chat answers
        assert isinstance(result["per_layer_mastery"], list)
        # recent answers surfaced
        recent = result.get("recent_answers") or []
        assert any(r["question_id"] == 9001 for r in recent)
    finally:
        conn.close()


def test_quiz_progress_empty_user():
    conn = get_db()
    try:
        result = call_tool("scripture_quiz_progress", conn, user_id="nobody-xyz")
        assert result.get("ok") is True
        assert result["total_questions_answered"] == 0
    finally:
        conn.close()


def test_hebrew_progress_tool_real_db():
    """Hebrew progress reads memorize.db — smoke test against whatever DB is present."""
    conn = get_db()
    try:
        result = call_tool("scripture_hebrew_progress", conn, user_id="default")
        assert result.get("ok") is True
        # Never crashes; has_progress is a bool either way
        assert "has_progress" in result
        if result["has_progress"]:
            assert isinstance(result["by_category"], list)
            assert isinstance(result["due_reviews"], dict)
            assert "gamification" in result
            assert "placement" in result
    finally:
        conn.close()


def test_hebrew_placement_tool_real_db():
    conn = get_db()
    try:
        result = call_tool("scripture_hebrew_placement", conn, user_id="default")
        assert result.get("ok") is True
        assert "has_placement" in result
        if result["has_placement"]:
            assert isinstance(result["skills"], list)
            assert "summary" in result
    finally:
        conn.close()


def test_record_chat_quiz_endpoint(client):
    """POST /api/v1/quiz/record stores answers readable by scripture_quiz_progress."""
    conn = get_db()
    try:
        conn.execute("DELETE FROM chat_quiz_answers WHERE user_id='ep-test'")
        conn.commit()
    finally:
        conn.close()
    resp = client.post(
        "/api/v1/quiz/record",
        json={
            "user_id": "ep-test",
            "answers": [
                {"question": "Test Q1", "user_answer": "A", "correct_answer": "B", "correct": False},
                {"question": "Test Q2", "user_answer": "B", "correct_answer": "B", "correct": True},
            ],
            "source": "chat",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["recorded"] == 2

    conn = get_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM chat_quiz_answers WHERE user_id='ep-test'"
        ).fetchone()[0]
        assert count == 2
        result = call_tool("scripture_quiz_progress", conn, user_id="ep-test")
        assert result["chat_quiz_count"] == 2
    finally:
        conn.close()
