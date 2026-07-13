#!/usr/bin/env python3
"""Import a Bible translation (HTML per-chapter format) into text_resources."""

import glob
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import get_db

WEB_HTML_DIR = '/tmp/web_html'

BOOK_MAP = {
    'GEN': 'gen', 'EXO': 'exo', 'LEV': 'lev', 'NUM': 'num', 'DEU': 'deu',
    'JOS': 'josh', 'JDG': 'judg', 'RUT': 'ruth',
    '1SA': '1sam', '2SA': '2sam', '1KI': '1kgs', '2KI': '2kgs',
    '1CH': '1chr', '2CH': '2chr',
    'EZR': 'ezra', 'NEH': 'neh', 'EST': 'esth',
    'JOB': 'job', 'PSA': 'psa', 'PRO': 'prov', 'ECC': 'eccl', 'SNG': 'song',
    'ISA': 'isa', 'JER': 'jer', 'LAM': 'lam', 'EZK': 'ezek', 'DAN': 'dan',
    'HOS': 'hos', 'JOL': 'joel', 'AMO': 'amos', 'OBA': 'obad', 'JON': 'jonah',
    'MIC': 'mic', 'NAM': 'nah', 'HAB': 'hab', 'ZEP': 'zeph', 'HAG': 'hag',
    'ZEC': 'zech', 'MAL': 'mal',
    'MAT': 'matt', 'MRK': 'mark', 'LUK': 'luke', 'JHN': 'john',
    'ACT': 'acts',
    'ROM': 'rom', '1CO': '1cor', '2CO': '2cor', 'GAL': 'gal',
    'EPH': 'eph', 'PHP': 'phil', 'COL': 'col',
    '1TH': '1thes', '2TH': '2thes', '1TI': '1tim', '2TI': '2tim',
    'TIT': 'titus', 'PHM': 'philem', 'HEB': 'heb',
    'JAS': 'james', '1PE': '1pet', '2PE': '2pet',
    '1JN': '1john', '2JN': '2john', '3JN': '3john', 'JUD': 'jude',
    'REV': 'rev',
}

# Books to skip (apocrypha, front/back matter)
SKIP_BOOKS = {'FRT', 'TOB', 'JDT', 'ESG', 'DAG', 'WIS', 'SIR', 'BAR',
              '1MA', '2MA', '1ES', 'MAN', 'PS2', '3MA', '2ES', '4MA', 'GLO'}

VERSE_RE = re.compile(r'<span\s+class="verse"[^>]*\s+id="V(\d+)"[^>]*>\d+&#\d+;</span>', re.IGNORECASE)
TAG_RE = re.compile(r'<[^>]+>')
NAV_OR_FOOTNOTE_RE = re.compile(r'<(?:ul\s+class=[\'"]tnav[\'"]|div\s+class=[\'"]footnote[\'"])', re.IGNORECASE)

def strip_tags(text):
    return TAG_RE.sub('', text)

def extract_verses_from_html(filepath):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    main_match = re.search(r'<div class="main">(.*?)(?=<ul class=\'tnav\'|<div class="footnote")', content, re.DOTALL)
    if not main_match:
        return []
    main_content = main_match.group(1)
    main_content = re.sub(r'<a[^>]*class="notemark"[^>]*>.*?</a>', '', main_content)

    matches = list(VERSE_RE.finditer(main_content))
    if not matches:
        return []

    verses = []
    for i, m in enumerate(matches):
        vnum = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(main_content)
        raw_text = main_content[start:end]
        text = html.unescape(strip_tags(raw_text).strip())
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            verses.append((vnum, text))
    return verses


def import_web(conn, version='WEB'):
    count = 0
    seen = set()

    files = sorted(glob.glob(os.path.join(WEB_HTML_DIR, '*.htm')))
    book_codes_sorted = sorted(BOOK_MAP.keys(), key=lambda x: (len(x), x), reverse=True)
    book_codes_pat = '(' + '|'.join(re.escape(c) for c in book_codes_sorted) + ')'
    chapter_file_re = re.compile(book_codes_pat + r'(\d+)\.htm$')

    total_looked_up = 0
    total_missing = 0
    missing_books = set()

    for fpath in files:
        m = chapter_file_re.search(fpath)
        if not m:
            continue
        book_code = m.group(1)
        ch_num = int(m.group(2))

        if book_code in SKIP_BOOKS or ch_num == 0:
            continue

        book_id = BOOK_MAP.get(book_code)
        if not book_id:
            missing_books.add(book_code)
            continue

        verses = extract_verses_from_html(fpath)

        for vnum, text in verses:
            vid = f"{book_id}.{ch_num}.{vnum}"
            if vid in seen:
                continue
            seen.add(vid)

            row = conn.execute(
                "SELECT COUNT(*) FROM verses WHERE id=?", (vid,)
            ).fetchone()[0]
            total_looked_up += 1

            if row:
                conn.execute(
                    "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, ?, ?, 'eng')",
                    (vid, version, text)
                )
                count += 1
            else:
                total_missing += 1
                if total_missing <= 5:
                    pass

    if missing_books:
        print(f"  Unmapped book codes: {missing_books}")

    print(f"  Verses looked up: {total_looked_up}, not in DB: {total_missing}")
    return count


def main():
    from lib.db import init_db
    init_db()

    conn = get_db()
    version = 'WEB'

    print(f"Importing {version} from {WEB_HTML_DIR}...")
    count = import_web(conn, version)

    if count > 0:
        conn.execute("UPDATE text_resources SET is_default = 0 WHERE is_default = 1")
        conn.execute("UPDATE text_resources SET is_default = 1 WHERE version = ?", (version,))
        conn.commit()
        print(f"Set {version} as default")
    else:
        print("No verses imported — nothing set as default.")

    conn.close()

    print(f"\nTotal: {count} verses imported")

    if count > 0:
        conn = get_db()
        rows = conn.execute(
            "SELECT verse_id, text FROM text_resources WHERE version='WEB' AND verse_id IN ('gen.1.1','john.1.1','psa.23.1') ORDER BY verse_id"
        ).fetchall()
        for r in rows:
            print(f"  {r['verse_id']}: {r['text'][:100]}")
        conn.close()


if __name__ == '__main__':
    main()
