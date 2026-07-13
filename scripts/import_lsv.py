#!/usr/bin/env python3
"""
Import the Literal Standard Version (LSV) from USX format into text_resources.

Download source: https://openbible-api-1.biblica.com/artifactContent/64bff5e9fc80f074487a4e79
(USX ZIP from Open.Bible)

Usage: python3 scripts/import_lsv.py /path/to/lsv_usx_dir
"""

import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# USX book code → our book ID mapping
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

SKIP_CHARS = [
    '<char style="bd">', '</char>', '<char style="it">',
    '[[', ']]',  # square bracket markers
]

def clean_text(text):
    """Remove USX markup and normalize whitespace."""
    for sc in SKIP_CHARS:
        text = text.replace(sc, '')
    import re
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('\n', ' ').replace('\r', '')
    text = ' '.join(text.split())
    return text.strip()

def parse_verse_text(elem):
    """Extract text from a verse element, handling mixed content."""
    text = ''
    if elem.text:
        text += elem.text
    for child in elem:
        if child.tag == 'verse' and child.get('eid'):
            pass  # verse end marker
        elif child.tail:
            text += child.tail
    return text

def import_lsv(usx_dir):
    conn = get_db()
    total = 0
    errors = 0

    for usx_code, book_id in BOOK_MAP.items():
        usx_path = os.path.join(usx_dir, f"{usx_code}.usx")
        if not os.path.exists(usx_path):
            print(f"  SKIP {usx_code}: file not found")
            continue

        tree = ET.parse(usx_path)
        root = tree.getroot()
        current_chapter = None
        chapter_text = {}
        chapter_verses = {}

        # Walk through USX elements
        for elem in root:
            tag = elem.tag
            if tag == 'chapter':
                if elem.get('number'):
                    current_chapter = int(elem.get('number'))
                    chapter_text[current_chapter] = ''
                    chapter_verses[current_chapter] = {}
                continue

            if tag == 'para' and current_chapter:
                # Walk children to find verses
                current_verse = None
                text_parts = {}

                def walk_children(el, verse_num, text_parts):
                    if el.text:
                        if verse_num not in text_parts:
                            text_parts[verse_num] = ''
                        text_parts[verse_num] += el.text or ''
                    for child in el:
                        if child.tag == 'verse':
                            if child.get('number'):
                                verse_num = int(child.get('number'))
                            elif child.get('eid'):
                                pass
                        else:
                            walk_children(child, verse_num, text_parts)
                        if child.tail:
                            if verse_num not in text_parts:
                                text_parts[verse_num] = ''
                            text_parts[verse_num] += child.tail or ''

                walk_children(elem, current_verse, text_parts)

                for vnum, txt in text_parts.items():
                    if vnum and txt.strip():
                        cleaned = clean_text(txt)
                        if cleaned:
                            chapter_verses[current_chapter][vnum] = cleaned

        # Insert into text_resources
        for chapter, verses in chapter_verses.items():
            for verse, text in sorted(verses.items()):
                verse_id = f"{book_id}.{chapter}.{verse}"
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'LSV', ?, 'eng')",
                        (verse_id, text)
                    )
                    total += 1
                except Exception as e:
                    print(f"  ERROR: {verse_id}: {e}")
                    errors += 1
                    if errors > 100:
                        print("  Too many errors, aborting")
                        conn.close()
                        return

        # Mark as default for verses that don't have WEB
        print(f"  {usx_code} ({book_id}): {sum(len(v) for v in chapter_verses.values())} verses")

    conn.commit()
    conn.close()
    print(f"\nImported {total} verses, {errors} errors")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/import_lsv.py /path/to/USX_1_directory")
        sys.exit(1)
    import_lsv(sys.argv[1])
