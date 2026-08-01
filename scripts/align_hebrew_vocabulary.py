#!/usr/bin/env python3
"""Align generated Hebrew vocabulary lessons to exact OSHB OT tokens."""

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

try:
    from scripts.seed_hebrew_vocabulary import get_top_words, make_lesson_id
except ModuleNotFoundError:
    from seed_hebrew_vocabulary import get_top_words, make_lesson_id

BASE = Path(__file__).parent.parent
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"
MEM_DB = BASE / "data" / "memorize.db"
SOURCE = {
    "source_id": "oshb",
    "source_version": "3d15126fb1ef74867fc1434be1942e837932691f",
    "source_license": "WLC text: public domain; OSHB morphology/lemmas: CC BY 4.0",
    "source_attribution": "Open Scriptures Hebrew Bible Project",
}

# The legacy lemma_gloss table contains wrong glosses for a handful of Aramaic
# lexemes (e.g. "Daniel" for the relative particle), and earlier fix scripts
# replaced their Hebrew surfaces with unrelated Daniel narratives. These are
# authoritative corrected citation forms keyed by Strong's numeric base.
LEMMA_OVERRIDES = {
    "1768": {"hebrew": "דִּי", "gloss": "that, which", "transliteration": "di",
             "description": "The Aramaic relative particle 'that, which, who'. Used throughout the Aramaic sections of Daniel and Ezra."},
    "4430": {"hebrew": "מֶלֶךְ", "gloss": "king (Aramaic)", "transliteration": "melekh",
             "description": "The Aramaic word for 'king'. Used extensively in Daniel for Nebuchadnezzar, Belshazzar, and Darius."},
    "426": {"hebrew": "אֱלָהּ", "gloss": "God (Aramaic)", "transliteration": "elah",
            "description": "The Aramaic word for 'God'. Used in Daniel and Ezra."},
    "1934": {"hebrew": "הָוָא", "gloss": "to be, become", "transliteration": "hava",
             "description": "The Aramaic verb 'to be, become, come to pass'. Common in the Aramaic sections of Daniel and Ezra."},
    "1836": {"hebrew": "דֵּן", "gloss": "this", "transliteration": "den",
             "description": "The Aramaic demonstrative pronoun 'this'. Used in Daniel and Ezra."},
}

_DISTRACTORS = ["God", "king", "this", "that", "to be", "Israel", "LORD", "father"]


def reconciled_gloss(lemma_base: str, current_gloss: str) -> str:
    return LEMMA_OVERRIDES.get(lemma_base, {}).get("gloss", current_gloss or "")


def lemma_parts(raw_lemma: str) -> tuple[str, str]:
    """Return the lexical lemma (with homonym suffix) and numeric base."""
    lexical = (raw_lemma or "").strip().split("/")[-1].strip()
    lexical = re.sub(r"^[HG](?=\d)", "", lexical)
    match = re.match(r"(\d+)", lexical)
    return lexical, match.group(1) if match else lexical


def cloze_at_word_index(verse_text: str, word_index: int) -> str:
    """Blank one OSHB token position, never a substring inside another word."""
    words = verse_text.split()
    if not 0 <= word_index < len(words):
        raise ValueError(f"word index {word_index} outside {len(words)}-token verse")
    words[word_index] = "______"
    return " ".join(words)


def unpointed(word: str) -> str:
    """Reduce a Hebrew token to its consonant skeleton for typed-answer grading.

    The learner-facing UI has no niqqud entry, so production (typing/cloze/recall)
    answers are stored and compared as unpointed skeletons. This also removes the
    OSHB morpheme-separator slash. Choice questions keep their pointed options.
    """
    return re.sub(r"[\u0591-\u05c7]", "", word or "").replace("/", "")


