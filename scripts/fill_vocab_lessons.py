#!/usr/bin/env python3
"""Fill instructional content for vocabulary lessons missing teaching material.

Math Academy Way review finding: 517 of 535 vocab lessons were metadata shells
(gloss, Hebrew, frequency, verse reference) with NO explanation, key_points, or
worked_examples — violating direct instruction and the worked-example effect.

This script generates, from the existing verified metadata (gloss, root,
description, verse example), a complete lesson body for every vocab node that
lacks one:
  - explanation   — prose built from the (already verified) description + gloss
  - key_points    — 3-5 bullet facts
  - worked_examples — 1-2 stepped examples grounded in the real OT verse

It never overwrites existing content, and only touches hebrew_lessons.

Usage:
    python3 scripts/fill_vocab_lessons.py --dry-run
    python3 scripts/fill_vocab_lessons.py --apply
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

HEB = re.compile(r"[\u0590-\u05FF]")

# Description prefixes that indicate a raw Strong's-dump rather than prose
RAW_DUMP = re.compile(r"^(\d+[a-z]?\)|adv;|conj;|n m;|n f;|prep;|interr|interj)")


def _strip_strongs_numbers(desc: str) -> str:
    """Strip leading '1)', '1a)', '1a1)' style Strong's numbering."""
    return re.sub(r"(?:^|\s)\d+[a-z]*(?:\)|;)", " ", desc).strip()


def _clean_desc(desc: str) -> str:
    """Return a usable prose description, or '' if it's a raw dump."""
    if not desc:
        return ""
    if RAW_DUMP.match(desc.strip()):
        return ""
    # Collapse whitespace, cap length
    desc = re.sub(r"\s+", " ", desc).strip()
    return desc[:900]


def build_lesson_content(node: dict, verse: dict) -> dict:
    """Generate explanation / key_points / worked_examples for one lesson node.

    node: row from hebrew_nodes joined with hebrew_lessons metadata.
    verse: the verse row (hebrew + english) for node['verse_example'], or None.
    """
    hebrew = node.get("hebrew") or ""
    gloss = (node.get("gloss") or "").strip()
    root = (node.get("root") or "").strip()
    translit = (node.get("transliteration") or "").strip()
    strongs = (node.get("strongs_id") or "").strip()
    desc = _clean_desc(node.get("description") or "")
    vref = node.get("verse_example") or ""
    vheb = (verse or {}).get("text_hebrew") or node.get("verse_hebrew") or ""
    veng = (verse or {}).get("text_english") or node.get("verse_english") or ""
    token = node.get("example_token_surface") or ""

    # Phrase lessons carry their content in key_points; derive worked examples
    # from the key points when no verse is attached.
    existing_kp = node.get("key_points") or []

    # ── explanation ──
    parts = []
    if desc:
        parts.append(desc)
    else:
        # Fallback prose from gloss + strongs + root
        g = gloss or "this word"
        if translit:
            parts.append(f"{hebrew} (transliterated {translit}) means '{g}'.")
        elif gloss:
            parts.append(f"{hebrew} means '{g}'.")
        if strongs:
            parts.append(f"It is Strong's {strongs}.")
        if root and root != hebrew:
            parts.append(f"The root is {root}.")
    if vref and veng:
        # Attach a short authentic example
        excerpt = veng[:180].rstrip()
        parts.append(f"In {vref}: \u201c{excerpt}\u2026\u201d")
    explanation = " ".join(parts)

    # ── key_points ──
    kp = []
    g = gloss or "—"
    if hebrew or gloss:
        if translit:
            kp.append(f"{hebrew} ({translit}) = {g}")
        else:
            kp.append(f"{hebrew} = {g}")
    if strongs:
        kp.append(f"Strong's {strongs}")
    if root:
        kp.append(f"Root: {root}")
    if desc:
        # Extract a usage sentence: split off "Used for:" / "Used to:" clauses
        m = re.search(r"Used (?:for|to):(.+)", desc, re.I)
        if m:
            usage = m.group(1).strip().split(".")[0][:160]
            if usage:
                kp.append(f"Uses: {usage}")
    if vref:
        kp.append(f"Example: {vref}")
    kp = (kp + list(existing_kp))[:5] or list(existing_kp)[:5]

    # ── worked_examples ──
    worked = []
    if vref and vheb:
        # Step 1: show the verse with the token (the lesson view renders the
        # verse; the token itself is the target word being learned).
        step1 = f"Read {vref}: {vheb}"
        if token and token in vheb:
            step1 = f"Read {vref}: \u2026{token}\u2026 (this is the word {hebrew})"
        step2 = f"The word {token or hebrew} means '{g}' here."
        step3 = f"English: {veng[:160].rstrip()}\u2026"
        worked.append({
            "question": f"What does {hebrew} mean in {vref}?",
            "steps": [step1, step2, step3],
            "answer": g,
        })
    if not worked and existing_kp:
        # Derive a worked example from the phrase's key points (no verse needed)
        head = existing_kp[0] if existing_kp else (hebrew or "this phrase")
        phrase_label = node.get("title") or hebrew or "this phrase"
        worked.append({
            "question": f"What does {phrase_label} mean?",
            "steps": [head] + [kp for kp in existing_kp[1:3]],
            "answer": gloss or head,
        })
    if not worked:
        worked.append({
            "question": f"What does {hebrew} mean?",
            "steps": [f"{hebrew} ({translit}) is a common Biblical Hebrew word.",
                      f"Its gloss is '{g}'."],
            "answer": g,
        })

    return {
        "explanation": explanation,
        "key_points": kp,
        "worked_examples": worked,
    }


