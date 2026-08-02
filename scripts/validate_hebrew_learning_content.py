#!/usr/bin/env python3
"""Validate Hebrew lessons, practice items, graph integrity, and OT examples."""

import argparse
import json
import re
import sqlite3
from pathlib import Path

OT_BOOKS = {
    "gen", "exo", "lev", "num", "deu", "josh", "judg", "ruth", "1sam", "2sam",
    "1kgs", "2kgs", "1chr", "2chr", "ezra", "neh", "esth", "job", "psa", "prov",
    "eccl", "song", "isa", "jer", "lam", "ezek", "dan", "hos", "joel", "amos",
    "obad", "jonah", "mic", "nah", "hab", "zeph", "hag", "zech", "mal",
}

FORBIDDEN_CLAIMS = {
    "a dot in the center": "Samekh has no dot",
    "בְּ·רֵ·א·שִׁית": "Bereshit has three syllables in the standard reading",
    "Always preceded by Lamed": "the infinitive construct can take several prepositions",
    "changes its tense": "wayyiqtol/weqatal are discourse forms, not tense reversal",
    "about 50% of all verb uses": "unsupported frequency claim",
    "סֵפֶר (book/scroll) also derives from this root": "sefer belongs to root ספר",
}

ASSESSED_TYPES = {"multiple_choice", "true_false", "classification", "contrast"}

# True/false questions are banned outright (Math Academy Way review decision).
NO_TRUE_FALSE = True


def _norm_answer_in_question(text: str) -> str:
    """Lowercase, strip punctuation/quotes, collapse whitespace for a fuzzy
    'answer appears in the question' check."""
    s = re.sub(r"[\u05be\u05f3\u2018\u2019\u201c\u201d\"'\.,;:!?()\[\]{}]", " ", text.lower())
    return re.sub(r"\s+", " ", s).strip()


