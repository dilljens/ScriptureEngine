#!/usr/bin/env python3
"""Rebuild lexicon frequency fields from exact lemma aggregates.

The legacy lexicon conflates prefixed raw forms (c/b/3605, l/3605, ...) with the
canonical base, so lexicon.frequency understates true OT usage. This recomputes,
per canonical Strong's base, the exact OT token and verse counts and writes them
back to every lexicon row sharing that base (raw, prefixed, and H/G rows).
Definitions, glosses, and other curated fields are never touched.
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"


def canonical_base(lemma: str) -> str:
    """Reduce a raw lexicon/gematria lemma to its numeric Strong's base."""
    lexical = (lemma or "").strip().split("/")[-1].strip()
    lexical = re.sub(r"^[HG](?=\d)", "", lexical)
    match = re.match(r"(\d+)", lexical)
    return match.group(1) if match else ""


def compute_counts(conn) -> dict[str, dict]:
    tokens = {}
    for lemma, verse_id, book_id in conn.execute("""
        SELECT g.lemma, g.verse_id, b.id
        FROM gematria g
        JOIN verses v ON v.id=g.verse_id
        JOIN books b ON b.id=v.book_id
        WHERE b.work_id='ot'
    """):
        base_key = canonical_base(lemma)
        if not base_key or not base_key.isdigit():
            continue
        entry = tokens.setdefault(base_key, {"tokens": 0, "verses": set(), "books": {}})
        entry["tokens"] += 1
        entry["verses"].add(verse_id)
        entry["books"][book_id] = entry["books"].get(book_id, 0) + 1
    return tokens


def rebuild(scripture_db: Path) -> dict:
    conn = sqlite3.connect(scripture_db)
    counts = compute_counts(conn)
    updated = 0
    for lemma, in conn.execute("SELECT lemma FROM lexicon"):
        base_key = canonical_base(lemma)
        if not base_key or base_key not in counts:
            continue
        entry = counts[base_key]
        frequency = entry["tokens"]
        per_book = json.dumps({k: v for k, v in sorted(entry["books"].items())}, ensure_ascii=False)
        books_list = ",".join(sorted(entry["books"]))
        conn.execute(
            "UPDATE lexicon SET frequency=?, frequency_per_book=?, books_list=? WHERE lemma=?",
            (frequency, per_book, books_list, lemma),
        )
        updated += 1
        # Keep the derived gloss table in sync too.
        conn.execute(
            "UPDATE lemma_gloss SET frequency=? WHERE lemma=? AND frequency<?",
            (frequency, lemma, frequency),
        )
    conn.commit()
    conn.close()
    return {"canonical_bases": len(counts), "lexicon_rows_updated": updated}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scripture-db", type=Path, default=SCRIPTURE_DB)
    args = parser.parse_args()
    result = rebuild(args.scripture_db)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
