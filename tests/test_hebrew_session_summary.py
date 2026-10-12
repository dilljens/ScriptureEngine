"""Tests for web.lib.hebrew_session_summary. Uses :memory: DBs only."""

import json
import sqlite3

from web.lib.hebrew_session_summary import (
    summarize_hebrew_session,
    write_session_summary,
)

USER = "test-user"


def _bare_conn():
    # No tables at all -- summarizer must not crash.
    return sqlite3.connect(":memory:")


def _full_conn():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE hebrew_nodes (
            id TEXT PRIMARY KEY, title TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 4,
            category TEXT NOT NULL DEFAULT 'word', description TEXT DEFAULT ''
        );
        CREATE TABLE hebrew_progress (
            user_id TEXT NOT NULL DEFAULT 'default', node_id TEXT NOT NULL,
            mastery REAL DEFAULT 0.0, attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0, last_practiced TEXT,
            source TEXT DEFAULT 'practice',
            PRIMARY KEY (user_id, node_id)
        );
        CREATE TABLE hebrew_review_state (
            user_id TEXT NOT NULL, node_id TEXT NOT NULL, card_mode TEXT NOT NULL DEFAULT '',
            stability REAL NOT NULL DEFAULT 0.0, difficulty REAL NOT NULL DEFAULT 5.0,
            due TEXT NOT NULL DEFAULT '2000-01-01 00:00:00',
            last_review TEXT, last_rating INTEGER, reps INTEGER NOT NULL DEFAULT 0,
            lapses INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, node_id, card_mode)
        );
        CREATE TABLE hebrew_attempt_events (
            id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, node_id TEXT NOT NULL,
            question_id TEXT, mode TEXT DEFAULT 'hebrew', raw_response TEXT DEFAULT '',
            correct INTEGER NOT NULL, hints INTEGER DEFAULT 0,
            content_version TEXT DEFAULT '', evaluator_version TEXT DEFAULT '',
            event_hash TEXT NOT NULL, created_at TEXT DEFAULT '2000-01-01 00:00:00'
        );
        CREATE TABLE tutor_memory (
            user_id TEXT NOT NULL DEFAULT 'default', key TEXT NOT NULL,
            value TEXT NOT NULL DEFAULT '', source TEXT NOT NULL DEFAULT 'tutor',
            evidence TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, key)
        );
        CREATE TABLE tutor_session_summary (
            session_key TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
            summary TEXT NOT NULL DEFAULT '', turn_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        """
    )
    return conn


def test_empty_db_all_defaults_no_crash():
    conn = _bare_conn()
    s = summarize_hebrew_session(conn, USER)
    assert s["user_id"] == USER
    assert s["generated_at"]
    assert set(s["categories"]) == {"grammar", "verb", "syntax", "root", "word"}
    for stats in s["categories"].values():
        assert stats == {"avg_mastery": 0.0, "practiced_count": 0, "mastered_count": 0}
    assert s["weakest_nodes"] == []
    assert s["due_by_mode"] == {}
    assert s["new_today"] == 0
    assert s["confusion_hotspots"] == []
    json.dumps(s)  # must be JSON-serializable
    conn.close()


def test_weak_node_appears_with_summed_lapses():
    conn = _full_conn()
    conn.executemany(
        "INSERT INTO hebrew_nodes (id, title, category) VALUES (?, ?, ?)",
        [("n1", "Qal Verb", "verb"), ("n2", "Noun", "grammar")],
    )
    conn.executemany(
        "INSERT INTO hebrew_progress (user_id, node_id, mastery, attempts) VALUES (?, ?, ?, ?)",
        [(USER, "n1", 0.2, 5), (USER, "n2", 0.9, 4)],
    )
    conn.executemany(
        "INSERT INTO hebrew_review_state (user_id, node_id, card_mode, lapses) VALUES (?, ?, ?, ?)",
        [(USER, "n1", "recall", 2), (USER, "n1", "recognition", 3), (USER, "n2", "recall", 0)],
    )
    conn.commit()
    s = summarize_hebrew_session(conn, USER)
    assert s["weakest_nodes"][0]["node_id"] == "n1"
    assert s["weakest_nodes"][0]["lapses"] == 5
    assert s["weakest_nodes"][0]["title"] == "Qal Verb"
    assert s["categories"]["verb"]["practiced_count"] == 1
    assert s["categories"]["verb"]["mastered_count"] == 0
    assert s["categories"]["grammar"]["mastered_count"] == 1
    conn.close()


def test_write_then_reread_returns_same_summary():
    conn = _full_conn()
    s = summarize_hebrew_session(conn, USER)
    res = write_session_summary(conn, USER, s)
    assert res == {"ok": True, "memory_key": "hebrew_knowledge_state"}
    row = conn.execute(
        "SELECT value, source FROM tutor_memory WHERE user_id = ? AND key = ?",
        (USER, "hebrew_knowledge_state"),
    ).fetchone()
    assert row is not None
    assert json.loads(row[0]) == json.loads(json.dumps(s))
    assert row[1] == "hebrew_session_summary"
    sess = conn.execute("SELECT summary FROM tutor_session_summary").fetchone()
    assert json.loads(sess[0]) == json.loads(json.dumps(s))
    conn.close()


def test_missing_attempt_events_table_does_not_crash():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY, title TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 4, category TEXT NOT NULL DEFAULT 'word',
            description TEXT DEFAULT '');
        CREATE TABLE hebrew_progress (user_id TEXT NOT NULL DEFAULT 'default',
            node_id TEXT NOT NULL, mastery REAL DEFAULT 0.0, attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0, last_practiced TEXT,
            source TEXT DEFAULT 'practice', PRIMARY KEY (user_id, node_id));
        CREATE TABLE hebrew_review_state (user_id TEXT NOT NULL, node_id TEXT NOT NULL,
            card_mode TEXT NOT NULL DEFAULT '', stability REAL NOT NULL DEFAULT 0.0,
            difficulty REAL NOT NULL DEFAULT 5.0,
            due TEXT NOT NULL DEFAULT '2000-01-01 00:00:00',
            last_review TEXT, last_rating INTEGER, reps INTEGER NOT NULL DEFAULT 0,
            lapses INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, node_id, card_mode));
        """
    )
    conn.execute(
        "INSERT INTO hebrew_progress (user_id, node_id, mastery, attempts) VALUES (?, ?, ?, ?)",
        (USER, "n1", 0.1, 3),
    )
    conn.commit()
    s = summarize_hebrew_session(conn, USER)
    assert s["confusion_hotspots"] == []
    json.dumps(s)
    conn.close()
