#!/usr/bin/env python3
"""Ingest Latin Vulgate text into textual_variants table.

Downloads structured JSON from yorikso/latinvulgatebible and
inserts verse-aligned Latin text into the database for
comparison with the KJV English text.

Usage:  python3 scripts/ingest_vulgate.py
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Vulgate book name -> project book ID mapping
BOOK_MAP = {
    'Genesis': 'gen', 'Exodus': 'exo', 'Leviticus': 'lev', 'Numbers': 'num',
    'Deuteronomy': 'deu', 'Joshua': 'josh', 'Judges': 'judg', 'Ruth': 'ruth',
    '1-Samuel': '1sam', '2-Samuel': '2sam', '1-Kings': '1kgs', '2-Kings': '2kgs',
    '1-Chronicles': '1chr', '2-Chronicles': '2chr',
    'Ezra': 'ezra', 'Nehemiah': 'neh',
    'Esther': 'esth',
    'Job': 'job', 'Psalms': 'psa', 'Proverbs': 'prov',
    'Ecclesiastes': 'eccl', 'SongOfSongs': 'song',
    'Isaiah': 'isa', 'Jeremiah': 'jer', 'Lamentations': 'lam',
    'Ezekiel': 'ezek', 'Daniel': 'dan',
    'Hosea': 'hos', 'Joel': 'joel', 'Amos': 'amos', 'Obadiah': 'obad',
    'Jonah': 'jonah', 'Micah': 'mic', 'Nahum': 'nah', 'Habakkuk': 'hab',
    'Zephaniah': 'zeph', 'Haggai': 'hag', 'Zechariah': 'zech', 'Malachi': 'mal',
    # NT
    'Matthew': 'matt', 'Mark': 'mark', 'Luke': 'luke', 'John': 'john',
    'Acts': 'acts',
    'Romans': 'rom', '1-Corinthians': '1cor', '2-Corinthians': '2cor',
    'Galatians': 'gal', 'Ephesians': 'eph', 'Philippians': 'phil',
    'Colossians': 'col', '1-Thessalonians': '1thes', '2-Thessalonians': '2thes',
    '1-Timothy': '1tim', '2-Timothy': '2tim', 'Titus': 'titus', 'Philemon': 'philem',
    'Hebrews': 'heb', 'James': 'james', '1-Peter': '1pet', '2-Peter': '2pet',
    '1-John': '1john', '2-John': '2john', '3-John': '3john', 'Jude': 'jude',
    'Revelation': 'rev',
}

# Books to skip (deuterocanonical, not in project canon)
SKIP_BOOKS = {'Tobit', 'Judith', 'Song2', 'Wisdom', 'Sirach', 'Baruch',
              '1-Maccabees', '2-Maccabees'}


def create_textual_variants_table(conn):
    """Create the textual_variants table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS textual_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_id TEXT NOT NULL REFERENCES verses(id),
            tradition TEXT NOT NULL DEFAULT 'vulgate',
            text TEXT NOT NULL,
            source TEXT DEFAULT 'Clementine Vulgate',
            notes TEXT DEFAULT '',
            UNIQUE(verse_id, tradition)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tv_verse ON textual_variants(verse_id)")
    conn.commit()
    print("  ✓ textual_variants table ready")


def map_psalm_chapter(vulgate_ch):
    """Map Vulgate Psalm numbering to KJV numbering.

    Vulgate follows LXX numbering which differs from MT/KJV.
    Vulgate 1-8 = KJV 1-8
    Vulgate 9 = KJV 9+10 (combined)
    Vulgate 10-112 = KJV 11-113
    Vulgate 113 = KJV 114+115 (combined)
    Vulgate 114-115 = KJV 116 (split)
    Vulgate 116-145 = KJV 117-146
    Vulgate 146-147 = KJV 147 (split)
    Vulgate 148-150 = KJV 148-150
    Vulgate 151 = no KJV equivalent
    """
    ch = int(vulgate_ch)
    if ch <= 8:
        return [ch]  # 1-8 match
    elif ch == 9:
        return [9, 10]  # Vulgate 9 = KJV 9+10
    elif ch <= 112:
        return [ch + 1]  # 10-112 → 11-113
    elif ch == 113:
        return [114, 115]  # Vulgate 113 = KJV 114+115
    elif ch == 114:
        return [116]  # Vulgate 114 = KJV 116:1-9
    elif ch == 115:
        return [116]  # Vulgate 115 = KJV 116:10-19
    elif ch <= 145:
        return [ch + 2]  # 116-145 → 118-147
    elif ch == 146:
        return [147]  # Vulgate 146 = KJV 147:1-11
    elif ch == 147:
        return [147]  # Vulgate 147 = KJV 147:12-20
    elif ch <= 150:
        return [ch - 2]  # 148→148, 149→149, 150→150 (offset = -2)
    elif ch == 151:
        return []  # No KJV equivalent
    return [ch]


