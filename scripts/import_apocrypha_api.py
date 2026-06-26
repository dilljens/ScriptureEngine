#!/usr/bin/env python3
"""
Import KJV Apocrypha from bible-api.com.
Inserts into verses table (for chapter view + search) and text_resources.

Usage: python3 scripts/import_apocrypha_api.py
"""

import sys, os, json, urllib.request, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Apocrypha books: (api_name, our_book_id, title, chapter_count)
APOC_BOOKS = [
    ('Tobit', 'tob', 'Tobit', 14),
    ('Judith', 'jdt', 'Judith', 16),
    ('Wisdom+of+Solomon', 'wis', 'Wisdom of Solomon', 19),
    ('Sirach', 'sir', 'Sirach (Ecclesiasticus)', 51),
    ('Baruch', 'bar', 'Baruch', 6),
    ('Prayer+of+Manasses', 'man', 'Prayer of Manasses', 1),
    ('1+Maccabees', '1ma', '1 Maccabees', 16),
    ('2+Maccabees', '2ma', '2 Maccabees', 15),
    ('1+Esdras', '1esd', '1 Esdras', 9),
    ('2+Esdras', '2esd', '2 Esdras', 16),
    ('Additions+to+Esther', 'esga', 'Additions to Esther', 16),
    ('Prayer+of+Azariah', 's3y', 'Song of Three Children', 1),
    ('Susanna', 'sus', 'Susanna', 1),
    ('Bel+and+the+Dragon', 'bel', 'Bel and the Dragon', 1),
    ('Psalm+151', 'psa151', 'Psalm 151', 1),
]

def fetch_book(api_name, book_id, chapters):
    """Fetch all verses for a book from bible-api.com."""
    verses = []
    for ch in range(1, chapters + 1):
        url = f'https://bible-api.com/{api_name}+{ch}?version=kjv'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            for v in data.get('verses', []):
                text = v.get('text', '').strip()
                if text:
                    verses.append((ch, v.get('verse', 1), text))
            time.sleep(0.3)  # rate limit
        except Exception as e:
            print(f'  ERROR fetching {api_name} ch.{ch}: {e}')
    return verses

def main():
    conn = get_db()
    
    # Add apoc work
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('apoc', 'Apocrypha')")
    for bid, _, title, _ in APOC_BOOKS:
        conn.execute("INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES (?, 'apoc', ?, 99)",
                     (bid, title))
    conn.commit()
    
    total = 0
    for api_name, book_id, title, chapters in APOC_BOOKS:
        print(f'{title} ({book_id})...', end=' ', flush=True)
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
    print(f'\nTotal: {total} verses imported')

if __name__ == '__main__':
    main()
