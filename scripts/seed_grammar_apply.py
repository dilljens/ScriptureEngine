#!/usr/bin/env python3
"""Seed grammar-application cards (active-recall R2).

Recognition (MC "which statement describes X?") tests rule memory;
application tests rule USE. Two item shapes, both mined from attested
lesson content — never composed, never invented:

A. Produce/inflect (typing):  "Add 'our' (־נוּ) to דָּבָר" → דְּבָרֵנוּ.
   Sources: "Example: BASE → FORM (gloss)" lines and bare BASE → FORM
   pairs in suffix/prefix lesson explanations + worked examples.
B. Break down (parse): "Break לָהֶם into parts" → "ל הם to them".
   Sources: "Parse 'X'" worked examples whose steps are "PART = gloss"
   lines plus a full-form final step. The keyword grader requires every
   token (both Hebrew parts AND the gloss words), so neither half alone
   passes.

Both ride existing paths (typing/parse grading, lesson + cumulative
quizzes, FSRS '' rows). Idempotent via same-answer skip.

Usage:
    python3 scripts/seed_grammar_apply.py --dry-run
    python3 scripts/seed_grammar_apply.py --apply
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEM_DB = BASE / "data" / "memorize.db"

HEB = r"[֐-׿]"
ARROW_PAT = re.compile(r"([֐-׿/]{2,})(?:\s*\([^)]{1,60}\))?\s*[→⇒]\s*([֐-׿/]{2,})(?:\s*\(([^)]{1,60})\))?")


def _heb_only(s: str) -> str:
    return re.sub(rf"[^{HEB[1:-1]}]", "", s or "")


def _gloss_head(g: str) -> str:
    g = re.sub(r"\(.*?\)", "", g or "").strip()
    return g.split("/")[0].strip()


def type_a_from_text(nid: str, text: str):
    """(base, form, gloss) triples from complete worked examples only.

    Accepts 'BASE → FORM (gloss)' example lines and 'STEM + affix → FORM'
    compositions (base = the stem). Rejects sound-description lines
    (begadkefat), stem fragments, and gloss-less pairs — except the single
    attested jussive-shortening pair, whose gloss lives in the lesson rule.
    """
    out = []
    for line in (text or "").split("\n"):
        if "sound" in line:
            continue
        # 'STEM + affix → FORM': the affix is this lesson's own topic.
        had_plus = "+" in line.split("→")[0].split("⇒")[0] if ("→" in line or "⇒" in line) else False
        line = re.sub(r"([֐-׿/]+)\s*\+\s*[֐-׿/]+\s*(?=[→⇒])", r"\1 ", line)
        for base, form, gloss in ARROW_PAT.findall(line):
            base, form = _heb_only(base), _heb_only(form)
            if "/" in base or len(base) < 3 or len(form) < 3:
                continue
            gloss = (gloss or "").strip()
            ok_line = (("Example" in line) or had_plus or ("shortening" in line)
                       or re.search(r"\([^)]{1,12}\):\s*[֐-׿]", line))
            if not ok_line:
                continue
            if not gloss and nid != "commands_jussive":
                continue
            out.append((base, form, gloss))
    # Batch dedup (worked examples repeat explanation lines).
    seen, uniq = set(), []
    for triple in out:
        if triple not in seen:
            seen.add(triple)
            uniq.append(triple)
    return uniq


# Type B is morphological only: breaking a SENTENCE into words restates it
# (no discrimination); breaking a FORM into morphemes tests the rule.
BREAKDOWN_NODES = {
    "prepositions_with_suffixes", "pronominal_suffixes_nouns",
    "object_suffixes_verbs", "infinitive_construct",
    "prefix_bet", "prefix_lamed", "prefix_mem", "prefix_kaf",
    "suffix_pron_1s", "suffix_pron_2ms", "suffix_pron_3ms",
    "suffix_pron_1p", "suffix_plural_m", "suffix_plural_f",
}


def type_b_from_worked(nid: str, we) -> list:
    """Parse-style breakdowns from 'Parse X' worked examples.

    Returns [(surface, [part...], full_gloss)]. The final full-form step
    is the whole, never a part. Only morphological nodes qualify.
    """
    if nid not in BREAKDOWN_NODES:
        return []
    out = []
    for ex in we or []:
        q = ex.get("question", "")
        m = re.match(r"""\s*Parse\s+['"“](.+?)['"”]""", q)
        if not m:
            continue
        surface = m.group(1).strip()
        steps = ex.get("steps") or []
        if len(steps) < 2:
            continue
        parts = []
        for st in steps[:-1]:
            pm = re.match(r"\s*([^=]{1,30}?)\s*=\s*(.+)", st)
            if not pm:
                continue
            lhs, rhs = pm.group(1).strip(), pm.group(2).strip()
            if _heb_only(lhs):
                parts.append((_heb_only(lhs), _gloss_head(rhs)))
        last = steps[-1]
        if len(parts) >= 2 and ("=" in last and
                                (_heb_only(surface) in _heb_only(last) or
                                 _heb_only(last) in _heb_only(surface))):
            full = _gloss_head(last.split("=", 1)[1])
            out.append((surface, parts, full))
    return out


