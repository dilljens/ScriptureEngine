import json
import sqlite3

from scripts.validate_hebrew_learning_content import validate


def test_validator_accepts_minimal_valid_curriculum(tmp_path):
    db = tmp_path / "hebrew.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY);
        CREATE TABLE hebrew_lessons (
            node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
            content_json TEXT NOT NULL
        );
        CREATE TABLE hebrew_practice_items (
            id INTEGER PRIMARY KEY,
            node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
            question_type TEXT NOT NULL,
            question_text TEXT NOT NULL,
            options_json TEXT,
            correct_answer TEXT NOT NULL,
            explanation TEXT DEFAULT ''
        );
    """)
    conn.execute("INSERT INTO hebrew_nodes VALUES ('aleph')")
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES (?, ?)",
        ("aleph", json.dumps({"title": "Aleph", "verse_ref": "gen.1.1"})),
    )
    conn.execute(
        "INSERT INTO hebrew_practice_items VALUES (1,?,?,?,?,?,NULL)",
        ("aleph", "multiple_choice", "Which is Aleph?", '["א","ב"]', "א"),
    )
    conn.commit()
    conn.close()

    assert validate(db) == []


def test_validator_reports_unsafe_content(tmp_path):
    db = tmp_path / "hebrew.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY);
        CREATE TABLE hebrew_lessons (node_id TEXT PRIMARY KEY, content_json TEXT NOT NULL);
        CREATE TABLE hebrew_practice_items (
            id INTEGER PRIMARY KEY, node_id TEXT, question_type TEXT,
            question_text TEXT, options_json TEXT, correct_answer TEXT, explanation TEXT DEFAULT ''
        );
        INSERT INTO hebrew_nodes VALUES ('samekh');
    """)
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES (?, ?)",
        ("samekh", json.dumps({"explanation": "a dot in the center", "verse_ref": "dss.1.1"})),
    )
    conn.execute(
        "INSERT INTO hebrew_practice_items VALUES (1,'samekh','multiple_choice',?,?,?,NULL)",
        ("Is 'Samekh' a consonant in Biblical Hebrew?", '["True","False"]', "True"),
    )
    conn.commit()
    conn.close()

    errors = validate(db)
    assert any("Samekh has no dot" in error for error in errors)
    assert any("non-OT" in error for error in errors)
    assert any("tautological" in error for error in errors)


def test_validator_rejects_true_false_and_answer_in_question(tmp_path):
    """True/false questions are banned; answers must not be revealed in the Q."""
    db = tmp_path / "hebrew.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY);
        CREATE TABLE hebrew_lessons (node_id TEXT PRIMARY KEY, content_json TEXT NOT NULL);
        CREATE TABLE hebrew_practice_items (
            id INTEGER PRIMARY KEY, node_id TEXT, question_type TEXT,
            question_text TEXT, options_json TEXT, correct_answer TEXT, explanation TEXT DEFAULT ''
        );
        INSERT INTO hebrew_nodes VALUES ('aleph'), ('bet');
    """)
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES (?, ?)",
        ("aleph", json.dumps({"explanation": "ok"})),
    )
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES (?, ?)",
        ("bet", json.dumps({"explanation": "ok"})),
    )
    conn.execute(
        "INSERT INTO hebrew_practice_items VALUES "
        "(1,'aleph','true_false','Aleph is a letter.','[\"True\",\"False\"]','True',NULL),"
        "(2,'aleph','multiple_choice','What is the name of this Hebrew letter: Aleph?','[\"Aleph\",\"Bet\"]','Aleph',NULL),"
        "(3,'bet','multiple_choice','Which is Bet?','[\"א\",\"ב\"]','ב',NULL);",
    )
    conn.commit()
    conn.close()

    errors = validate(db)
    assert any("true/false questions are not allowed" in error for error in errors)
    assert any("answer is given away in the question" in error for error in errors)
    # item 3 is clean (answer not in question text)
    assert not any("practice 3 " in error for error in errors)


def test_repair_quarantines_and_removes_unsafe_records(tmp_path):
    from scripts.repair_hebrew_learning_content import repair

    db = tmp_path / "hebrew.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY);
        CREATE TABLE hebrew_lessons (
            node_id TEXT PRIMARY KEY, content_json TEXT NOT NULL,
            version INTEGER DEFAULT 1, updated_at TEXT
        );
        CREATE TABLE hebrew_practice_items (
            id INTEGER PRIMARY KEY, node_id TEXT, question_type TEXT,
            question_text TEXT, options_json TEXT, correct_answer TEXT, explanation TEXT DEFAULT ''
        );
        CREATE TABLE hebrew_edges (source_id TEXT, target_id TEXT);
        INSERT INTO hebrew_nodes VALUES ('aleph');
        INSERT INTO hebrew_practice_items VALUES
            (1,'aleph','true_false','Is ''Aleph'' a consonant in Biblical Hebrew?','["True","False"]','True',NULL),
            (2,'aleph','multiple_choice','Choose','["—","א"]','א',NULL);
        INSERT INTO hebrew_edges VALUES ('missing','aleph');
    """)
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES (?,?,1,NULL)",
        ("aleph", json.dumps({"verse_example": "dss.1.1", "verse_hebrew": "א"})),
    )
    conn.commit()
    conn.close()

    counts = repair(db)
    assert counts == {
        "examples_quarantined": 1,
        "practice_removed": 2,
        "practice_duplicates_removed": 0,
        "edges_removed": 1,
        "graph_edges_reoriented": 0,
    }
    conn = sqlite3.connect(db)
    lesson = json.loads(conn.execute("SELECT content_json FROM hebrew_lessons").fetchone()[0])
    assert lesson["example_status"] == "quarantined_non_ot"
    assert "verse_example" not in lesson
    assert conn.execute("SELECT COUNT(*) FROM hebrew_practice_items").fetchone()[0] == 0
    conn.close()