def validate(db_path: Path) -> list[str]:
    errors: list[str] = []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    scripture_path = Path("data/processed/scripture.db")
    scripture = sqlite3.connect(f"file:{scripture_path}?mode=ro", uri=True) if scripture_path.exists() else None

    for table, rowid, parent, fkid in conn.execute("PRAGMA foreign_key_check"):
        errors.append(f"foreign key: {table} row {rowid} parent {parent} constraint {fkid}")

    node_count = conn.execute("SELECT COUNT(*) FROM hebrew_nodes").fetchone()[0]
    lesson_count = conn.execute("SELECT COUNT(*) FROM hebrew_lessons").fetchone()[0]
    if lesson_count != node_count:
        errors.append(f"coverage: {node_count} nodes but {lesson_count} lessons")

    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "hebrew_vocabulary_alignment" in tables:
        try:
            from scripts.align_hebrew_vocabulary import LEMMA_OVERRIDES
        except ModuleNotFoundError:
            from align_hebrew_vocabulary import LEMMA_OVERRIDES
        vocabulary_count = conn.execute(
            "SELECT COUNT(*) FROM hebrew_nodes WHERE id GLOB 'vocab_*'"
        ).fetchone()[0]
        alignments = conn.execute("SELECT * FROM hebrew_vocabulary_alignment").fetchall()
        if len(alignments) != vocabulary_count:
            errors.append(f"vocabulary alignment: {len(alignments)}/{vocabulary_count} lessons aligned")
        lesson_glosses = {
            row["node_id"]: json.loads(row["content_json"]).get("gloss", "")
            for row in conn.execute("SELECT node_id,content_json FROM hebrew_lessons")
        }
        lesson_hebrews = {
            row["node_id"]: json.loads(row["content_json"]).get("hebrew", "")
            for row in conn.execute("SELECT node_id,content_json FROM hebrew_lessons")
        }
        if scripture:
            for alignment in alignments:
                expected = LEMMA_OVERRIDES.get(alignment["lemma_base"])
                if expected:
                    if lesson_glosses.get(alignment["node_id"]) != expected["gloss"]:
                        errors.append(f"vocabulary alignment {alignment['node_id']}: gloss does not match lemma "
                                      f"(expected {expected['gloss']!r})")
                    if lesson_hebrews.get(alignment["node_id"]) != expected["hebrew"]:
                        errors.append(f"vocabulary alignment {alignment['node_id']}: display form does not match "
                                      f"lemma (expected {expected['hebrew']!r})")
                token = scripture.execute("""
                    SELECT g.lemma,g.morph,b.work_id
                    FROM gematria g
                    JOIN verses v ON v.id=g.verse_id
                    JOIN books b ON b.id=v.book_id
                    WHERE g.verse_id=? AND g.word_index=?
                """, (alignment["example_verse_id"], alignment["example_word_index"])).fetchone()
                if not token:
                    errors.append(f"vocabulary alignment {alignment['node_id']}: token position missing")
                    continue
                _key, token_base = lemma_parts_for_validation(token[0])
                expected_prefix = "A" if alignment["language"] == "aramaic" else "H"
                if token_base != alignment["lemma_base"] or token[2] != "ot" or not token[1].startswith(expected_prefix):
                    errors.append(f"vocabulary alignment {alignment['node_id']}: lemma/language/work mismatch")
                if not all(alignment[field] for field in ("source_id", "source_version", "source_license")):
                    errors.append(f"vocabulary alignment {alignment['node_id']}: provenance missing")

    duplicate_rows = conn.execute("""
        SELECT node_id,question_type,question_text,COUNT(*) AS count,
               COUNT(DISTINCT correct_answer) AS answers
        FROM hebrew_practice_items
        GROUP BY node_id,question_type,question_text
        HAVING COUNT(*) > 1 OR COUNT(DISTINCT correct_answer) > 1
    """).fetchall()
    if duplicate_rows:
        errors.append(f"practice: {len(duplicate_rows)} duplicate question group(s)")

    expected_edges = [
        ("kaf", "kaf_final"),
        ("qal_perfect", "qal_imperfect"),
        ("syllable_basics", "syllable_open"),
    ]
    node_ids = {row[0] for row in conn.execute("SELECT id FROM hebrew_nodes")}
    for prerequisite, dependent in expected_edges:
        if prerequisite not in node_ids or dependent not in node_ids:
            continue
        if not conn.execute(
            "SELECT 1 FROM hebrew_edges WHERE source_id=? AND target_id=? AND edge_type='prerequisite'",
            (prerequisite, dependent),
        ).fetchone():
            errors.append(f"graph: expected prerequisite edge {prerequisite} -> {dependent}")
        if conn.execute(
            "SELECT 1 FROM hebrew_edges WHERE source_id=? AND target_id=? AND edge_type='prerequisite'",
            (dependent, prerequisite),
        ).fetchone():
            errors.append(f"graph: reversed prerequisite edge {dependent} -> {prerequisite}")

    for row in conn.execute("SELECT node_id, content_json FROM hebrew_lessons"):
        try:
            lesson = json.loads(row["content_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            errors.append(f"lesson {row['node_id']}: invalid JSON ({exc})")
            continue
        text = json.dumps(lesson, ensure_ascii=False)
        for phrase, reason in FORBIDDEN_CLAIMS.items():
            if phrase in text:
                errors.append(f"lesson {row['node_id']}: {reason} ({phrase!r})")
        refs = [(key, lesson.get(key)) for key in ("verse_example", "verse_ref")]
        refs.extend(("verse_examples", example.get("verse_ref"))
                    for example in lesson.get("verse_examples", []) if isinstance(example, dict))
        for key, ref in refs:
            if ref and not valid_ot_ref(ref):
                errors.append(f"lesson {row['node_id']}: non-OT or invalid {key} {ref!r}")
            elif ref and scripture:
                start = ref.split("-")[0]
                end = start.rsplit(".", 1)[0] + "." + ref.rsplit("-", 1)[1] if "-" in ref else start
                if not scripture.execute("SELECT 1 FROM verses WHERE id=?", (start,)).fetchone() or not scripture.execute("SELECT 1 FROM verses WHERE id=?", (end,)).fetchone():
                    errors.append(f"lesson {row['node_id']}: nonexistent verse {ref!r}")

    for row in conn.execute(
        "SELECT id,node_id,question_type,question_text,options_json,correct_answer,explanation "
        "FROM hebrew_practice_items"
    ):
        if row["question_type"] == "true_false" and NO_TRUE_FALSE:
            errors.append(f"practice {row['id']} ({row['node_id']}): true/false questions are not allowed")
        try:
            options = json.loads(row["options_json"] or "[]")
        except json.JSONDecodeError:
            errors.append(f"practice {row['id']} ({row['node_id']}): invalid options JSON")
            continue
        if any(option == "—" for option in options):
            errors.append(f"practice {row['id']} ({row['node_id']}): placeholder option")
        if len({str(option) for option in options}) != len(options):
            errors.append(f"practice {row['id']} ({row['node_id']}): duplicate options")
        if row["question_type"] in ASSESSED_TYPES and options and row["correct_answer"] not in options:
            errors.append(f"practice {row['id']} ({row['node_id']}): correct answer absent from options")
        # Answer must not be revealed by the question text (retrieval integrity).
        # Exemption: read_* nodes are reading-scaffolding "find this English word
        # in the passage" exercises (priming), not retrieval quiz questions — they
        # are never served by the quiz endpoint. Keep them as intentional design.
        answer = (row["correct_answer"] or "").strip()
        if answer and len(answer) > 2 and row["question_type"] != "true_false" \
                and not row["node_id"].startswith("read_"):
            norm_q = _norm_answer_in_question(row["question_text"])
            norm_a = _norm_answer_in_question(answer)
            if norm_a and re.search(r"(^|\s)" + re.escape(norm_a) + r"(\s|$)", norm_q):
                errors.append(
                    f"practice {row['id']} ({row['node_id']}): answer is given away in the question "
                    f"({answer!r})"
                )
        if re.match(r"^Is '.+' a .+ in Biblical Hebrew\?$", row["question_text"]):
            errors.append(f"practice {row['id']} ({row['node_id']}): tautological generated question")
        if "dss." in f"{row['question_text']} {row['explanation'] or ''}".casefold():
            errors.append(f"practice {row['id']} ({row['node_id']}): non-OT source")

    conn.close()
    if scripture:
        scripture.close()
    return errors


def valid_ot_ref(ref: str) -> bool:
    match = re.fullmatch(r"([1-3]?[a-z]+)\.(\d+)\.(\d+)(?:-(\d+))?", ref)
    return bool(match and match.group(1) in OT_BOOKS)


def lemma_parts_for_validation(raw_lemma: str) -> tuple[str, str]:
    lexical = (raw_lemma or "").strip().split("/")[-1].strip()
    lexical = re.sub(r"^[HG](?=\d)", "", lexical)
    match = re.match(r"(\d+)", lexical)
    return lexical, match.group(1) if match else lexical


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/memorize.db"))
    args = parser.parse_args()
    errors = validate(args.db)
    if errors:
        print(f"Hebrew content validation failed: {len(errors)} issue(s)")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Hebrew content validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