def load_ot_occurrences(scripture: sqlite3.Connection):
    by_base = defaultdict(list)
    token_frequency = defaultdict(int)
    verses_by_base = defaultdict(set)
    rows = scripture.execute("""
        SELECT g.verse_id,g.word_index,g.word_hebrew,g.lemma,g.morph,
               v.text_hebrew,v.text_english,b.position,v.chapter,v.verse
        FROM gematria g
        JOIN verses v ON v.id=g.verse_id
        JOIN books b ON b.id=v.book_id
        WHERE b.work_id='ot' AND (g.morph LIKE 'H%' OR g.morph LIKE 'A%')
        ORDER BY b.position,v.chapter,v.verse,g.word_index
    """)
    for row in rows:
        key, base = lemma_parts(row["lemma"])
        if not base:
            continue
        occurrence = dict(row)
        occurrence["lemma_key"] = key
        occurrence["lemma_base"] = base
        language = "aramaic" if row["morph"].startswith("A") else "hebrew"
        occurrence["language"] = language
        corpus_key = (language, base)
        by_base[corpus_key].append(occurrence)
        token_frequency[corpus_key] += 1
        verses_by_base[corpus_key].add(row["verse_id"])
    return by_base, token_frequency, verses_by_base


def choose_occurrence(candidates, source_key):
    exact = [row for row in candidates if row["lemma_key"] == source_key]
    pool = exact or candidates
    return min(pool, key=lambda row: (row["lemma"].count("/"), row["position"], row["chapter"], row["verse"], row["word_index"]))


def ensure_schema(mem: sqlite3.Connection):
    mem.executescript("""
        CREATE TABLE IF NOT EXISTS hebrew_vocabulary_alignment (
            node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
            lemma_key TEXT NOT NULL,
            lemma_base TEXT NOT NULL,
            strongs_id TEXT NOT NULL,
            language TEXT NOT NULL,
            example_verse_id TEXT NOT NULL,
            example_word_index INTEGER NOT NULL,
            token_surface TEXT NOT NULL,
            token_lemma_raw TEXT NOT NULL,
            token_morph TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_version TEXT NOT NULL,
            source_license TEXT NOT NULL,
            alignment_method TEXT NOT NULL DEFAULT 'exact_lemma',
            confidence REAL NOT NULL DEFAULT 1.0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS hebrew_attestations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
            verse_id TEXT NOT NULL,
            attestation_type TEXT NOT NULL DEFAULT 'grammar',
            explanation TEXT DEFAULT '',
            difficulty TEXT DEFAULT 'beginner',
            UNIQUE(node_id,verse_id)
        );
    """)