APPLY_NODES = None  # None = all grammar-ish nodes with attested pairs


def collect(conn):
    q = ("SELECT n.id FROM hebrew_nodes n WHERE n.category IN ('grammar','syntax')"
         " OR n.id LIKE 'prefix_%' OR n.id LIKE 'suffix_%'"
         " OR n.id IN ('prepositions_with_suffixes','pronominal_suffixes_nouns',"
         " 'object_suffixes_verbs','infinitive_construct','infinitive_absolute')"
         " ORDER BY n.id")
    type_a, type_b = [], []
    for (nid,) in conn.execute(q):
        if APPLY_NODES and nid not in APPLY_NODES:
            continue
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                           (nid,)).fetchone()
        if not row:
            continue
        try:
            c = json.loads(row[0] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        text = (c.get("explanation") or "") + "\n" + json.dumps(
            c.get("worked_examples") or [], ensure_ascii=False)
        for base, form, gloss in type_a_from_text(nid, text):
            hint = f" ('{gloss}')" if gloss else ""
            type_a.append({
                "node_id": nid,
                "question_type": "typing",
                "question_text": f"Apply this lesson to {base}{hint} — write the full form.",
                "options_json": json.dumps([], ensure_ascii=False),
                "correct_answer": form,
                "difficulty": 0.75,
                "explanation": f"{base} → {form}{hint} — see the {nid} lesson.",
            })
        for surface, parts, full in type_b_from_worked(nid, c.get("worked_examples")):
            hebs = " ".join(p[0] for p in parts)
            glosses = " ".join(p[1] for p in parts if p[1])
            answer = f"{hebs} {full or glosses}".strip()
            if len(hebs) < 2:
                continue
            type_b.append({
                "node_id": nid,
                "question_type": "parse",
                "question_text": f"Break {surface} into its parts (name each part and the whole).",
                "options_json": json.dumps([], ensure_ascii=False),
                "correct_answer": answer,
                "difficulty": 0.7,
                "explanation": f"{surface} = {answer} — see the {nid} lesson.",
            })
    return type_a, type_b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    fresh = []
    for it in (*collect(conn)[0], *collect(conn)[1]):
        dup = conn.execute(
            """SELECT 1 FROM hebrew_practice_items
               WHERE node_id=? AND question_type=? AND correct_answer=?""",
            (it["node_id"], it["question_type"], it["correct_answer"])).fetchone()
        if not dup:
            fresh.append(it)
    print(f"new grammar-application cards: {len(fresh)}")
    if not args.apply:
        for it in fresh[:8]:
            print(f"  [{it['question_type']}] {it['node_id']}: {it['question_text'][:70]} → {it['correct_answer']}")
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
    print(f"inserted {len(fresh)} grammar-application cards")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
