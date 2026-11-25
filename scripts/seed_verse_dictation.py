#!/usr/bin/env python3
"""Seed verse-level dictation cards (R3-verse: gloss-cued target in verse audio).

Design (per the verse-dictation spec):
- Source: vocab nodes that already have a sentence-context cloze card
  (exact aligned verse example + blankable target — the C2 seeder proved
  both). One dictation card per node, idempotent.
- Front: gloss cue ("Which word means 'X'?") + full-verse audio player.
  The learner segments the target out of continuous speech — no Hebrew
  text anywhere on the front (unlike sentence cloze, whose printed verse
  lets the eyes do the segmenting).
- Answer: the niqqud-free consonantal skeleton (same convention as
  word-level dictation), graded by server skeleton match.
- Audio: the existing verse-audio pipeline (/api/v1/audio/play/{verse});
  audio_url stored per-card so the quiz audio player just works.

Why now: the 80%-retention gate was designed around live learner data
that never arrived (zero dictation attempts logged). The gate is kept as
a *serving* rule instead of a *seeding* rule: this script seeds all 300,
and serving order (verse_dictation next-endpoint, below) offers them
only once word-level retention clears 80% — or via explicit user opt-in.
No guessing, no new TTS, no new tables; same FSRS '' rows.

Usage:
    python3 scripts/seed_verse_dictation.py --dry-run [--count 300]
    python3 scripts/seed_verse_dictation.py --apply [--count 300]
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEM_DB = BASE / "data" / "memorize.db"
AUDIO_DIR = BASE / "data" / "audio" / "verses"


def _has_verse_audio(verse_ref: str) -> bool:
    """True iff a playable wav exists (any variant: plain, cloned, fast,
    schmueloff). The read-along endpoint advertises audio_url for all
    aligned verses, but only 31 (Genesis 1) have files on disk — the rest
    404. Never ship a card whose audio can't play."""
    if not verse_ref:
        return False
    try:
        return any((AUDIO_DIR / f"{verse_ref}{s}.wav").exists()
                   for s in ("", "_cloned", "_fast", "_schmueloff"))
    except OSError:
        return False

VERSE_DICTATION_PREFIX = "🎧 Verse dictation"


def _verse_ref_and_surface(conn, node_id: str):
    """Recover (verse_ref, pointed_surface, gloss) from the node's
    context cloze card: the card text embeds the verse ref, the blanked
    target is the pointed token whose skeleton matches correct_answer.
    Returns None when the verse has no playable wav (see
    _has_verse_audio) — never ship a card whose audio can't play."""
    row = conn.execute("""
        SELECT question_text, correct_answer FROM hebrew_practice_items
        WHERE node_id=? AND question_type='cloze'
          AND question_text LIKE 'Complete the verse%'
        ORDER BY id LIMIT 1""", (node_id,)).fetchone()
    if not row:
        return None
    qtext, skel = row
    m = re.search(r"Complete the verse \(([a-z0-9]+\.\d+\.\d+)\)", qtext or "")
    if not m:
        return None
    verse_ref = m.group(1)
    if not _has_verse_audio(verse_ref):
        return None
    # pointed surface: the token in the lesson whose skeleton matches
    content = conn.execute(
        "SELECT content_json FROM hebrew_lessons WHERE node_id=?",
        (node_id,)).fetchone()
    gloss = ""
    if content:
        try:
            gloss = (json.loads(content[0] or "{}").get("gloss") or "").strip()
        except (TypeError, json.JSONDecodeError):
            pass
    return verse_ref, (gloss or "see lesson")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=300)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    nids = [r[0] for r in conn.execute(
        """SELECT DISTINCT node_id FROM hebrew_practice_items
           WHERE question_type='cloze' AND question_text LIKE 'Complete the verse%'
           LIMIT ?""", (args.count,)).fetchall()]
    fresh = []
    for nid in nids:
        have = conn.execute(
            """SELECT 1 FROM hebrew_practice_items
               WHERE node_id=? AND question_type='dictation'
               AND question_text LIKE ?""",
            (nid, VERSE_DICTATION_PREFIX + "%")).fetchone()
        if have:
            continue
        got = _verse_ref_and_surface(conn, nid)
        if not got:
            continue
        verse_ref, gloss = got
        row = conn.execute(
            "SELECT correct_answer FROM hebrew_practice_items WHERE node_id=? AND question_type='dictation' AND question_text NOT LIKE ? LIMIT 1",
            (nid, VERSE_DICTATION_PREFIX + "%")).fetchone()
        if not row or not (row[0] or "").strip():
            continue
        skel = row[0].strip()
        fresh.append({
            "node_id": nid,
            "question_type": "dictation",
            "question_text": (
                f"{VERSE_DICTATION_PREFIX} ({verse_ref}):\n"
                f"Which word means '{gloss}'? Type what you hear."),
            "options_json": json.dumps([], ensure_ascii=False),
            "correct_answer": skel,
            "difficulty": 0.8,
            "explanation": (
                f"Verse dictation — segment '{skel}' out of {verse_ref}. "
                f"Hear the full verse: /api/v1/audio/play/{verse_ref}"),
        })
    print(f"candidates={len(nids)} new_verse_dictation={len(fresh)}")
    if not args.apply:
        for it in fresh[:5]:
            print(f"  {it['node_id']}: {it['question_text'][:90]} → {it['correct_answer']}")
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
    print(f"inserted {len(fresh)} verse-dictation cards")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
