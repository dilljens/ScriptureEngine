#!/usr/bin/env python3
"""Seed prefix-application cards from attested corpus tokens (content fill).

For transparent prefixes (bet=in, kaf=like/as, lamed=to/for, mem=from,
he=the) the gloss is compositional: prefix-gloss + stem-gloss. The FORM,
however, is never composed — it must be an exact OSHB token, so learners
never see hand-pointed Hebrew. Each card: "Add 'to/for' (ל) to מלך" →
לַמֶּלֶךְ (attested), with the citation form as prompt and the real
inflected token as answer (that's the rule being tested).

Skipped deliberately: vav (wayyiqtol changes tense/aspect — not
compositional), shin (relative "which X" rarely stands alone as a vocab
gloss), gutturals-driven vowel shifts are FINE because the form is
attested, not predicted.

Idempotent (same-answer skip). Requires the processed scripture DB.

Usage:
    python3 scripts/seed_prefix_apply.py --dry-run [--count 4]
    python3 scripts/seed_prefix_apply.py --apply [--count 4]
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"
sys.path.insert(0, str(BASE / "scripts"))
from generate_sentence_cloze import normalize_final, strip_niqqud  # noqa: E402

PREFIXES = {
    "prefix_bet": ("ב", "in/with/by"),
    "prefix_kaf": ("כ", "like/as"),
    "prefix_lamed": ("ל", "to/for"),
    "prefix_mem": ("מ", "from"),
    "prefix_he": ("ה", "the"),
}

# Tanakh only: DSS/apocryphal Hebrew (unpointed, different layer) must not
# source pointed-Hebrew pronunciation cards. Lowercase ids match verses.book_id.
OT_BOOKS = {"gen", "exo", "lev", "num", "deu", "josh", "judg", "ruth",
             "1sam", "2sam", "1kgs", "2kgs", "1chr", "2chr", "ezra",
             "neh", "esth", "job", "psa", "prov", "eccl", "song",
             "isa", "jer", "lam", "ezek", "dan", "hos", "joel",
             "amos", "obad", "jonah", "mic", "nah", "hab", "zeph",
             "hag", "zech", "mal"}

# Coincidental miqtal-pattern nouns (own lexemes, not prefix+stem).
# Caught by reviewer eyeball; the lexicon lacks these headwords so the
# headword test can't see them.
DENY_SURFACES = {"מזבח"}


def _bare(tok: str) -> str:
    return normalize_final(strip_niqqud(tok.replace("/", "")))


def _is_headword(scrip, bare: str) -> bool:
    """Lexicalized on its own (own gloss) => not a transparent prefixation."""
    try:
        return scrip.execute("SELECT 1 FROM lexicon WHERE hebrew_plain=? LIMIT 1",
                             (bare,)).fetchone() is not None
    except Exception:
        return False


def collect(conn, scrip, per_node: int):
    # Citation surfaces of top vocab, for stem matching.
    stems = {}
    for node_id, cj in conn.execute(
            "SELECT node_id, content_json FROM hebrew_lessons WHERE node_id LIKE 'vocab\\_%' ESCAPE '\\'"):
        try:
            c = json.loads(cj or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        hw = (c.get("hebrew") or "").strip()
        if hw:
            stems[_bare(hw)] = (node_id, c.get("gloss", "").strip(), hw)
    try:
        placeholders = ",".join("?" for _ in OT_BOOKS)
        verses = scrip.execute(
            f"SELECT text_hebrew FROM verses WHERE book_id IN ({placeholders})",
            tuple(sorted(OT_BOOKS))).fetchall()
    except Exception as exc:
        print(f"scripture read failed: {exc}", file=sys.stderr)
        return []
    # Count bare corpus tokens per (prefix, stem).
    hits: dict = {}
    for (heb,) in verses:
        for chunk in (heb or "").split():
            tok = chunk.replace("/", "")
            bare = _bare(tok)
            if len(bare) < 3:
                continue
            for nid, (ph, _gloss) in PREFIXES.items():
                pb = _bare(ph)
                if bare.startswith(pb) and len(bare) > len(pb) + 1:
                    stem = bare[len(pb):]
                    if stem in stems and not _is_headword(scrip, bare):
                        key = (nid, stems[stem][0], stems[stem][2], tok)
                        hits[key] = hits.get(key, 0) + 1
    # Top `per_node` distinct surfaces per lesson (corpus frequency = natural).
    by_node: dict = {}
    for (nid, _stem_nid, stem_hw, tok), n in sorted(hits.items(), key=lambda kv: -kv[1]):
        if normalize_final(strip_niqqud(tok)) in DENY_SURFACES:
            continue
        cur = by_node.setdefault(nid, [])
        if len(cur) < per_node and tok not in [t for _, t in cur]:
            cur.append((stem_hw, tok))
    items = []
    for nid, pairs in by_node.items():
        ph, pgloss = PREFIXES[nid]
        for stem_hw, tok in pairs:
            items.append({
                "node_id": nid,
                "question_type": "typing",
                "question_text": f"Add '{pgloss}' ({ph}) to {stem_hw} — write the full form as it appears in the text.",
                "options_json": json.dumps([], ensure_ascii=False),
                "correct_answer": tok,
                "difficulty": 0.7,
                "explanation": f"{tok} = {ph} + {stem_hw} ('{pgloss} …') — attested OSHB token.",
            })
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=4)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not MEM_DB.exists():
        print(f"missing {MEM_DB}", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(MEM_DB))
    scrip = sqlite3.connect(str(SCRIPTURE_DB))
    from generate_sentence_cloze import normalize_final as _nf, strip_niqqud as _sn
    seen = set()
    fresh = []
    for it in collect(conn, scrip, args.count):
        key = (it["node_id"], it["question_type"], _nf(_sn(it["correct_answer"])))
        if key in seen:
            continue
        seen.add(key)
        # DB-side dedup on skeletons: same word, different cantillation
        # marks in the corpus must not seed duplicate cards across runs.
        skel = _nf(_sn(it["correct_answer"]))
        have = {normalize_final(strip_niqqud(r[0] or "")) for (r,) in
                conn.execute(
                    """SELECT correct_answer FROM hebrew_practice_items
                       WHERE node_id=? AND question_type='typing'""",
                    (it["node_id"],)).fetchall()}
        if skel not in have:
            fresh.append(it)
    print(f"new prefix-application cards: {len(fresh)}")
    if not args.apply:
        for it in fresh[:8]:
            print(f"  {it['node_id']}: {it['question_text'][:60]} → {it['correct_answer']}")
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
    print(f"inserted {len(fresh)} prefix-application cards")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
