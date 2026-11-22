#!/usr/bin/env python3
"""Seed sentence-context cloze cards for top-frequency vocabulary (Track C2).

For each of the top-N vocab nodes (by OT token frequency) that carries an
exact aligned verse example, create ONE context card on the vocab node:

  - Hebrew cloze: the real pointed verse with the target word blanked → the
    learner types the word (niqqud-free skeleton, same convention as the
    reading-node sentence cloze). Verse audio plays from the existing
    read-along pipeline: /api/v1/audio/play/{verse_example}.

The card rides the existing cloze/progress path: lesson quizzes serve it,
POST /hebrew/progress grades it server-side, and the lesson-loop feed writes
the FSRS '' row — the same scheduling guarantee as every other card
(hebrew-card-rules.md rule 7).

Idempotent: nodes that already hold a context card (question_text LIKE
'Complete the verse%') are skipped.

Usage:
    python3 scripts/seed_sentence_context.py --dry-run [--count 300]
    python3 scripts/seed_sentence_context.py --apply [--count 300]
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
sys.path.insert(0, str(BASE / "scripts"))
from generate_sentence_cloze import (  # noqa: E402
    distractor_words,
    normalize_final,
    strip_niqqud,
)

CONTEXT_PREFIX = "Complete the verse"


def _blank_target(verse_hebrew: str, surface: str) -> str | None:
    """Replace the first occurrence of the target with ______. Returns None
    when the surface cannot be located exactly (falls back to a
    niqqud-stripped token match)."""
    if surface and surface in verse_hebrew:
        return verse_hebrew.replace(surface, "______", 1)
    # Fallback: match on stripped tokens (handles separator drift).
    target = normalize_final(strip_niqqud(surface or ""))
    if not target:
        return None
    out, done = [], False
    for tok in (verse_hebrew or "").split():
        base = normalize_final(strip_niqqud(tok.replace("/", "")))
        if not done and base == target:
            out.append("______")
            done = True
        else:
            out.append(tok)
    return " ".join(out) if done else None


def collect_candidates(conn, count: int):
    """Top-N vocab nodes by OT token frequency with a verse example."""
    rows = conn.execute(
        "SELECT node_id, content_json FROM hebrew_lessons WHERE node_id LIKE 'vocab_%'"
    ).fetchall()
    cands = []
    for node_id, cj in rows:
        try:
            c = json.loads(cj or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        verse, heb_verse = c.get("verse_example"), c.get("verse_hebrew")
        surface = c.get("example_token_surface") or c.get("hebrew")
        if not (verse and heb_verse and surface):
            continue
        try:
            freq = int(c.get("ot_token_frequency") or c.get("frequency") or 0)
        except (TypeError, ValueError):
            freq = 0
        cands.append({
            "node_id": node_id,
            "freq": freq,
            "verse": verse,
            "verse_hebrew": heb_verse,
            "verse_english": (c.get("verse_english") or "").strip(),
            "surface": surface,
            "gloss": (c.get("gloss") or "").strip(),
        })
    cands.sort(key=lambda c: -c["freq"])
    return cands[:count]


def build_item(scrip, cand) -> dict | None:
    cloze = _blank_target(cand["verse_hebrew"], cand["surface"])
    if not cloze:
        return None
    skeleton = normalize_final(strip_niqqud(cand["surface"]))
    if not skeleton:
        return None
    eng = cand["verse_english"]
    hint = f' (“{eng[:90]}…”) ' if eng else " "
    return {
        "node_id": cand["node_id"],
        "question_type": "cloze",
        "question_text": (
            f"{CONTEXT_PREFIX} ({cand['verse']}):{hint}\n\n{cloze}"
        ),
        "options_json": json.dumps([skeleton], ensure_ascii=False),
        "correct_answer": skeleton,
        "difficulty": 0.6,
        "explanation": (
            f"'{cand['surface']}' = {cand['gloss'] or 'see lesson'} — "
            f"{cand['verse']}. Hear it: /api/v1/audio/play/{cand['verse']}"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=300)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    scrip = sqlite3.connect(str(BASE / "data" / "processed" / "scripture.db"))
    cands = collect_candidates(conn, args.count)
    have = {r[0] for r in conn.execute(
        "SELECT DISTINCT node_id FROM hebrew_practice_items "
        "WHERE question_text LIKE 'Complete the verse%'").fetchall()}
    fresh = [c for c in cands if c["node_id"] not in have]
    items = []
    for c in fresh:
        it = build_item(scrip, c)
        if it:
            items.append(it)
    print(f"candidates={len(cands)} already_have={len(have)} new_items={len(items)}")
    if not args.apply:
        for it in items[:5]:
            print(f"  {it['node_id']}: {it['question_text'][:100]}… → {it['correct_answer']}")
        print("dry run — pass --apply to write")
        return 0
    # Upgrade-in-place: a context card strictly dominates a same-answer
    # generic cloze on the same node (same retrieval + exact aligned verse +
    # audio link), so remove the redundant sibling instead of letting the
    # lesson-quiz same-answer dedup hide the context card forever.
    replaced = 0
    for it in items:
        cur = conn.execute(
            """DELETE FROM hebrew_practice_items
               WHERE node_id=? AND question_type='cloze'
               AND correct_answer=? AND question_text NOT LIKE 'Complete the verse%'""",
            (it["node_id"], it["correct_answer"]))
        replaced += cur.rowcount
    conn.executemany(
        """INSERT INTO hebrew_practice_items
           (node_id, question_type, question_text, options_json,
            correct_answer, difficulty, explanation)
           VALUES (:node_id, :question_type, :question_text, :options_json,
                   :correct_answer, :difficulty, :explanation)""",
        items)
    conn.commit()
    print(f"inserted {len(items)} sentence-context cards (replaced {replaced} generic cloze siblings)")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