def main():
    parser = argparse.ArgumentParser(description="Fill missing vocab lesson content")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument("--apply", action="store_true", help="Apply to database")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to apply")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    # Lessons missing a substantive explanation OR worked examples — covers the
    # vocab word category plus phrase/root/reading lessons that had content but
    # no worked examples.
    rows = conn.execute("""
        SELECT n.id, n.title, n.description, n.category,
               l.content_json,
               json_extract(l.content_json, '$.gloss') AS gloss,
               json_extract(l.content_json, '$.hebrew') AS hebrew,
               json_extract(l.content_json, '$.root') AS root,
               json_extract(l.content_json, '$.transliteration') AS transliteration,
               json_extract(l.content_json, '$.strongs_id') AS strongs_id,
               json_extract(l.content_json, '$.verse_example') AS verse_example,
               json_extract(l.content_json, '$.verse_hebrew') AS verse_hebrew,
               json_extract(l.content_json, '$.verse_english') AS verse_english,
               json_extract(l.content_json, '$.example_token_surface') AS example_token_surface,
               json_extract(l.content_json, '$.key_points') AS key_points,
               json_extract(l.content_json, '$.explanation') AS explanation
        FROM hebrew_nodes n
        JOIN hebrew_lessons l ON l.node_id = n.id
        WHERE (json_extract(l.content_json, '$.explanation') IS NULL
               OR length(json_extract(l.content_json, '$.explanation')) < 80
               OR COALESCE(json_array_length(json_extract(l.content_json, '$.worked_examples')), 0) = 0)
    """).fetchall()

    print(f"Found {len(rows)} lessons missing explanation or worked examples")

    to_fix = []
    for r in rows:
        node = dict(r)
        # key_points arrive as a JSON string from json_extract; normalize
        try:
            kp = json.loads(node.get("key_points")) if node.get("key_points") else []
        except (json.JSONDecodeError, TypeError):
            kp = []
        node["key_points"] = kp
        # Verse text is embedded in the lesson content_json (verse_hebrew /
        # verse_english) — no cross-DB lookup needed.
        verse = {
            "text_hebrew": node.get("verse_hebrew") or "",
            "text_english": node.get("verse_english") or "",
        }
        new_content = build_lesson_content(node, verse)
        # Merge: keep existing keys, add/fill the three teaching fields
        try:
            existing = json.loads(r["content_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            existing = {}
        # Preserve an existing substantive explanation (phrase/reading lessons
        # already have hand-written ones); fill the missing pieces. Keep
        # existing key_points unless the lesson had none.
        if not existing.get("explanation") or len(existing.get("explanation", "")) < 80:
            existing["explanation"] = new_content["explanation"]
        if not existing.get("key_points"):
            existing["key_points"] = new_content["key_points"]
        if not existing.get("worked_examples"):
            existing["worked_examples"] = new_content["worked_examples"]
        to_fix.append((r["id"], json.dumps(existing, ensure_ascii=False)))

    if args.dry_run:
        for nid, blob in to_fix[:6]:
            d = json.loads(blob)
            print(f"\n  [{nid}]")
            print(f"    explanation: {d['explanation'][:110]}\u2026")
            print(f"    key_points: {d['key_points']}")
            print(f"    worked_examples: {json.dumps(d['worked_examples'], ensure_ascii=False)[:150]}")
        print(f"\n  → {len(to_fix)} lessons to fill. Run with --apply to write.")
        conn.close()
        return

    cur = conn.cursor()
    for nid, blob in to_fix:
        cur.execute(
            """UPDATE hebrew_lessons
               SET content_json=?, version=COALESCE(version,0)+1, updated_at=datetime('now')
               WHERE node_id=?""",
            (blob, nid),
        )
    conn.commit()
    print(f"  ✅ Filled instructional content for {len(to_fix)} vocab lessons")

    # Verify
    missing = conn.execute("""
        SELECT COUNT(*) FROM hebrew_lessons
        WHERE json_extract(content_json, '$.explanation') IS NULL
           OR length(json_extract(content_json, '$.explanation')) < 80
           OR COALESCE(json_array_length(json_extract(content_json, '$.worked_examples')), 0) = 0
    """).fetchone()[0]
    print(f"  lessons still missing explanation or worked examples: {missing}")
    conn.close()


if __name__ == "__main__":
    main()