def map_esther_chapter(vulgate_ch):
    """Vulgate Esther has chapters 1-10 matching KJV.
    Additional chapters (11-16) are deuterocanonical."""
    ch = int(vulgate_ch)
    if 1 <= ch <= 10:
        return [ch]
    return []  # Skip deuterocanonical chapters


def map_daniel_chapter(vulgate_ch):
    """Vulgate Daniel has chapters 1-12 matching KJV.
    Chapters 13 (Susanna) and 14 (Bel & Dragon) are deuterocanonical."""
    ch = int(vulgate_ch)
    if 1 <= ch <= 12:
        return [ch]
    return []  # Skip deuterocanonical chapters


def get_chapter_mapper(book_id):
    """Get the chapter mapping function for a book."""
    mappers = {
        'psa': map_psalm_chapter,
        'esth': map_esther_chapter,
        'dan': map_daniel_chapter,
    }
    return mappers.get(book_id, lambda ch: [int(ch)])


def download_vulgate():
    """Download the complete Vulgate JSON."""
    url = 'https://raw.githubusercontent.com/yoarikso/latinvulgatebible/master/vulgate-json/EntireBible-VULGATE.json'
    print(f"  Downloading from {url}...", flush=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read())
    print(f"  Downloaded {len(data)} keys")
    return data


def ingest_vulgate(conn, data):
    """Ingest Vulgate text into textual_variants table."""
    # Clear existing Vulgate variants
    conn.execute("DELETE FROM textual_variants WHERE tradition = 'vulgate'")
    conn.commit()

    total = 0
    unmapped = 0
    skipped_dc = 0

    for vulg_book_name, chapters in data.items():
        if vulg_book_name == 'charset':
            continue

        book_id = BOOK_MAP.get(vulg_book_name)
        if not book_id:
            if vulg_book_name in SKIP_BOOKS:
                skipped_dc += 1
            else:
                print(f"  ? Unmapped book: {vulg_book_name}")
                unmapped += 1
            continue

        chapter_mapper = get_chapter_mapper(book_id)
        total_in_book = 0

        for vulg_ch, verses in chapters.items():
            if vulg_ch == 'charset':
                continue

            kjv_chapters = chapter_mapper(vulg_ch)
            if not kjv_chapters:
                continue

            for kjv_ch in kjv_chapters:
                for vulg_v, text in verses.items():
                    if vulg_v == 'charset':
                        continue

                    verse_id = f"{book_id}.{kjv_ch}.{vulg_v}"

                    # Verify the verse exists in the DB
                    exists = conn.execute(
                        "SELECT 1 FROM verses WHERE id = ?", (verse_id,)
                    ).fetchone()

                    if exists:
                        try:
                            conn.execute("""
                                INSERT OR IGNORE INTO textual_variants
                                    (verse_id, tradition, text, source)
                                VALUES (?, 'vulgate', ?, 'Clementine Vulgate')
                            """, (verse_id, text))
                            total += 1
                            total_in_book += 1
                        except Exception:
                            pass

        if total_in_book > 0:
            print(f"  {vulg_book_name:<20} → {book_id:<6} {total_in_book:>5} verses")

    conn.commit()
    print(f"\n  Total verses stored: {total:,}")
    print(f"  Unmapped books: {unmapped}")
    print(f"  Deuterocanonical skipped: {skipped_dc}")
    return total


def main():
    print("=" * 60)
    print("  VULGATE INGESTION")
    print("=" * 60)

    conn = get_db()
    create_textual_variants_table(conn)

    data = download_vulgate()
    total = ingest_vulgate(conn, data)

    conn.close()
    print(f"\n  Done. {total:,} verses ingested.")


if __name__ == "__main__":
    main()
