#!/usr/bin/env python3
"""Seed verb-parse practice items from verb lessons (Track C3).

Parses surface→gloss pairs out of each verb lesson's explanation
(`3ms: יִכְתֹּב (he will write)`, `Pattern: נִכְתַּב (it was written)`) and
creates ONE `parse` item per surface:

  prompt:  the pointed surface + gloss hint
  answer:  "Binyan form person"  (e.g. "Qal perfect 3ms", "Niphal", "Qal infinitive")

Person tags come from the `2ms:`-style prefix where present; binyan/form come
from the node id (`qal_perfect` → Qal perfect, `weak_he` → Qal III-He).

Grading is server-side keyword matching (`_parse_matches` in
web/routes/hebrew.py): the answer must name the binyan, the form, and the
person (codes or long forms, e.g. `3ms` ≡ `third masculine singular`).
Items ride the existing /hebrew/progress path → FSRS '' rows
(hebrew-card-rules.md rule 7).

Idempotent: nodes that already hold parse items are skipped.

Usage:
    python3 scripts/seed_verb_parse.py --dry-run
    python3 scripts/seed_verb_parse.py --apply
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

HEB = r"[֐-׿]"
PERSON_PAT = re.compile(r"(1c[sp]|2m[sp]|2f[sp]|3m[sp]|3f[sp]):\s*(" + HEB + r"+)(?:\s*\(([^)]*)\))?")
GENERIC_PAT = re.compile(r"(" + HEB + r"{2,})(?:\s*\(([^)]{2,60})\))?")

FORM_OF = {
    "qal_perfect": ("Qal", "perfect"),
    "qal_imperfect": ("Qal", "imperfect"),
    "qal_imperative": ("Qal", "imperative"),
    "qal_infinitive": ("Qal", "infinitive"),
    "qal_participle": ("Qal", "participle"),
    "niphal": ("Niphal", ""),
    "piel": ("Piel", ""),
    "pual": ("Pual", ""),
    "hiphil": ("Hiphil", ""),
    "hophal": ("Hophal", ""),
    "hithpael": ("Hithpael", ""),
    "weak_guttural": ("Qal", "I-guttural"),
    "weak_nun": ("Qal", "I-nun"),
    "weak_he": ("Qal", "III-he"),
    "weak_hollow": ("Qal", "hollow"),
    "weak_double": ("Qal", "double-ayin"),
    "weak_initial_yod": ("Qal", "I-yod"),
    "weak_initial_aleph": ("Qal", "I-aleph"),
    "weak_final_aleph": ("Qal", "III-aleph"),
    "weak_doubly": ("Qal", "doubly-weak"),
}

SKIP_TOKENS = {"א־מ־ר", "אהחע"}  # meta-notation, not real forms


def extract(explanation: str, node_id: str):
    """Return [(surface, gloss, person_or_None)]."""
    out = []
    for person, surface, gloss in PERSON_PAT.findall(explanation or ""):
        if surface not in SKIP_TOKENS:
            out.append((surface, (gloss or "").strip(), person))
    if out:
        return out
    for surface, gloss in GENERIC_PAT.findall(explanation or ""):
        letters = re.sub(r"[\u0591-\u05C7]", "", surface)
        # Prefix fragments (הִתְ) have no gloss; real 2-letter roots (קָם) do.
        if surface in SKIP_TOKENS or (len(letters) < 3 and not (gloss or "").strip()):
            continue
        if any(s == surface for s, _, _ in out):
            continue
        out.append((surface, (gloss or "").strip(), None))
        if len(out) >= 4:
            break
    return out


def build_item(node_id: str, surface: str, gloss: str, person: str | None):
    binyan, form = FORM_OF.get(node_id, ("Qal", ""))
    parts = [binyan, form, person or ""]
    answer = " ".join(p for p in parts if p).strip()
    hint = f" Gloss: '{gloss}'." if gloss else ""
    form_word = f" {form}" if form else ""
    person_word = f" ({person})" if person else ""
    return {
        "node_id": node_id,
        "question_type": "parse",
        "question_text": (
            f"Parse the verb form:\n\n{surface}{person_word}"
            f"\n\nName the binyan and{form_word} form"
            f"{' and person' if person else ''}"
            f" (e.g. '{answer}').{hint}"
        ),
        "options_json": json.dumps([], ensure_ascii=False),
        "correct_answer": answer,
        "difficulty": 0.7,
        "explanation": f"{surface} = {binyan}{form_word}{person_word or ''} — see the {node_id} lesson.",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    nodes = [r[0] for r in conn.execute(
        "SELECT id FROM hebrew_nodes WHERE category='verb' ORDER BY id").fetchall()]
    have = {r[0] for r in conn.execute(
        "SELECT DISTINCT node_id FROM hebrew_practice_items WHERE question_type='parse'").fetchall()}
    items = []
    for nid in nodes:
        if nid in have or nid not in FORM_OF:
            continue
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                           (nid,)).fetchone()
        if not row:
            continue
        try:
            exp = (json.loads(row[0] or "{}")).get("explanation", "")
        except (TypeError, json.JSONDecodeError):
            continue
        for surface, gloss, person in extract(exp, nid):
            items.append(build_item(nid, surface, gloss, person))
    print(f"verb_nodes={len(nodes)} already_have={len(have)} new_items={len(items)}")
    if not args.apply:
        for it in items[:6]:
            print(f"  {it['node_id']}: {it['question_text'].splitlines()[2]} → {it['correct_answer']}")
        print("dry run — pass --apply to write")
        return 0
    conn.executemany(
        """INSERT INTO hebrew_practice_items
           (node_id, question_type, question_text, options_json,
            correct_answer, difficulty, explanation)
           VALUES (:node_id, :question_type, :question_text, :options_json,
                   :correct_answer, :difficulty, :explanation)""",
        items)
    conn.commit()
    print(f"inserted {len(items)} verb-parse cards")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
