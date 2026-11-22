#!/usr/bin/env python3
"""Seed production (generate-from-scratch) cards (recall environment, P1).

Recognition (multiple choice) tests option-elimination; production tests the
memory itself (Bjork generation gradient: recognition → recall → production).
Three sources, all from lesson content already in the DB:

1. Verb-form production (typing on verb nodes): "Write the Qal imperfect
   3ms ('he will write')" → יִכְתֹּב. Learners type the unpointed skeleton;
   grading is niqqud-insensitive, so pointed answers stay canonical.
2. Root extraction (typing on root nodes): "אָהַב ('he loved') + אַהֲבָה
   ('love') share one root — write it" → אהב. One root unlocks dozens of
   words, so this is the highest-leverage card in the bank.
3. Phrase production (typing on phrase nodes): "Say 'Behold, here I am'
   in Hebrew" → הִנְנִי (title carries surface — gloss).

Items ride the existing typing/progress path (typed FREE_TEXT in quizzes,
MC-converted in mc lesson mode) and feed FSRS '' rows. Idempotent: nodes
that already hold a same-answer typing item are skipped.

Usage:
    python3 scripts/seed_production.py --dry-run
    python3 scripts/seed_production.py --apply
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEM_DB = BASE / "data" / "memorize.db"
sys.path.insert(0, str(BASE / "scripts"))
from seed_verb_parse import FORM_OF, extract  # noqa: E402
from generate_sentence_cloze import normalize_final, strip_niqqud  # noqa: E402


def _have_same_answer(conn, node_id: str, answer: str) -> bool:
    return conn.execute(
        """SELECT 1 FROM hebrew_practice_items
           WHERE node_id=? AND question_type='typing' AND correct_answer=?""",
        (node_id, answer)).fetchone() is not None


def verb_items(conn):
    items = []
    for nid, (binyan, form) in FORM_OF.items():
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                           (nid,)).fetchone()
        if not row:
            continue
        try:
            exp = json.loads(row[0] or "{}").get("explanation", "")
        except (TypeError, json.JSONDecodeError):
            continue
        for surface, gloss, person in extract(exp, nid):
            form_word = f" {form}" if form else ""
            person_word = f" {person}" if person else ""
            gloss_hint = f" ('{gloss}')" if gloss else ""
            items.append({
                "node_id": nid,
                "question_text": (
                    f"Write the {binyan}{form_word}{person_word}{gloss_hint} in Hebrew."),
                "correct_answer": surface,
            })
    return items


def root_items(conn):
    items = []
    for (nid,) in conn.execute("SELECT node_id FROM hebrew_lessons WHERE node_id LIKE 'root\\_%' ESCAPE '\\'"):
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                           (nid,)).fetchone()
        try:
            c = json.loads(row[0] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        root, derived = c.get("root"), c.get("derived_words") or []
        if not root or len(derived) < 2:
            continue
        shown = [(w.get("word", ""), w.get("gloss", "")) for w in derived[:3]]
        shown = [(w, g) for w, g in shown if w]
        if len(shown) < 2:
            continue
        examples = " + ".join(f"{w} ('{g}')" if g else w for w, g in shown)
        items.append({
            "node_id": nid,
            "question_text": f"These words share one root: {examples} — write the root.",
            "correct_answer": root,
        })
    return items


def phrase_items(conn):
    items = []
    for (nid,) in conn.execute("SELECT node_id FROM hebrew_lessons WHERE node_id LIKE 'phrase\\_%' ESCAPE '\\'"):
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                           (nid,)).fetchone()
        try:
            title = (json.loads(row[0] or "{}").get("title") or "")
        except (TypeError, json.JSONDecodeError):
            continue
        if "—" not in title:
            continue
        surface, _, gloss = title.partition("—")
        surface, gloss = surface.strip(), gloss.strip()
        if not surface or not gloss or len(surface) < 2:
            continue
        items.append({
            "node_id": nid,
            "question_text": f"Say '{gloss}' in Hebrew.",
            "correct_answer": surface,
        })
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    fresh = []
    for it in verb_items(conn) + root_items(conn) + phrase_items(conn):
        if not _have_same_answer(conn, it["node_id"], it["correct_answer"]):
            fresh.append({**it, "question_type": "typing",
                          "options_json": json.dumps([], ensure_ascii=False),
                          "difficulty": 0.75,
                          "explanation": f"Production drill — generate, don't recognize."})
    print(f"candidates={len(fresh)} new production cards")
    if not args.apply:
        for it in fresh[:6]:
            print(f"  {it['node_id']}: {it['question_text'][:80]} → {it['correct_answer']}")
        print("dry run — pass --apply to write")
        return 0
    conn.executemany(
        """INSERT INTO hebrew_practice_items
           (node_id, question_type, question_text, options_json,
            correct_answer, difficulty, explanation)
           VALUES (:node_id, :question_type, :question_text, :options_json,
                   :correct_answer, :difficulty, :explanation)""",
        fresh)
    conn.commit()
    print(f"inserted {len(fresh)} production cards")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
