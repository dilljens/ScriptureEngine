import sqlite3

import pytest

from lib.api.conversations import add_message, extract_verse_refs


@pytest.mark.parametrize(("text", "expected"), [
    ("Leviticus 14:10,23", ["lev.14.10", "lev.14.23"]),
    ("lev.14.10,23", ["lev.14.10", "lev.14.23"]),
    ("Leviticus 14:10-12", ["lev.14.10", "lev.14.11", "lev.14.12"]),
    ("lev.14.10–12", ["lev.14.10", "lev.14.11", "lev.14.12"]),
    ("1 Nephi 3: 1 - 7", [f"1ne.3.{verse}" for verse in range(1, 8)]),
    ("1 John 1:1", ["1john.1.1"]),
    ("2 John 1:2", ["2john.1.2"]),
    ("3 John 1:3", ["3john.1.3"]),
    ("Isaiah 53:5, 11", ["isa.53.5", "isa.53.11"]),
    ("Isaiah 52:1-2, 54:2", ["isa.52.1", "isa.52.2", "isa.54.2"]),
    ("Exodus 33:22–34:6", ["exo.33.22", "exo.34.6"]),
])
def test_extracts_every_verse_in_ranges_and_lists(text, expected):
    refs = extract_verse_refs(text)
    assert [ref["verse_id"] for ref in refs] == expected


def test_duplicate_refs_are_returned_once():
    refs = extract_verse_refs("lev.14.10,23 and Leviticus 14:10")
    assert [ref["verse_id"] for ref in refs] == ["lev.14.10", "lev.14.23"]


def test_unreasonably_large_reference_numbers_are_ignored():
    refs = extract_verse_refs(f"Genesis 1:1-{'9' * 4301}")
    assert refs == []
    assert extract_verse_refs(f"gen.{'9' * 4301}.1") == []
    assert extract_verse_refs("gen.10001.1") == []


def test_add_message_persists_all_expanded_refs():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE verses (id TEXT PRIMARY KEY);
        CREATE TABLE conversation_sessions (
            id TEXT PRIMARY KEY, message_count INTEGER DEFAULT 0, updated_at TEXT
        );
        CREATE TABLE conversation_messages (
            id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT,
            metadata_json TEXT, timestamp TEXT
        );
        CREATE TABLE conversation_refs (
            id INTEGER PRIMARY KEY, session_id TEXT, message_id INTEGER,
            verse_id TEXT, context TEXT, confidence REAL,
            UNIQUE(message_id, verse_id)
        );
        CREATE TABLE connections (source_verse TEXT, target_verse TEXT);
        CREATE TABLE conversation_connections (
            id INTEGER PRIMARY KEY, session_id TEXT, source_verse TEXT,
            target_verse TEXT, relationship TEXT, connection_type TEXT,
            existing_connection_id INTEGER, confidence REAL, description TEXT,
            context_message TEXT
        );
        INSERT INTO conversation_sessions (id, message_count) VALUES ('session', 0);
        INSERT INTO verses (id) VALUES ('lev.14.10'), ('lev.14.11'), ('lev.14.12');
    """)
    try:
        add_message(conn, "session", "assistant", "Leviticus 14:10-12")
        saved = conn.execute(
            "SELECT verse_id FROM conversation_refs ORDER BY verse_id"
        ).fetchall()
        assert [row["verse_id"] for row in saved] == [
            "lev.14.10", "lev.14.11", "lev.14.12",
        ]
    finally:
        conn.close()
