#!/usr/bin/env python3
"""
Import KJV (including Apocrypha) into the verses table.

Uses the KJV USFM from ebible.org for the standard 66 books.
For the Apocrypha, extracts from the Crosswire KJVA Sword module.

Usage: python3 scripts/import_kjv_apocrypha.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Apocrypha book IDs and titles
APOC_BOOKS = [
    ('1esd', '1 Esdras', 1),
    ('2esd', '2 Esdras', 2),
    ('tob', 'Tobit', 3),
    ('jdt', 'Judith', 4),
    ('esga', 'Additions to Esther', 5),
    ('wis', 'Wisdom of Solomon', 6),
    ('sir', 'Sirach (Ecclesiasticus)', 7),
    ('bar', 'Baruch', 8),
    ('s3y', 'Song of Three Children', 9),
    ('sus', 'Susanna', 10),
    ('bel', 'Bel and the Dragon', 11),
    ('man', 'Prayer of Manasses', 12),
    ('1ma', '1 Maccabees', 13),
    ('2ma', '2 Maccabees', 14),
]

def import_apocrypha_text(text_file):
    """Import Apocrypha from a plain text file.

    Format expected:
    TOB 1:1 The book of the words of Tobias...
    TOB 1:2 ...
    """
    conn = get_db()

    # Add apoc work if not exists
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('apoc', 'Apocrypha')")

    total = 0
    for book_id, title, pos in APOC_BOOKS:
        # Add book
        conn.execute(
            "INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES (?, 'apoc', ?, ?)",
            (book_id, title, pos)
        )

    # Parse the text file (if provided)
    if text_file and os.path.exists(text_file):
        with open(text_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Format: BOOK CH:VERSE text
                m = re.match(r'^([A-Z0-9]+)\s+(\d+):(\d+)\s+(.+)$', line)
                if m:
                    book = m.group(1).lower()
                    chapter = int(m.group(2))
                    verse = int(m.group(3))
                    text = m.group(4).strip()

                    # Map to our book IDs
                    book_map = {
                        '1esd': '1esd', '2esd': '2esd', 'tob': 'tob',
                        'jdt': 'jdt', 'esga': 'esga', 'wis': 'wis',
                        'sir': 'sir', 'bar': 'bar', 's3y': 's3y',
                        'sus': 'sus', 'bel': 'bel', 'man': 'man',
                        '1ma': '1ma', '2ma': '2ma',
                    }
                    our_book = book_map.get(book.upper() if len(book) <= 4 else book, book)
                    verse_id = f"{our_book}.{chapter}.{verse}"

                    # Insert into verses table (creates the verse)
                    conn.execute(
                        "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
                        (verse_id, our_book, chapter, verse, text)
                    )
                    # Also add to text_resources as KJV
                    conn.execute(
                        "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'KJV', ?, 'eng')",
                        (verse_id, text)
                    )
                    total += 1

    conn.commit()
    conn.close()
    print(f"Imported {total} Apocrypha verses")

def import_kjv_usfm(usfm_dir):
    """Import KJV from USFM files (66 books)."""
    conn = get_db()

    # USFM 3-letter code to our book ID mapping
    BOOK_MAP = {
        'GEN': 'gen', 'EXO': 'exo', 'LEV': 'lev', 'NUM': 'num', 'DEU': 'deu',
        'JOS': 'josh', 'JDG': 'judg', 'RUT': 'ruth',
        '1SA': '1sam', '2SA': '2sam', '1KI': '1kgs', '2KI': '2kgs',
        '1CH': '1chr', '2CH': '2chr', 'EZR': 'ezra', 'NEH': 'neh',
        'EST': 'esth', 'JOB': 'job', 'PSA': 'psa', 'PRO': 'prov',
        'ECC': 'eccl', 'SNG': 'song', 'ISA': 'isa', 'JER': 'jer',
        'LAM': 'lam', 'EZK': 'ezek', 'DAN': 'dan', 'HOS': 'hos',
        'JOL': 'joel', 'AMO': 'amos', 'OBA': 'obad', 'JON': 'jonah',
        'MIC': 'mic', 'NAM': 'nah', 'HAB': 'hab', 'ZEP': 'zeph',
        'HAG': 'hag', 'ZEC': 'zech', 'MAL': 'mal',
        'MAT': 'matt', 'MRK': 'mark', 'LUK': 'luke', 'JHN': 'john',
        'ACT': 'acts', 'ROM': 'rom', '1CO': '1cor', '2CO': '2cor',
        'GAL': 'gal', 'EPH': 'eph', 'PHP': 'phil', 'COL': 'col',
        '1TH': '1thes', '2TH': '2thes', '1TI': '1tim', '2TI': '2tim',
        'TIT': 'titus', 'PHM': 'philem', 'HEB': 'heb', 'JAS': 'james',
        '1PE': '1pet', '2PE': '2pet', '1JN': '1john', '2JN': '2john',
        '3JN': '3john', 'JUD': 'jude', 'REV': 'rev',
    }

    total = 0
    for code, book_id in BOOK_MAP.items():
        path = os.path.join(usfm_dir, f"{code}.usfm")
        if not os.path.exists(path):
            continue

        with open(path, encoding='utf-8') as f:
            content = f.read()

        # Parse USFM: \v 1 text \v 2 text ...
        # USFM format: \c 1 \p \v 1 text...
        vs_pattern = re.findall(r'\\\\v (\d+)\s+(.*?)(?=\\\\v \d+|\\\\c \d+|$)', content, re.DOTALL)
        current_ch = 1

        # Parse chapter markers
        lines = content.split('\n')
        for line in lines:
            cm = re.match(r'\\c\s+(\d+)', line)
            if cm:
                current_ch = int(cm.group(1))

        for v_num, text in vs_pattern:
            v = int(v_num)
            # Clean up USFM markup
            text = re.sub(r'\\(?:w|f|fr|ft|xo|xq|xt|qs|ls)\s*.*?(?=\\\w|$)', '', text)
            text = re.sub(r'\\(?:p|q1|q2|q3|q4|m|r|s1|s2|s3|s4|d|sp|b|nb|ph|pi|pc|qr|qc|qa)', ' ', text)
            text = re.sub(r'\\(?:add|it|bd|sc|no|ul|em|fig)\*?', '', text)
            text = re.sub(r'\*', '', text)
            text = ' '.join(text.split()).strip()

            if text:
                verse_id = f"{book_id}.{current_ch}.{v}"
                conn.execute(
                    "UPDATE verses SET text_english = ? WHERE id = ?",
                    (text, verse_id)
                )
                conn.execute(
                    "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'KJV', ?, 'eng')",
                    (verse_id, text)
                )
                total += 1
                if total % 1000 == 0:
                    print(f"  {total} verses...")

    conn.commit()
    conn.close()
    print(f"Imported KJV {total} verses")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--apoc':
        import_apocrypha_text(sys.argv[2] if len(sys.argv) > 2 else None)
    elif len(sys.argv) > 2 and sys.argv[1] == '--usfm':
        import_kjv_usfm(sys.argv[2])
    else:
        print("Usage:")
        print("  python3 scripts/import_kjv_apocrypha.py --usfm /path/to/usfm_dir")
        print("  python3 scripts/import_kjv_apocrypha.py --apoc /path/to/apoc_text.txt")
