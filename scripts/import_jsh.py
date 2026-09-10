#!/usr/bin/env python3
"""Backfill Joseph Smith—History chapter 1 into the scripture DB.

Background: scripts/ingest.py::ingest_pgp_flat splits references on the first
space, so multi-word PGP books ("Joseph Smith—History", "Joseph Smith—Matthew",
"Articles of Faith") were skipped as "Unknown PGP book" — jsh/jsm/aoff have
zero verses even though their book rows exist. This script imports JSH ch.1
from data/jsh_chapter1.json (verbatim from churchofjesuschrist.org).

Uses lib.db.insert_verse (idempotent upsert) and mirrors rows into verses_fts
so JSH is searchable like the rest of the canon. Safe to re-run.

Usage: python3 scripts/import_jsh.py [db_path]
"""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.db import insert_verse  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_DB = DATA_DIR / "processed" / "scripture.db"
SOURCE = DATA_DIR / "jsh_chapter1.json"


def main(db_path: str = str(DEFAULT_DB)) -> int:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    book, chapter = data["book"], data["chapter"]
    verses = data["verses"]
    nums = sorted(v["verse"] for v in verses)
    assert nums == list(range(1, len(verses) + 1)), "verse numbers must be 1..N contiguous"

    conn = sqlite3.connect(db_path)
    try:
        has_book = conn.execute("SELECT 1 FROM books WHERE id=?", (book,)).fetchone()
        if not has_book:
            print(f"book row '{book}' missing — run scripts/ingest.py build_books first")
            return 1
        for v in verses:
            text = (v["text"] or "").strip()
            if not text:
                print(f"  WARNING: empty text for {book}.{chapter}.{v['verse']}")
                continue
            insert_verse(conn, book, chapter, v["verse"], text)
            vid = f"{book}.{chapter}.{v['verse']}"
            conn.execute("DELETE FROM verses_fts WHERE verse_id=?", (vid,))
            conn.execute(
                "INSERT INTO verses_fts (verse_id, book_id, text_english, text_hebrew, text_greek)"
                " VALUES (?, ?, ?, '', '')",
                (vid, book, text),
            )
        conn.commit()
    finally:
        conn.close()
    print(f"  Joseph Smith—History ch.{chapter}: {len(verses)} verses")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_DB)))
