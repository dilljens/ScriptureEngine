#!/usr/bin/env python3
"""
Re-import ALL KJV Apocrypha from bible-api.com.
Cleans up duplicates, re-imports all books fresh.

Usage: python3 scripts/import_apocrypha_api.py
"""

import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Apocrypha books: (api_name, our_book_id, title, chapter_count)
# Chapter counts verified against bible-api.com (2026-07)
APOC_BOOKS = [
    ('Tobit', 'tob', 'Tobit', 14),
    ('Judith', 'jdt', 'Judith', 16),
    ('Wisdom+of+Solomon', 'wis', 'Wisdom of Solomon', 19),
    ('Sirach', 'sir', 'Sirach (Ecclesiasticus)', 51),
    ('Baruch', 'bar', 'Baruch', 5),
    ('Prayer+of+Manasses', 'man', 'Prayer of Manasses', 1),
    ('1+Maccabees', '1ma', '1 Maccabees', 16),
    ('2+Maccabees', '2ma', '2 Maccabees', 15),
    ('1+Esdras', '1esd', '1 Esdras', 9),
    ('2+Esdras', '2esd', '2 Esdras', 16),
    ('Esther+Additions', 'esga', 'Additions to Esther', 16),
    ('Prayer+of+Azariah', 's3y', 'Song of Three Children', 1),
    ('Susanna', 'sus', 'Susanna', 1),
    ('Bel+and+the+Dragon', 'bel', 'Bel and the Dragon', 1),
]


def fetch_book(api_name, book_id, chapters):
    """Fetch all verses for a book from bible-api.com, with retries."""
    verses = []
    last_error = None
    for ch in range(1, chapters + 1):
        url = f'https://bible-api.com/{api_name}+{ch}?version=kjv'
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                resp = urllib.request.urlopen(req, timeout=20)
                data = json.loads(resp.read())
                chapter_verses = data.get('verses', [])
                for v in chapter_verses:
                    text = v.get('text', '').strip()
                    if text:
                        verses.append((ch, v.get('verse', 1), text))
                last_error = None
                time.sleep(0.5)
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    # Chapter genuinely doesn't exist
                    last_error = f"ch.{ch}: 404"
                    break
                last_error = f"ch.{ch}: HTTP {e.code}"
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                last_error = f"ch.{ch}: {e}"
                time.sleep(2 * (attempt + 1))
        if last_error:
            print(f'  WARN: {api_name} {last_error}')
    return verses


def cleanup_duplicates(conn):
    """Remove duplicate apocrypha book entries (URL-encoded names)."""
    # Delete duplicate books with URL-encoded names (have 0 verses)
    deleted = conn.execute("""
        DELETE FROM books
        WHERE work_id = 'apoc'
        AND id IN (
            '1+Esdras', '1+Maccabees', '2+Esdras', '2+Maccabees',
            'Additions+to+Esther', 'Baruch', 'Bel+and+the+Dragon',
            'Judith', 'Prayer+of+Azariah', 'Prayer+of+Manasses',
            'Psalm+151', 'Sirach', 'Susanna', 'Tobit', 'Wisdom+of+Solomon'
        )
    """).rowcount
    # Clean up any unused verses
    conn.execute("""
        DELETE FROM verses
        WHERE book_id IN (
            '1+Esdras', '1+Maccabees', '2+Esdras', '2+Maccabees',
            'Additions+to+Esther', 'Baruch', 'Bel+and+the+Dragon',
            'Judith', 'Prayer+of+Azariah', 'Prayer+of+Manasses',
            'Psalm+151', 'Sirach', 'Susanna', 'Tobit', 'Wisdom+of+Solomon',
            'psa151'
        )
    """)
    # Clean up corresponding text_resources
    conn.execute("""
        DELETE FROM text_resources
        WHERE verse_id LIKE 'psa151.%'
    """)
    for bad_id in ['1+Esdras', '1+Maccabees', '2+Esdras', '2+Maccabees',
                    'Additions+to+Esther', 'Baruch', 'Bel+and+the+Dragon',
                    'Judith', 'Prayer+of+Azariah', 'Prayer+of+Manasses',
                    'Psalm+151', 'Sirach', 'Susanna', 'Tobit', 'Wisdom+of+Solomon']:
        conn.execute("DELETE FROM text_resources WHERE verse_id LIKE ?", (f'{bad_id}.%',))
    conn.commit()
    print(f"  Cleaned up {deleted} duplicate book entries")


def delete_existing_apoc(conn):
    """Remove all existing apocrypha verse data for fresh re-import."""
    # Delete verses
    del_verses = conn.execute("""
        DELETE FROM verses WHERE book_id IN (SELECT id FROM books WHERE work_id='apoc')
    """).rowcount
    # Delete text_resources
    for r in conn.execute("SELECT id FROM books WHERE work_id='apoc'").fetchall():
        conn.execute("DELETE FROM text_resources WHERE verse_id LIKE ?", (f'{r["id"]}.%',))
    conn.commit()
    print(f"  Deleted {del_verses} existing apocrypha verses")


def main():
    conn = get_db()

    # Step 1: ensure work exists
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('apoc', 'Apocrypha')")

    # Step 2: clean up duplicate entries
    print("Step 1: Cleaning up duplicate book entries...")
    cleanup_duplicates(conn)

    # Step 3: delete all existing apocrypha verse data
    print("Step 2: Removing existing apocrypha verse data...")
    delete_existing_apoc(conn)

    # Step 4: ensure all books exist (with proper position)
    print("Step 3: Ensuring book entries...")
    for idx, (_, book_id, title, _) in enumerate(APOC_BOOKS, start=1):
        conn.execute(
            "INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES (?, 'apoc', ?, ?)",
            (book_id, title, idx)
        )
    conn.commit()

    # Step 5: fetch all books
    print("Step 4: Fetching all apocrypha from bible-api.com...")
    total = 0
    for api_name, book_id, title, chapters in APOC_BOOKS:
        print(f'  {title} ({book_id})...', end=' ', flush=True)
        verses = fetch_book(api_name, book_id, chapters)

        for ch, vs, text in verses:
            vid = f'{book_id}.{ch}.{vs}'
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
                    (vid, book_id, ch, vs, text)
                )
                conn.execute(
                    "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'KJV', ?, 'eng')",
                    (vid, text)
                )
                total += 1
            except Exception as e:
                print(f'  DB error {vid}: {e}')

        conn.commit()
        print(f'{len(verses)} verses')

    conn.close()
    print(f'\n{"="*50}')
    print(f'Total: {total} verses imported')

    # Summary of what was attempted vs what succeeded
    print(f'\nBooks: {len(APOC_BOOKS)}')
    print('Note: Psalm 151 is not available on bible-api.com (skipped)')
    print('Note: Some books may have fewer chapters on bible-api.com than full KJV Apocrypha')
    print('      — Wisdom of Solomon has 10 chapters on API vs 19 in standard KJV')
    print('      — Additions to Esther is treated as a single chapter')
    print(f'{"="*50}')


if __name__ == '__main__':
    main()
