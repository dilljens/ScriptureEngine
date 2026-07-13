#!/usr/bin/env python3
"""Ingest the full JST (Inspired Version) from awerkamp markdown.

Compares JST vs KJV verse-by-verse through the entire OT + NT.
Creates:
  - jst_change:  modified wording (length ratio < 1.3×)
  - jst_addition: expanded text (length ratio >= 1.3×)
  - skips identical verses

Source: github.com/awerkamp/markdown-scriptures-standard-works-church-of-jesus-christ
Uses the KJV and JST markdown files side-by-side from the same repo.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db

# Path to the cloned awerkamp repo
REPO = "/tmp/jst-markdown"

# Book ID mapping: (directory_name) -> our book_id
# Handles both KJV (spaces) and JST (no spaces) naming
BOOK_NAME_TO_ID = {
    "Genesis": "gen", "Exodus": "exo", "Leviticus": "lev", "Numbers": "num",
    "Deuteronomy": "deu", "Joshua": "josh", "Judges": "judg", "Ruth": "ruth",
    "1Samuel": "1sam", "1 Samuel": "1sam",
    "2Samuel": "2sam", "2 Samuel": "2sam",
    "1Kings": "1kgs", "1 Kings": "1kgs",
    "2Kings": "2kgs", "2 Kings": "2kgs",
    "1Chronicles": "1chr", "1 Chronicles": "1chr",
    "2Chronicles": "2chr", "2 Chronicles": "2chr",
    "Ezra": "ezra", "Nehemiah": "neh", "Esther": "esth",
    "Job": "job", "Psalms": "psa", "Proverbs": "prov",
    "Ecclesiastes": "eccl",
    "Solomon's Song": "song", "Song of Solomon": "song",
    "Isaiah": "isa", "Jeremiah": "jer", "Lamentations": "lam",
    "Ezekiel": "ezek", "Daniel": "dan",
    "Hosea": "hos", "Joel": "joel", "Amos": "amos",
    "Obadiah": "obad", "Obediah": "obad",
    "Jonah": "jonah", "Micah": "mic", "Nahum": "nah", "Habakkuk": "hab",
    "Zephaniah": "zeph", "Haggai": "hag", "Zechariah": "zech", "Malachi": "mal",
    # NT
    "Matthew": "matt", "Mark": "mark", "Luke": "luke", "John": "john",
    "Acts": "acts", "Romans": "rom",
    "1Corinthians": "1cor", "1 Corinthians": "1cor",
    "2Corinthians": "2cor", "2 Corinthians": "2cor",
    "Galatians": "gal", "Ephesians": "eph", "Philippians": "phil",
    "Colossians": "col", "Collosians": "col",
    "1Thessalonians": "1thes", "1 Thessalonians": "1thes",
    "2Thessalonians": "2thes", "2 Thessalonians": "2thes",
    "1Timothy": "1tim", "1 Timothy": "1tim",
    "2Timothy": "2tim", "2 Timothy": "2tim",
    "Titus": "titus", "Philemon": "philem", "Hebrews": "heb",
    "James": "james",
    "1Peter": "1pet", "1 Peter": "1pet",
    "2Peter": "2pet", "2 Peter": "2pet",
    "1John": "1john", "1 John": "1john",
    "2John": "2john", "2 John": "2john",
    "3John": "3john", "3 John": "3john",
    "Jude": "jude", "Revelation": "rev",
}

# Books excluded from JST (Song of Solomon)
SKIP_BOOKS = {"Solomon's Song", "Song of Solomon"}

# Books that use different chapter numbering in JST vs KJV — handle carefully
# For now, we parse both and match by (book, chapter, verse) key


def normalize(text):
    """Normalize text for comparison — strip whitespace, lowercase."""
    return re.sub(r'\s+', ' ', text.strip().lower().replace("'", "'"))


def parse_markdown_file(filepath):
    """Parse a markdown scripture file into a dict of {verse_ref: text}.

    Format: line with "## N." starts a verse, text follows until next marker.
    Returns dict of {(chapter, verse): text}
    """
    verses = {}
    if not os.path.exists(filepath):
        return verses

    with open(filepath) as f:
        content = f.read()

    # Find all verse markers: "## N." where N is the verse number
    # Split on ## markers
    parts = re.split(r'^##\s+(\d+)\.\s*$', content, flags=re.MULTILINE)

    # parts = [header_before_first_verse, verse1_num, verse1_text, verse2_num, verse2_text, ...]
    if len(parts) < 3:
        return verses

    # First part is before the first verse marker (navigation links)
    # Then alternating: verse_num, verse_text
    for i in range(1, len(parts) - 1, 2):
        if i + 1 < len(parts):
            verse_num = int(parts[i])
            verse_text = parts[i + 1].strip()
            # Remove any trailing navigation links on last line
            verse_text = re.sub(r'\n\[\[.*?\]\].*$', '', verse_text).strip()
            if verse_text:
                verses[verse_num] = verse_text

    return verses


def parse_all_books(base_dir, is_jst=False):
    """Parse all books from a testament directory.

    Args:
        base_dir: e.g., "/tmp/jst-markdown/Old Testament" or "JST Old Testament"
        is_jst: whether this is JST (affects file casing and naming)

    Returns:
        dict of {book_id: {chapter: {verse: text}}}
    """
    result = {}

    if not os.path.exists(base_dir):
        return result

    # Get chapter-level markdown files (one per chapter)
    # JST uses capitalized file names, KJV uses lowercase
    for book_dir in sorted(os.listdir(base_dir)):
        book_path = os.path.join(base_dir, book_dir)
        if not os.path.isdir(book_path):
            continue

        # Extract book name: "01 Genesis" -> "Genesis"
        book_name = re.sub(r'^\d+\s+', '', book_dir).strip()

        if book_name in SKIP_BOOKS:
            continue

        book_id = BOOK_NAME_TO_ID.get(book_name)
        if not book_id:
            print(f"  WARNING: Unknown book '{book_name}' in {base_dir}")
            continue

        result[book_id] = {}

        # Parse each chapter file
        for fname in sorted(os.listdir(book_path)):
            if not fname.endswith('.md'):
                continue
            if fname.lower().startswith(book_name.lower().replace(' ', '').replace('1', '').replace('2', '').replace('3', '') or 'readme'):
                # Skip the book index file (e.g., Genesis.md)
                if fname.lower() == book_name.lower().replace(' ', '') + '.md':
                    continue
                if fname.lower().startswith(book_name.lower().split(' ')[-1] + '.md'):
                    continue

            # Extract chapter number from filename
            # JST: "Genesis1.md" -> 1, KJV: "genesis1.md" -> 1
            # But also: "genesis10.md" -> 10, "genesis1.md" -> 1
            ch_match = re.search(r'(\d+)\.md$', fname)
            if not ch_match:
                continue

            chapter = int(ch_match.group(1))
            filepath = os.path.join(book_path, fname)
            verses = parse_markdown_file(filepath)

            if verses:
                result[book_id][chapter] = verses

    return result


def is_real_change(kjv_text, jst_text):
    """Check if texts are genuinely different beyond punctuation/whitespace."""
    k_norm = normalize(kjv_text)
    j_norm = normalize(jst_text)
    if k_norm == j_norm:
        return False
    # Strip punctuation-only differences
    k_stripped = re.sub(r'[^\w\s]', '', k_norm)
    j_stripped = re.sub(r'[^\w\s]', '', j_norm)
    return k_stripped != j_stripped


def main():
    conn = get_db()

    # Parse all books
    print("Parsing KJV OT...", flush=True)
    kjv_ot = parse_all_books(os.path.join(REPO, "Old Testament"))
    print(f"  {sum(len(chs) for chs in kjv_ot.values())} chapters")

    print("Parsing KJV NT...", flush=True)
    kjv_nt = parse_all_books(os.path.join(REPO, "New Testament"))
    print(f"  {sum(len(chs) for chs in kjv_nt.values())} chapters")

    print("Parsing JST OT...", flush=True)
    jst_ot = parse_all_books(os.path.join(REPO, "JST Old Testament"), is_jst=True)
    print(f"  {sum(len(chs) for chs in jst_ot.values())} chapters")

    print("Parsing JST NT...", flush=True)
    jst_nt = parse_all_books(os.path.join(REPO, "JST New Testament"), is_jst=True)
    print(f"  {sum(len(chs) for chs in jst_nt.values())} chapters")

    # Combine
    kjv = {**kjv_ot, **kjv_nt}
    jst = {**jst_ot, **jst_nt}

    # Count total verses across all books
    kjv_total = sum(len(cv) for b in kjv.values() for cv in b.values())
    jst_total = sum(len(cv) for b in jst.values() for cv in b.values())
    print(f"KJV total: {kjv_total} verses across {len(kjv)} books")
    print(f"JST total: {jst_total} verses across {len(jst)} books")

    # Compare verse-by-verse
    count_change = 0
    count_addition = 0
    count_identical = 0
    count_skip = 0

    books_list = sorted(set(list(kjv.keys()) + list(jst.keys())))
    for bi, book_id in enumerate(books_list):
        print(f"  [{bi+1}/{len(books_list)}] {book_id}...", flush=True)
        kjv_book = kjv.get(book_id, {})
        jst_book = jst.get(book_id, {})

        all_chapters = set(list(kjv_book.keys()) + list(jst_book.keys()))

        for ch in sorted(all_chapters):
            kjv_ch = kjv_book.get(ch, {})
            jst_ch = jst_book.get(ch, {})

            all_verses = set(list(kjv_ch.keys()) + list(jst_ch.keys()))

            for v in sorted(all_verses):
                k_text = kjv_ch.get(v, "")
                j_text = jst_ch.get(v, "")

                # JST-only verse (new addition, no KJV counterpart)
                if j_text and not k_text:
                    vid = f"{book_id}.{ch}.{v}"
                    meta = json.dumps({
                        "jst": j_text[:500],
                        "kjv": "(no KJV verse)",
                        "jst_len": len(normalize(j_text)),
                        "kjv_len": 0,
                    })
                    try:
                        conn.execute("""
                            INSERT INTO connections
                                (source_verse, target_verse, layer, type, subtype,
                                 strength, confidence, discovered_by, metadata)
                            VALUES (?, ?, 'textual', 'jst_addition', 'joseph_smith',
                                    0.8, 0.85, 'algorithm', ?)
                            ON CONFLICT(source_verse, target_verse, layer, type, subtype)
                            DO UPDATE SET metadata = excluded.metadata
                        """, (vid, vid, meta))
                        count_addition += 1
                    except Exception:
                        count_skip += 1
                    continue

                # KJV-only verse (skipped — JST doesn't remove verses)
                if not j_text:
                    continue

                if not is_real_change(k_text, j_text):
                    count_identical += 1
                    continue

                # Determine change type
                k_len = len(normalize(k_text))
                j_len = len(normalize(j_text))

                if j_len > k_len * 1.3:
                    ctype = "jst_addition"
                    count_addition += 1
                else:
                    ctype = "jst_change"
                    count_change += 1

                vid = f"{book_id}.{ch}.{v}"
                meta = json.dumps({
                    "jst": j_text[:500],
                    "kjv": k_text[:500],
                    "jst_len": j_len,
                    "kjv_len": k_len,
                })

                try:
                    conn.execute("""
                        INSERT INTO connections
                            (source_verse, target_verse, layer, type, subtype,
                             strength, confidence, discovered_by, metadata)
                        VALUES (?, ?, 'textual', ?, 'joseph_smith',
                                0.8, 0.9, 'algorithm', ?)
                        ON CONFLICT(source_verse, target_verse, layer, type, subtype)
                        DO UPDATE SET strength = 0.8, confidence = 0.9,
                                      metadata = excluded.metadata
                    """, (vid, vid, ctype, meta))
                except Exception:
                    count_skip += 1

                if (count_change + count_addition) % 500 == 0:
                    conn.commit()
                    print(f"  ... {count_change + count_addition} JST connections so far", flush=True)

    conn.commit()

    # Stats
    total = count_change + count_addition
    print("\nResults:")
    print(f"  jst_change:   {count_change}")
    print(f"  jst_addition: {count_addition}")
    print(f"  Total JST:    {total}")
    print(f"  Identical:    {count_identical}")
    print(f"  Skipped:      {count_skip}")

    t = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='textual'").fetchone()["c"]
    print(f"\n  Textual layer total: {t}")

    conn.close()


if __name__ == "__main__":
    main()
