#!/usr/bin/env python3
"""
Import DSS English from The Firmament into text_english.

Stores Vermès-style English translations for 1QS, CD, 1QM, 1QSa.

Usage: python3 scripts/import_dss_english.py
"""

import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Each scroll: URL, prefix for verse IDs, and the short prefix
SITES = {
    '1QS': ('https://www.thefirmament.org/books-of-wisdom/dead-sea-scrolls/community-rule/', 'CR'),
    'CD': ('https://www.thefirmament.org/books-of-wisdom/dead-sea-scrolls/damascus-document/', 'DD'),
    '1QM': ('https://www.thefirmament.org/books-of-wisdom/dead-sea-scrolls/war-rule/', 'WR'),
    '1QSa': ('https://www.thefirmament.org/books-of-wisdom/dead-sea-scrolls/messianic-rule/', ''),
}


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    return resp.read().decode('utf-8')


def extract_verses(html_content, prefix, scroll_id):
    """Extract verses from Firmament HTML."""
    import html as html_mod
    verses = []
    if prefix:
        pattern = re.compile(f'({prefix}\\s+(\\d+):(\\d+))\\s+(.+)', re.DOTALL)
    else:
        pattern = re.compile(r'((?:1QSa|MR)\s+(\d+):(\d+))\s+(.+)', re.DOTALL)

    for p in re.findall(r'<p[^>]*>(.*?)</p>', html_content, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', p)
        text = html_mod.unescape(text)
        text = text.strip()
        m = pattern.search(text)
        if m:
            ch = int(m.group(2))
            vs = int(m.group(3))
            verse_text = re.sub(r'\s+', ' ', m.group(4)).strip()
            verses.append((ch, vs, verse_text))
    return verses


def main():
    print("DSS English Import — The Firmament")
    print("=" * 50)

    conn = get_db()
    total_mapped = 0

    for scroll_id, (url, prefix) in SITES.items():
        print(f"\n{scroll_id}...", end=' ', flush=True)
        try:
            html_content = fetch(url)
        except Exception as e:
            print(f"FETCH ERROR: {e}")
            continue

        verses = extract_verses(html_content, prefix, scroll_id)
        if not verses:
            print("0 verses — checking alternate prefix...")
            # Try to auto-discover the prefix
            for alt_prefix in ['1QSa', 'MR', 'SA', 'SEREK', 'RULE']:
                matches = re.findall(f'({alt_prefix}\\s+\\d+:\\d+)', html_content)
                if matches:
                    prefix = alt_prefix
                    verses = extract_verses(html_content, prefix, scroll_id)
                    print(f"  Found prefix '{prefix}' with {len(verses)} verses")
                    break

            if not verses:
                print("  No English found")
                continue
        else:
            print(f"  {len(verses)} verses")

        # Get existing Hebrew verses for this scroll
        existing = conn.execute(
            "SELECT id, verse FROM verses WHERE book_id=? ORDER BY verse",
            (scroll_id,)
        ).fetchall()

        if not existing:
            print("  No verses in DB")
            continue

        # Map by sequential position
        n = min(len(existing), len(verses))
        updated = 0

        for i in range(n):
            verse_id = existing[i]['id']
            _, _, text = verses[i]

            # Store Firmament English as text_english
            conn.execute(
                "UPDATE verses SET text_english=? WHERE id=?",
                (text, verse_id)
            )
            # Also store as text_resource for version lookup
            conn.execute(
                "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'FIRMAMENT', ?, 'eng')",
                (verse_id, text)
            )
            updated += 1

        conn.commit()
        total_mapped += updated
        print(f"  Mapped {updated}/{len(existing)} lines")

    print(f"\n{'='*50}")
    print(f"Total DSS verses with English: {total_mapped}")

    # Verify
    dss_eng = conn.execute("""SELECT COUNT(*) FROM verses v
        WHERE v.book_id IN (SELECT id FROM books WHERE work_id='dss')
        AND (v.text_english LIKE 'The %' OR v.text_english LIKE 'In the%'
             OR v.text_english LIKE 'And%' OR v.text_english LIKE '"%'
             OR v.text_english LIKE 'Blessed%' OR v.text_english LIKE 'Who%'
             OR v.text_english LIKE 'Hear%' OR v.text_english LIKE 'For%')"""
    ).fetchone()[0]
    dss_total = conn.execute("""SELECT COUNT(*) FROM verses v
        WHERE v.book_id IN (SELECT id FROM books WHERE work_id='dss')"""
    ).fetchone()[0]
    print(f"DSS verses with proper English: {dss_eng} / {dss_total}")
    conn.close()


if __name__ == '__main__':
    main()
