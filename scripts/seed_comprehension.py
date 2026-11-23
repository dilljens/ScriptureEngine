#!/usr/bin/env python3
"""Seed verse-scope comprehension checks (active-recall R4a).

Word-presence true/false: "Gen 1:1 contains the word בָּרָא ('he created')."
True items use the node's own aligned example token; False items swap in a
different top word VERIFIED ABSENT from the verse's folded tokens (a present
absent-word would teach a lie — the check is the point).

This is verse-scope verification (does the word belong to this verse?), the
bridge between word cards and reading. Full meaning-judgment claims
("the verse says X") need hand review and stay deferred.

Type true_false with options ["True","False"]: renders as 2-option choice
in cumulative/mental quizzes; kept unconverted (never padded to 5) in mc
lesson quizzes. Graded by the existing choice matcher; FSRS '' rows.

Idempotent (exact question_text match).

Usage:
    python3 scripts/seed_comprehension.py --dry-run [--count 300]
    python3 scripts/seed_comprehension.py --apply [--count 300]
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
from generate_sentence_cloze import normalize_final, strip_niqqud  # noqa: E402


def verse_tokens(verse_hebrew: str) -> set:
    toks = set()
    for chunk in (verse_hebrew or "").split():
        t = normalize_final(strip_niqqud(chunk.replace("/", "")))
        if t:
            toks.add(t)
    return toks


def collect(conn, count: int):
    rows = conn.execute(
        "SELECT node_id, content_json FROM hebrew_lessons WHERE node_id LIKE 'vocab\\_%' ESCAPE '\\'"
    ).fetchall()
    cands = []
    for node_id, cj in rows:
        try:
            c = json.loads(cj or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        verse, heb_verse = c.get("verse_example"), c.get("verse_hebrew")
        surface = c.get("example_token_surface") or c.get("hebrew")
        gloss = (c.get("gloss") or "").strip()
        if not (verse and heb_verse and surface and gloss):
            continue
        try:
            freq = int(c.get("ot_token_frequency") or c.get("frequency") or 0)
        except (TypeError, ValueError):
            freq = 0
        cands.append({"node_id": node_id, "freq": freq, "verse": verse,
                      "verse_hebrew": heb_verse, "surface": surface, "gloss": gloss})
    cands.sort(key=lambda c: -c["freq"])
    return cands[:count]


def build(conn, cand, top):
    """(true_item, false_item) or (None, None) if no clean absent word."""
    vtoks = verse_tokens(cand["verse_hebrew"])
    target = normalize_final(strip_niqqud(cand["surface"]))
    if not target or target not in vtoks:
        return None, None
    foil = None
    for other in top:
        if other["node_id"] == cand["node_id"]:
            continue
        osurf = normalize_final(strip_niqqud(other["surface"]))
        if not osurf or osurf in vtoks or osurf == target:
            continue
        if not other["gloss"]:
            continue
        foil = other
        break
    if foil is None:
        return None, None
    fsurf = normalize_final(strip_niqqud(foil["surface"]))
    true_q = (f"The word {cand['surface']} ('{cand['gloss']}') "
              f"appears in {cand['verse']}.")
    false_q = (f"The word {foil['surface']} ('{foil['gloss']}') "
               f"appears in {cand['verse']}.")
    mk = lambda q, a: {
        "node_id": cand["node_id"],
        "question_type": "true_false",
        "question_text": q,
        "options_json": json.dumps(["True", "False"], ensure_ascii=False),
        "correct_answer": a,
        "difficulty": 0.55,
        "explanation": f"{cand['surface']} ('{cand['gloss']}') is in {cand['verse']}; "
                       f"{fsurf} ('{foil['gloss']}') is not.",
    }
    return mk(true_q, "True"), mk(false_q, "False")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=300)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    top = collect(conn, args.count)
    fresh = []
    for cand in top:
        t, f = build(conn, cand, top)
        for it in (t, f):
            if it is None:
                continue
            dup = conn.execute(
                """SELECT 1 FROM hebrew_practice_items
                   WHERE node_id=? AND question_type='true_false' AND question_text=?""",
                (it["node_id"], it["question_text"])).fetchone()
            if not dup:
                fresh.append(it)
    print(f"candidates={len(top)} new_comprehension={len(fresh)}")
    if not args.apply:
        for it in fresh[:6]:
            print(f"  {it['node_id']}: {it['question_text'][:85]} → {it['correct_answer']}")
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
    print(f"inserted {len(fresh)} comprehension checks")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
