#!/usr/bin/env python3
"""Replace degenerate worked examples and generic key_points with real ones.

Math Academy Way review finding: 93 lessons had real explanations but their
worked examples were lazy stubs ("What is X?" / "See the explanation above.")
and 90 had generic key_points ("Key concept in consonant" / "Review the
explanation above"). A worked example must MODEL how to recognize or use the
concept, and key_points must state the actual takeaways.

This script regenerates both fields from each lesson's own explanation:
  - worked_examples: a question that tests recognition/application of the
    concept, with steps that quote the explanation's concrete facts.
  - key_points: 3-4 bullet facts extracted from the explanation.
It only touches lessons whose current worked_examples are degenerate or whose
key_points are the generic fallback, and never touches clean lessons.

Usage:
    python3 scripts/fix_degenerate_worked_examples.py --dry-run
    python3 scripts/fix_degenerate_worked_examples.py --apply
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

DEGENERATE_QUESTION = re.compile(
    r"^What (?:is|does) .+ (?:noun|verb|letter|vowel|syllable|reading|word|concept|pattern|root)\??$"
)
GENERIC_KEYPOINT = re.compile(r"Key concept in|Review the explanation above")


def _sentences(text: str) -> list:
    """Split explanation into sentences (keep short ones too)."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _key_points_from_explanation(explanation: str, max_points: int = 4) -> list:
    """Extract 3-4 concrete facts from an explanation.

    Prefers sentences containing concrete cues (examples, 'means', 'used for',
    'marked by', 'pattern', numbers, Hebrew chars), then falls back to the
    first sentences. Caps at max_points, each ≤ ~140 chars.
    """
    sents = _sentences(explanation)
    if not sents:
        return []
    cue = re.compile(r"(means|used for|marked by|pattern|e\.g\.|example|ה|־|מ|ב|כ|ל|ו|י|נ|ת|\b\d\b)", re.I)
    ranked = sorted(sents, key=lambda s: (not cue.search(s), len(s)))
    points = []
    for s in ranked:
        s = re.sub(r"\s+", " ", s)
        if len(s) > 140:
            s = s[:137].rstrip() + "\u2026"
        if s and s not in points:
            points.append(s)
        if len(points) >= max_points:
            break
    return points


def _worked_example_from_explanation(explanation: str, title: str, glyph: str) -> dict:
    """Build a recognition/application worked example grounded in the explanation."""
    sents = _sentences(explanation)
    steps = []
    for s in sents[:3]:
        s = re.sub(r"\s+", " ", s)
        steps.append(s)
    label = glyph if glyph else title
    question = f"Which statement correctly describes {label}?"
    if not steps:
        steps = [f"{title} is a Biblical Hebrew concept."]
    # Avoid a degenerate "See the explanation above" answer — summarize.
    first = steps[0] if steps else ""
    m = re.search(r"((?:means|is|uses|has|marks|forms?|pattern)[^.\n]{5,80})", first, re.I)
    answer = (m.group(1).strip() if m else first)[:160] or title
    return {
        "question": question,
        "steps": steps,
        "answer": answer,
    }


def _is_degenerate(we) -> bool:
    if not isinstance(we, list) or not we:
        return False
    for x in we:
        if not isinstance(x, dict):
            return False
        q = str(x.get("question", ""))
        a = str(x.get("answer", ""))
        if "explanation above" in a.lower() or DEGENERATE_QUESTION.match(q):
            return True
    return False


def _is_generic_kp(kp) -> bool:
    if not isinstance(kp, list) or not kp:
        return False
    return any(GENERIC_KEYPOINT.search(str(k)) for k in kp)


def main():
    parser = argparse.ArgumentParser(description="Replace degenerate worked examples and generic key points")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to apply")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT n.id, n.title, l.content_json
        FROM hebrew_lessons l JOIN hebrew_nodes n ON n.id = l.node_id
    """).fetchall()

    # node_id -> glyph from title
    def glyph_of(title):
        for p in reversed(re.findall(r"\(([^)]+)\)", title or "")):
            if any("\u0590" <= ch <= "\u05FF" for ch in p):
                return p
        return ""

    to_fix = []
    for r in rows:
        try:
            d = json.loads(r["content_json"])
        except (json.JSONDecodeError, TypeError):
            continue
        expl = d.get("explanation") or ""
        we = d.get("worked_examples")
        kp = d.get("key_points")
        we_bad = _is_degenerate(we)
        kp_bad = _is_generic_kp(kp)
        if not we_bad and not kp_bad:
            continue
        new = dict(d)
        if we_bad:
            new["worked_examples"] = [_worked_example_from_explanation(expl, r["title"], glyph_of(r["title"]))]
        if kp_bad:
            new["key_points"] = _key_points_from_explanation(expl) or ["Review the explanation above"]
        to_fix.append((r["id"], json.dumps(new, ensure_ascii=False),
                       we_bad and "we", kp_bad and "kp"))

    print(f"Lessons with degenerate content: {len(to_fix)}")
    if args.dry_run:
        for nid, blob, we, kp in to_fix[:8]:
            d = json.loads(blob)
            print(f"  [{nid}] {'we ' if we else ''}{'kp ' if kp else ''}")
            print(f"    key_points: {d['key_points']}")
            print(f"    worked_examples: {json.dumps(d['worked_examples'], ensure_ascii=False)[:180]}")
        conn.close()
        return

    cur = conn.cursor()
    for nid, blob, we, kp in to_fix:
        cur.execute(
            "UPDATE hebrew_lessons SET content_json=?, version=COALESCE(version,0)+1, updated_at=datetime('now') WHERE node_id=?",
            (blob, nid))
    conn.commit()
    print(f"  ✅ Regenerated content for {len(to_fix)} lessons")

    # Verify: recount degenerates
    still = 0
    for r in conn.execute("SELECT node_id, content_json FROM hebrew_lessons"):
        try: d = json.loads(r["content_json"])
        except (json.JSONDecodeError, TypeError): continue
        if _is_degenerate(d.get("worked_examples")) or _is_generic_kp(d.get("key_points")):
            still += 1
    print(f"  lessons still degenerate: {still}")
    conn.close()


if __name__ == "__main__":
    main()
