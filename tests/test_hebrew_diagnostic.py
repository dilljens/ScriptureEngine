from web.routes.hebrew import _diagnostic_answer_matches


def test_diagnostic_answer_matching_handles_pointed_hebrew():
    assert _diagnostic_answer_matches("בְּרֵאשִׁית", "בְּרֵאשִׁ֖ית")
    assert not _diagnostic_answer_matches("ברא", "בְּרֵאשִׁית")
    assert not _diagnostic_answer_matches("שׂ", "שׁ")
    assert not _diagnostic_answer_matches("ב", "בּ")
    assert _diagnostic_answer_matches("ָ", "ָ")


def test_diagnostic_answer_matching_rejects_empty_answers():
    assert not _diagnostic_answer_matches("", "א")


# Every type the adaptive placement can issue must be answerable in the UI:
# either it carries options (buttons render) or the frontend treats it as
# text input. A type with neither soft-locks the test (no way to submit).
# Keep in sync with TEXT_INPUT_TYPES in HebrewDiagnostic.jsx and the qtypes
# brackets in _placement_pick_question (web/routes/hebrew.py).
PLACEMENT_QTYPES = {"multiple_choice", "letter_recognition", "classification",
                    "transliteration", "cloze", "recall",
                    "typing", "contrast", "parse"}
TEXT_INPUT_QTYPES = {"transliteration", "cloze", "recall", "typing",
                     "letter_name", "parse", "dictation", "contrast"}


def _placement_qtypes_in_code():
    import re
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    src = open(root / "web" / "routes" / "hebrew.py", encoding="utf-8").read()
    found = set()
    pat = re.compile(r"qtypes = \(([^)]+)\)")
    word = re.compile(r"'([a-z_]+)'")
    for m in pat.finditer(src):
        found |= set(word.findall(m.group(1)))
    return found


def test_placement_qtypes_all_answerable():
    import sqlite3
    from pathlib import Path
    assert _placement_qtypes_in_code() <= PLACEMENT_QTYPES, (
        "new placement type not reviewed for answerability")
    conn = sqlite3.connect(str(Path(__file__).resolve().parent.parent
                               / "data" / "memorize.db"))
    try:
        rows = conn.execute(
            "SELECT DISTINCT question_type FROM hebrew_practice_items"
            " WHERE question_type IN (%s)" % ",".join("?" * len(PLACEMENT_QTYPES)),
            tuple(sorted(PLACEMENT_QTYPES))).fetchall()
    finally:
        conn.close()
    # Types actually served must either always carry options or be text-input.
    conn2 = sqlite3.connect(str(Path(__file__).resolve().parent.parent
                                / "data" / "memorize.db"))
    try:
        for (qt,) in rows:
            if qt in TEXT_INPUT_QTYPES:
                continue
            n_no_opts = conn2.execute(
                "SELECT COUNT(*) FROM hebrew_practice_items WHERE question_type=? "
                "AND (options_json IS NULL OR options_json='[]' OR options_json='')",
                (qt,)).fetchone()[0]
            assert n_no_opts == 0, f"{qt} served without options and not text-input"
    finally:
        conn2.close()


def _adaptive_session_with_parse(tmp_path, monkeypatch):
    """Isolated DB + placement session with a parse question issued."""
    import json
    import shutil
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
    from web.routes import hebrew as H
    src = _P(__file__).resolve().parent.parent / "data" / "memorize.db"
    iso = tmp_path / "memorize.db"
    shutil.copy2(src, iso)
    monkeypatch.setattr(H, "MEM_DB", iso)
    import sqlite3
    conn = sqlite3.connect(str(iso))
    H._placement_session_table(conn)
    row = conn.execute(
        "SELECT id, node_id, correct_answer FROM hebrew_practice_items"
        " WHERE question_type='parse' LIMIT 1").fetchone()
    assert row, "no parse items seeded"
    qid, nid, truth = row
    state = H._placement_initial_state()
    conn.execute(
        "INSERT INTO hebrew_placement_sessions (session_id, user_id, skill_idx,"
        " state_json, expires_at, issued_question_id, issued_node_id, issued_nonce)"
        " VALUES (?,?,?,?,datetime('now','+1 hour'),?,?,?)",
        ("sess-parse-1", "default", 0, json.dumps(state), qid, nid, "n1"))
    conn.commit()
    conn.close()
    return H, "sess-parse-1", qid, nid, truth


def test_adaptive_grades_parse_by_keywords(tmp_path, monkeypatch):
    H, sess, qid, nid, truth = _adaptive_session_with_parse(tmp_path, monkeypatch)
    # Case/spacing-insensitive keyword answer counts.
    out = H.answer_adaptive_diagnostic(
        {"session_id": sess, "question_id": qid, "node_id": nid,
         "question_nonce": "n1", "answer": truth.lower()},
        authorization="")
    assert out["ok"] is True and out["data"]["last_correct"] is True
    assert out["data"]["correct_answer"] == truth


def test_adaptive_rejects_wrong_parse(tmp_path, monkeypatch):
    H, sess, qid, nid, truth = _adaptive_session_with_parse(tmp_path, monkeypatch)
    out = H.answer_adaptive_diagnostic(
        {"session_id": sess, "question_id": qid, "node_id": nid,
         "question_nonce": "n1", "answer": "definitely not a parse"},
        authorization="")
    assert out["ok"] is True and out["data"]["last_correct"] is False
    # ...but the correction travels with the verdict (diagnostic feedback gap).
    assert out["data"]["correct_answer"] == truth