def align(mem_db=MEM_DB, scripture_db=SCRIPTURE_DB, count=500):
    scripture = sqlite3.connect(scripture_db)
    scripture.row_factory = sqlite3.Row
    mem = sqlite3.connect(mem_db)
    mem.row_factory = sqlite3.Row
    ensure_schema(mem)

    occurrences, frequencies, verse_sets = load_ot_occurrences(scripture)
    source_words = get_top_words(count=count, db_path=scripture_db)
    # Prefer existing alignment identities so corpus ranking changes (e.g. a
    # lexicon frequency rebuild) never renumber lesson node IDs. Match by
    # Hebrew surface first (homographs like את H853/H854 keep their lesson),
    # then by (language, Strong's base).
    existing_by_surface = {}
    existing_by_base = {}
    for row in mem.execute("""
        SELECT a.language, a.lemma_base, a.node_id, l.content_json
        FROM hebrew_vocabulary_alignment a
        LEFT JOIN hebrew_lessons l ON l.node_id=a.node_id
    """):
        try:
            surface = (json.loads(row[3] or "{}") or {}).get("hebrew", "")
        except (TypeError, json.JSONDecodeError):
            surface = ""
        if surface:
            existing_by_surface[(row[0], unpointed(surface))] = row[2]
        existing_by_base[(row[0], row[1])] = row[2]
    aligned = 0
    skipped = 0
    missing = []

    for index, word in enumerate(source_words):
        lemma_key, lemma_base = lemma_parts(word["lemma"])
        language = "aramaic" if word.get("morphology", "").startswith("A") else "hebrew"
        node_id = (
            existing_by_surface.get((language, unpointed(word["hebrew"])))
            or existing_by_base.get((language, lemma_base))
            or make_lesson_id(word["hebrew"], index)
        )
        lesson_row = mem.execute(
            "SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)
        ).fetchone()
        if not lesson_row:
            # A top-frequency word with no lesson yet is a seeding gap, not an
            # alignment failure; lesson creation is out of scope here.
            skipped += 1
            continue
        corpus_key = (language, lemma_base)
        candidates = occurrences.get(corpus_key, [])
        if not candidates:
            missing.append(f"{node_id}: no exact OT token for {word['lemma']}")
            continue
        occurrence = choose_occurrence(candidates, lemma_key)
        lesson = json.loads(lesson_row["content_json"])
        override = LEMMA_OVERRIDES.get(lemma_base, {})
        old_hebrew = lesson.get("hebrew", "")
        old_gloss = lesson.get("gloss", "")
        hebrew = override.get("hebrew") or old_hebrew or word["hebrew"]
        gloss = override.get("gloss") or reconciled_gloss(lemma_base, old_gloss)
        transliteration = override.get("transliteration") or lesson.get("transliteration", "")
        description = override.get("description") or lesson.get("description", "")
        lesson_changed = (gloss and gloss != old_gloss) or (hebrew and hebrew != old_hebrew)
        lesson.update({
            "lemma": word["lemma"],
            "lemma_key": lemma_key,
            "lemma_base": lemma_base,
            "strongs_id": f"H{lemma_base}" if lemma_base.isdigit() else "",
            "language": language,
            "hebrew": hebrew,
            "gloss": gloss,
            "transliteration": transliteration,
            "description": description,
            "title": f"{hebrew} — {gloss}" if gloss else lesson.get("title"),
            "ot_token_frequency": frequencies[corpus_key],
            "ot_verse_frequency": len(verse_sets[corpus_key]),
            "verse_example": occurrence["verse_id"],
            "verse_hebrew": occurrence["text_hebrew"],
            "verse_english": occurrence["text_english"],
            "example_token_surface": occurrence["word_hebrew"],
            "example_word_index": occurrence["word_index"],
            "example_token_morph": occurrence["morph"],
            "provenance": {**SOURCE, "alignment_method": "exact_lemma", "confidence": 1.0},
        })
        # A valid OT example is now attached; clear any earlier quarantine marker.
        lesson.pop("example_status", None)
        lesson.pop("example_note", None)
        # Keep the curriculum list row in sync with the reconciled citation form.
        node_row = mem.execute(
            "SELECT description FROM hebrew_nodes WHERE id=?", (node_id,)
        ).fetchone()
        node_description = (node_row[0] if node_row else "") or ""
        description_differs = description and description != node_description
        if (lesson_changed or description_differs) and hebrew and gloss:
            mem.execute(
                "UPDATE hebrew_nodes SET title=?, description=? WHERE id=?",
                (f"{hebrew} — {gloss}", (description or node_description)[:200], node_id),
            )
        stale_answers = bool(mem.execute(
            "SELECT 1 FROM hebrew_practice_items WHERE node_id=? AND "
            "(correct_answer=? OR correct_answer=?) LIMIT 1",
            (node_id, hebrew, old_gloss),
        ).fetchone())
        if lesson_changed or stale_answers:
            # Rebuild practice so no stale pointed/glossed answer contradicts the
            # aligned lemma (affects the Aramaic lexemes and any migrated lesson).
            mem.execute("DELETE FROM hebrew_practice_items WHERE node_id=?", (node_id,))
            typed = unpointed(hebrew)
            distractors = [d for d in _DISTRACTORS if d != gloss][:3]
            options = json.dumps([gloss] + distractors, ensure_ascii=False)
            for qtype, qtext, opts, answer, difficulty, explanation in [
                ("multiple_choice", f"What does '{hebrew}' mean?", options, gloss, 0.3,
                 f"'{hebrew}' means '{gloss}'."),
                ("recall", f"What is the Hebrew/Aramaic word for '{gloss}'?", "[]", typed, 0.5,
                 f"The word is '{hebrew}' ({gloss})."),
                ("typing", f"Type the Hebrew/Aramaic word: '{gloss}'", "[]", typed, 0.7,
                 f"Type '{hebrew}' ({gloss})"),
            ]:
                mem.execute(
                    "INSERT OR IGNORE INTO hebrew_practice_items "
                    "(node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (node_id, qtype, qtext, opts, answer, difficulty, explanation),
                )
        encoded = json.dumps(lesson, ensure_ascii=False)
        mem.execute("""
            UPDATE hebrew_lessons SET content_json=?,version=version+1,updated_at=datetime('now')
            WHERE node_id=? AND content_json<>?
        """, (encoded, node_id, encoded))
        mem.execute("""
            INSERT INTO hebrew_vocabulary_alignment
                (node_id,lemma_key,lemma_base,strongs_id,language,example_verse_id,
                 example_word_index,token_surface,token_lemma_raw,token_morph,
                 source_id,source_version,source_license,alignment_method,confidence)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'exact_lemma',1.0)
            ON CONFLICT(node_id) DO UPDATE SET
                lemma_key=excluded.lemma_key,lemma_base=excluded.lemma_base,
                strongs_id=excluded.strongs_id,language=excluded.language,
                example_verse_id=excluded.example_verse_id,
                example_word_index=excluded.example_word_index,
                token_surface=excluded.token_surface,token_lemma_raw=excluded.token_lemma_raw,
                token_morph=excluded.token_morph,source_id=excluded.source_id,
                source_version=excluded.source_version,source_license=excluded.source_license,
                alignment_method='exact_lemma',confidence=1.0,
                updated_at=CASE WHEN
                    hebrew_vocabulary_alignment.example_verse_id<>excluded.example_verse_id OR
                    hebrew_vocabulary_alignment.example_word_index<>excluded.example_word_index OR
                    hebrew_vocabulary_alignment.lemma_key<>excluded.lemma_key
                THEN datetime('now') ELSE hebrew_vocabulary_alignment.updated_at END
        """, (
            node_id, lemma_key, lemma_base,
            f"H{lemma_base}" if lemma_base.isdigit() else "", language,
            occurrence["verse_id"], occurrence["word_index"], occurrence["word_hebrew"],
            occurrence["lemma"], occurrence["morph"], SOURCE["source_id"],
            SOURCE["source_version"], SOURCE["source_license"],
        ))

        # Replace only practice derived from unsafe verse-context generation.
        mem.execute("""
            DELETE FROM hebrew_practice_items
            WHERE node_id=? AND (
                question_text LIKE 'Complete the verse:%' OR
                question_text LIKE 'In the verse %' OR
                question_text LIKE 'Translate this into Hebrew:%'
            )
        """, (node_id,))
        cloze = cloze_at_word_index(occurrence["text_hebrew"], occurrence["word_index"])
        question = f"Complete the exact OT token in {occurrence['verse_id']}:\n\n{cloze}"
        explanation = (
            f"OSHB token {occurrence['verse_id']}#{occurrence['word_index']} is "
            f"{occurrence['word_hebrew']} (lemma {occurrence['lemma']})."
        )
        mem.execute(
            "DELETE FROM hebrew_practice_items WHERE node_id=? AND "
            "question_text LIKE 'Complete the exact OT token in %'",
            (node_id,),
        )
        mem.execute("""
            INSERT OR IGNORE INTO hebrew_practice_items
                (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation)
            VALUES (?,'cloze',?,'[]',?,0.6,?)
        """, (node_id, question, unpointed(occurrence["word_hebrew"]), explanation))
        mem.execute("""
            INSERT INTO hebrew_attestations
                (node_id,verse_id,attestation_type,explanation,difficulty)
            VALUES (?,?,'exact_lemma',?,'beginner')
            ON CONFLICT(node_id,verse_id) DO UPDATE SET
                attestation_type='exact_lemma',explanation=excluded.explanation
        """, (node_id, occurrence["verse_id"], explanation))
        aligned += 1

    mem.commit()
    scripture.close()
    mem.close()
    if missing:
        raise RuntimeError("Vocabulary alignment incomplete:\n" + "\n".join(missing[:20]))
    print(f"Aligned {aligned}/{count} vocabulary lessons to exact OT lemma tokens"
          f" ({skipped} top-frequency words without lessons skipped)")
    return aligned


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=MEM_DB)
    parser.add_argument("--scripture-db", type=Path, default=SCRIPTURE_DB)
    parser.add_argument("--count", type=int, default=500)
    args = parser.parse_args()
    align(args.db, args.scripture_db, args.count)
