"""Resolution layers for Hebrew flashcards: exact → folded → affix → lemma.

Every Top-Vocab surface must resolve to a lesson node so ratings persist
into hebrew_progress / hebrew_review_state (the schedule). Uses a minimal
in-memory lessons table — no fixture DB needed.
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.hebrew import _HEBREW_NODE_MAP, resolve_hebrew_node


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE hebrew_nodes (id TEXT PRIMARY KEY)")
    conn.execute("CREATE TABLE hebrew_lessons (node_id TEXT, content_json TEXT)")
    conn.execute("INSERT INTO hebrew_nodes VALUES ('n1'), ('n2')")
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES (?, ?), (?, ?)",
        (
            "n1",
            json.dumps({"hebrew": "שָׁמַע", "glyph": "שמע", "lemma": "8085"}),
            "n2",
            json.dumps({"hebrew": "רָאָה", "lemma": "7200", "lemma_key": "7200"}),
        ),
    )
    _HEBREW_NODE_MAP.update(count=-1, map={}, folded={})
    return conn


def test_resolve_exact_and_folded():
    conn = _conn()
    assert resolve_hebrew_node(conn, "שמע") == "n1"  # exact glyph hit
    assert resolve_hebrew_node(conn, "שָׁמַע") == "n1"  # exact hebrew hit
    assert resolve_hebrew_node(conn, "ראה") == "n2"  # folded hit (רָאָה)


def test_resolve_affix_strip():
    conn = _conn()
    assert resolve_hebrew_node(conn, "שמעתי") == "n1"  # -תי suffix
    assert resolve_hebrew_node(conn, "וישמע") == "n1"  # narrative ו- + י- prefix
    assert resolve_hebrew_node(conn, "תשמע") == "n1"  # 2nd-person ת- prefix


def test_resolve_affix_prefix_only():
    conn = _conn()
    assert resolve_hebrew_node(conn, "ושמע") == "n1"  # ו- prefix, no suffix


def test_resolve_lemma_fallback():
    conn = _conn()
    # ראיתי folds to nothing in the map and no affix strip reaches ראה,
    # so the Strong's lemma carries it.
    assert resolve_hebrew_node(conn, "ראיתי") == ""
    assert resolve_hebrew_node(conn, "ראיתי", "7200") == "n2"
    assert resolve_hebrew_node(conn, "ראיתי", "9999") == ""


def test_resolve_empty_and_unknown():
    conn = _conn()
    assert resolve_hebrew_node(conn, "") == ""
    assert resolve_hebrew_node(conn, "זזזזז") == ""
