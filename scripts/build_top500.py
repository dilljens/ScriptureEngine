#!/usr/bin/env python3
"""Build the top-500 words + top-500 roots dataset for Hebrew learning.

Reads lexicon frequencies (the only populated frequency source), cleans
 pointed forms, derives SBL transliteration + short glosses, and writes
 data/top500.json. Deterministic — rerun any time; diff to review drift.

Usage: python3 scripts/build_top500.py [--limit N] [--out data/top500.json]
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lib.hebrew_util import clean_hebrew, strip_cantillation, strip_vowels, transliterate  # noqa: E402

WORDS = 500
ROOTS = 500


def gloss_of(definition):
    """First clause before an em-dash/period — short, stable, flagged derived."""
    if not definition:
        return ""
    head = definition.split("—")[0].split(".")[0].strip()
    head = re.sub(r"\s+", " ", head)
    return head[:80]


def bare(hebrew):
    """Bare consonants for matching (no vowels, accents, or separators)."""
    return strip_vowels(strip_cantillation(clean_hebrew(hebrew or "")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=WORDS)
    ap.add_argument("--roots", type=int, default=ROOTS)
    ap.add_argument("--out", default="data/top500.json")
    ap.add_argument("--db", default="data/processed/scripture.db")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT lemma, hebrew, transliteration, part_of_speech, root_letters,"
        " definition, frequency FROM lexicon WHERE frequency > 0"
        " ORDER BY frequency DESC LIMIT ?",
        (args.limit,),
    ).fetchall()
    conn.close()

    words = []
    for rank, r in enumerate(rows, 1):
        pointed = strip_cantillation(clean_hebrew(r["hebrew"] or ""))
        words.append({
            "rank": rank,
            "lemma": r["lemma"],
            "hebrew": pointed,
            "bare": bare(r["hebrew"] or ""),
            "transliteration": r["transliteration"] or transliterate(r["hebrew"] or ""),
            "gloss": gloss_of(r["definition"]),
            "gloss_derived": True,
            "root": bare(r["root_letters"] or ""),
            "pos": r["part_of_speech"] or "",
            "frequency": r["frequency"],
        })

    # Roots: sum lemma frequencies per bare root, keep top examples.
    by_root = {}
    for w in words:
        if not w["root"]:
            continue
        b = by_root.setdefault(w["root"], {"total": 0, "words": []})
        # NOTE: frequencies here cover only the top-N word sample by default.
        b["total"] += w["frequency"]
        b["words"].append(w)
    # Full-corpus root totals (not just the word sample).
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    all_roots = conn.execute(
        "SELECT root_letters, SUM(frequency) AS total, COUNT(*) AS n"
        " FROM lexicon WHERE root_letters <> '' AND frequency > 0"
        " GROUP BY root_letters ORDER BY total DESC LIMIT ?",
        (args.roots,),
    ).fetchall()
    conn.close()
    by_lemma = {w["lemma"]: w for w in words}
    roots = []
    for rank, r in enumerate(all_roots, 1):
        root = bare(r["root_letters"])
        examples = sorted(
            (w for w in words if w["root"] == root),
            key=lambda w: -w["frequency"],
        )[:3]
        roots.append({
            "rank": rank,
            "root": root,
            "total_frequency": r["total"],
            "word_count": r["n"],
            "gloss": (examples[0]["gloss"] if examples else ""),
            "gloss_derived": True,
            "examples": [e["lemma"] for e in examples],
        })

    out = {
        "words": words,
        "roots": roots,
        "meta": {"word_n": len(words), "root_n": len(roots), "source": "lexicon frequencies"},
    }
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}: {len(words)} words, {len(roots)} roots")
    empties = sum(1 for w in words if not w["transliteration"]) + sum(1 for w in words if not w["gloss"])
    print(f"words missing translit-or-gloss: {empties}")


if __name__ == "__main__":
    main()
