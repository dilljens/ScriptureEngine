#!/usr/bin/env python3
"""Seed word-level dictation cards (active-recall R3, word level).

Hearing cards test recognition (audio → think the gloss); dictation
tests segmentation + orthography (audio → type the form) — the next rung
on the Bjork generation gradient. Only nodes with a node-id TTS wav are
seeded, so the card audio URL (`/api/v1/audio/word/{node_id}`) never leaks
the surface in the URL and always resolves.

Items ride the existing typing path: typed FREE_TEXT in quizzes (with the
quiz audio player), MC-converted in mc lesson mode, graded by skeleton
match via /hebrew/progress, FSRS '' rows. Idempotent.

Verse-level dictation (gloss-cued target word inside verse audio) waits
until word-level retention clears 80%.

Usage:
    python3 scripts/seed_dictation.py --dry-run
    python3 scripts/seed_dictation.py --apply
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEM_DB = BASE / "data" / "memorize.db"
WORDS_DIR = BASE / "data" / "audio" / "words"

sys.path.insert(0, str(BASE / "scripts"))
from generate_sentence_cloze import normalize_final, strip_niqqud  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    fresh = []
    for (nid,) in conn.execute(
            "SELECT id FROM hebrew_nodes WHERE id LIKE 'vocab\\_%' ESCAPE '\\' ORDER BY id"):
        if not (WORDS_DIR / f"{nid}.wav").exists():
            continue
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                           (nid,)).fetchone()
        try:
            surf = (json.loads(row[0] or "{}").get("hebrew") or "").strip()
        except (TypeError, json.JSONDecodeError):
            continue
        skel = normalize_final(strip_niqqud(surf))
        if not skel:
            continue
        dup = conn.execute(
            """SELECT 1 FROM hebrew_practice_items
               WHERE node_id=? AND question_type='dictation' AND correct_answer=?""",
            (nid, skel)).fetchone()
        if dup:
            continue
        fresh.append({
            "node_id": nid,
            "question_type": "dictation",
            "question_text": "🔊 Listen and type the word you hear.",
            "options_json": json.dumps([], ensure_ascii=False),
            "correct_answer": skel,
            "difficulty": 0.8,
            "explanation": f"Dictation — spell {surf} from sound alone.",
        })
    print(f"new dictation cards: {len(fresh)}")
    if not args.apply:
        for it in fresh[:5]:
            print(f"  {it['node_id']} → {it['correct_answer']}")
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
    print(f"inserted {len(fresh)} dictation cards")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
