#!/usr/bin/env python3
"""Import JST text as a Bible version in text_resources.

Stores JST verse text in text_resources with version='JST',
parallel to existing KJV, LSV, WEB etc.

Source: awerkamp markdown repo at /tmp/jst-markdown.
Also creates a JST↔KJV diff index.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db

REPO = "/tmp/jst-markdown"

BOOK_NAME_TO_ID = {
    "Genesis": "gen", "Exodus": "exo", "Leviticus": "lev", "Numbers": "num",
    "Deuteronomy": "deu", "Joshua": "josh", "Judges": "judg", "Ruth": "ruth",
    "1Samuel": "1sam", "2Samuel": "2sam", "1Kings": "1kgs", "2Kings": "2kgs",
    "1Chronicles": "1chr", "2Chronicles": "2chr", "Ezra": "ezra", "Nehemiah": "neh",
    "Esther": "esth", "Job": "job", "Psalms": "psa", "Proverbs": "prov",
    "Ecclesiastes": "eccl", "Song of Solomon": "song",
    "Isaiah": "isa", "Jeremiah": "jer", "Lamentations": "lam", "Ezekiel": "ezek",
    "Daniel": "dan", "Hosea": "hos", "Joel": "joel", "Amos": "amos",
    "Obadiah": "obad", "Jonah": "jonah", "Micah": "mic", "Nahum": "nah",
    "Habakkuk": "hab", "Zephaniah": "zeph", "Haggai": "hag", "Zechariah": "zech",
    "Malachi": "mal",
    "Matthew": "matt", "Mark": "mark", "Luke": "luke", "John": "john",
    "Acts": "acts", "Romans": "rom", "1Corinthians": "1cor", "2Corinthians": "2cor",
    "Galatians": "gal", "Ephesians": "eph", "Philippians": "phil",
    "Colossians": "col", "1Thessalonians": "1thes", "2Thessalonians": "2thes",
    "1Timothy": "1tim", "2Timothy": "2tim", "Titus": "titus", "Philemon": "philem",
    "Hebrews": "heb", "James": "james", "1Peter": "1pet", "2Peter": "2pet",
    "1John": "1john", "2John": "2john", "3John": "3john", "Jude": "jude",
    "Revelation": "rev",
}

EXCLUDED_BOOKS = {"song", "Song of Solomon"}  # JST doesn't include Song of Solomon

def parse_all_books(base_dir):
    """Parse all markdown files in a directory tree.
    Both KJV and JST use: 01 Genesis/Genesis1.md format.
    Returns: {book_id: {chapter: {verse: text}}}
    """
    result = {}
    for root, _dirs, files in os.walk(base_dir):
        # Get book name from directory name (e.g., "01 Genesis")
        dir_name = os.path.basename(root)
        book_name = re.sub(r'^\d+\s+', '', dir_name) if re.match(r'^\d+\s+', dir_name) else dir_name

        for fname in sorted(files):
            if not fname.endswith(".md"):
                continue
            # Filename like "Genesis1.md" or "SongofSolomon1.md"
            stem = fname[:-3]
            # Extract chapter number from end
            ch_match = re.match(r'.*?(\d+)$', stem)
            if not ch_match:
                continue
            ch = int(ch_match.group(1))

            bid = BOOK_NAME_TO_ID.get(book_name)
            if not bid:
                # Try alternative capitalization
                for key, val in BOOK_NAME_TO_ID.items():
                    if key.lower() == book_name.lower():
                        bid = val
                        break
            if not bid:
                continue

            if bid in EXCLUDED_BOOKS:
                continue

            with open(os.path.join(root, fname), encoding='utf-8') as f:
                content = f.read()

            # Parse markdown: ## N. for verse N, followed by text on same or next line
            # The chapter IS the file (Genesis1.md = chapter 1)
            ch = int(Path(fname).stem.rstrip('0123456789').removeprefix(book_name) or 0)
            try:
                ch = int(re.search(r'(\d+)$', fname[:-3]).group(1))
            except (ValueError, AttributeError):
                continue

            verses = {}
            current_vs = None
            current_text = ''

            for line in content.split('\n'):
                line = line.strip()
                if not line:
                    continue
                # Skip navigation links
                if line.startswith('[[') and line.endswith(']]'):
                    continue

                vs_match = re.match(r'^##\s*(\d+)\.?\s*(.*)', line)
                if vs_match:
                    # Save previous verse
                    if current_vs is not None and current_text:
                        verses[current_vs] = current_text.strip()
                    current_vs = int(vs_match.group(1))
                    current_text = vs_match.group(2).strip()
                elif current_vs is not None:
                    # Continuation of current verse
                    current_text += ' ' + line

            # Save last verse
            if current_vs is not None and current_text:
                verses[current_vs] = current_text.strip()

            if verses:
                if bid not in result:
                    result[bid] = {}
                result[bid][ch] = verses

    return result


def main():
    if not os.path.isdir(REPO):
        print(f"Error: {REPO} not found. Clone first:")
        print("  git clone https://github.com/awerkamp/markdown-scriptures-standard-works-church-of-jesus-christ.git /tmp/jst-markdown")
        sys.exit(1)

    conn = get_db()

    print("Parsing JST OT...", flush=True)
    jst_ot = parse_all_books(os.path.join(REPO, "JST Old Testament"))
    print(f"  {sum(len(chs) for chs in jst_ot.values())} chapters")

    print("Parsing JST NT...", flush=True)
    jst_nt = parse_all_books(os.path.join(REPO, "JST New Testament"))
    print(f"  {sum(len(chs) for chs in jst_nt.values())} chapters")

    jst = {**jst_ot, **jst_nt}

    # Store in text_resources
    inserted = 0
    for bid, chapters in jst.items():
        for ch, verses in chapters.items():
            for vs, text in verses.items():
                vid = f"{bid}.{ch}.{vs}"

                conn.execute(
                    "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'JST', ?, 'eng')",
                    (vid, text)
                )
                inserted += 1

                if inserted % 1000 == 0:
                    conn.commit()
                    print(f"  {inserted} verses...", flush=True)

    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM text_resources WHERE version='JST'").fetchone()[0]
    print("\nResults:")
    print(f"  Inserted: {inserted}")
    print(f"  Total JST verses: {total}")

    conn.close()


if __name__ == "__main__":
    main()
