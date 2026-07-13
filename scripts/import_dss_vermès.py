#!/usr/bin/env python3
"""
Import DSS English from Vermès translation via Bibliotecapleyades HTML.

Covers: 1QS (4), CD (5), 1QSa (6), 1QM (7), 1QHa (8), Sabbath Songs (9),
        Genesis Apocryphon, pesharim, Florilegium, Messianic Anthology (10)

Usage: python3 scripts/import_dss_vermès.py
"""

import html as html_mod
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

BASE = "https://www.bibliotecapleyades.net/scrolls_deadsea/deadseascrolls_english/"

# Each page: (url_suffix, scroll_id, title, columns)
# columns = list of (column_marker, column_name)
PAGES = [
    ("04.htm", "1QS", "Community Rule", list(range(1, 12))),  # cols I-XI
    ("05.htm", "CD", "Damascus Document", list(range(1, 21))),
    ("06.htm", "1QSa", "Messianic Rule (1QSa)", list(range(1, 6))),
    ("07.htm", "1QM", "War Scroll", list(range(1, 20))),
    ("08.htm", "1QHa", "Hodayot (Thanksgiving Hymns)", list(range(1, 27))),
    ("09.htm", None, "Liturgical Fragments", None),  # multiple scrolls
    ("10.htm", None, "Bible Interpretation", None),  # multiple scrolls
]


def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.bibliotecapleyades.net/scrolls_deadsea/deadseascrolls_english/contents.htm',
    })
    resp = urllib.request.urlopen(req, timeout=30)
    raw = resp.read().decode('iso-8859-1')
    return raw


def extract_paragraphs(html):
    """Extract paragraphs from the Vermès HTML.

    Returns list of (text, has_column_marker, column_num) tuples.
    """
    paragraphs = []
    # Find all <p> tags with the right style
    for match in re.finditer(r'<P[^>]*style="margin-left:\s*80px[^"]*"[^>]*>(.*?)</P>', html, re.DOTALL | re.IGNORECASE):
        content = match.group(1)
        # Strip all HTML tags
        text = re.sub(r'<[^>]+>', '\n', content)
        # Decode HTML entities
        text = html_mod.unescape(text)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        if not text or len(text) < 20:
            continue

        # Check for column markers like <<I>>, <<II>>, etc.
        col_match = re.search(r'<<\s*(I{1,3}|IV|V|VI{0,3}|VII{0,3}|VIII{0,3}|IX|X{1,3})\s*>>', text)
        col_num = 0
        if col_match:
            roman = col_match.group(1)
            roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
                         'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12,
                         'XIII': 13, 'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17,
                         'XVIII': 18, 'XIX': 19, 'XX': 20, 'XXI': 21, 'XXII': 22}
            col_num = roman_map.get(roman, 0)

        if text:
            paragraphs.append((text, col_match is not None, col_num))

    return paragraphs


def assign_paragraphs_to_scrolls(html, page_title):
    """For composite pages (09, 10), detect which scroll each paragraph belongs to."""
    # These pages have sub-headings that indicate the scroll
    scroll_sections = []
    current_scroll = None
    current_text = []

    for match in re.finditer(r'<P[^>]*style="margin-left:\s*80px[^"]*"[^>]*>(.*?)</P>', html, re.DOTALL | re.IGNORECASE):
        content = match.group(1)
        text = re.sub(r'<[^>]+>', ' ', content)
        text = html_mod.unescape(text)
        text = re.sub(r'\s+', ' ', text).strip()

        # Detect sub-headings (larger/bold text indicating a new scroll)
        has_subheading = bool(re.search(r'<b>.*?</b>', content)) and '<font size="2"' not in content

        if has_subheading and len(text) < 100:
            # This is a section heading
            if current_scroll and current_text:
                scroll_sections.append((current_scroll, ' '.join(current_text)))
            current_scroll = text.strip()
            current_text = []
        elif '<font size="2"' in content and text and len(text) > 20:
            current_text.append(text)

    if current_scroll and current_text:
        scroll_sections.append((current_scroll, ' '.join(current_text)))

    return scroll_sections


def main():
    print("DSS English Import — Vermès (BibliotecaPleyades)")
    print("=" * 50)

    conn = get_db()
    total_paragraphs = 0
    total_updated = 0

    for url_suffix, scroll_id, title, _columns in PAGES:
        url = BASE + url_suffix
        print(f"\n{url_suffix}: {title}...", end=' ', flush=True)

        try:
            html = fetch(url)
            time.sleep(2)  # be nice to the server
        except Exception as e:
            print(f"FETCH ERROR: {e}")
            continue

        # Get page title from <title> tag
        page_title = ""
        t_match = re.search(r'<TITLE>(.*?)</TITLE>', html, re.IGNORECASE)
        if t_match:
            page_title = t_match.group(1)

        if scroll_id:
            # Single-scroll page (04-08)
            paragraphs = extract_paragraphs(html)

            # Skip introductory paragraphs — start from the first column marker
            first_col = 0
            for i, (_text, has_col, col_num) in enumerate(paragraphs):
                if has_col and col_num > 0:
                    first_col = i
                    break

            scroll_paragraphs = paragraphs[first_col:]
            print(f"{len(paragraphs)} paragraphs (skipping {first_col} intro, using {len(scroll_paragraphs)})")

            # Get existing verses for this scroll
            existing = conn.execute(
                "SELECT id, verse FROM verses WHERE book_id=? ORDER BY verse",
                (scroll_id,)
            ).fetchall()

            if not existing:
                print(f"  No verses in DB for {scroll_id}")
                continue

            # Map paragraphs to sequential lines
            n = min(len(existing), len(scroll_paragraphs))
            for i in range(n):
                verse_id = existing[i]['id']
                text, has_col, col_num = scroll_paragraphs[i]

                # Store as VERMES English
                conn.execute(
                    "UPDATE verses SET text_english=? WHERE id=?",
                    (text, verse_id)
                )
                conn.execute(
                    "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'VERMES', ?, 'eng')",
                    (verse_id, text)
                )
                total_updated += 1

            total_paragraphs += n
            print(f"  Mapped {n}/{len(existing)} lines")

        else:
            # Composite page (09, 10) — multiple scrolls
            sections = assign_paragraphs_to_scrolls(html, page_title)
            print(f"{len(sections)} sections")

            for section_title, section_text in sections:
                # Try to identify which scroll this is
                section_lower = section_title.lower()

                book_id = None
                if 'angelic liturgy' in section_lower or 'sabbath' in section_lower or 'heavenly lights' in section_lower:
                    book_id = '4Q400'  # Songs of the Sabbath Sacrifice
                elif 'genesis apocryphon' in section_lower:
                    book_id = '1Q20'
                elif 'commentary on habakkuk' in section_lower or 'pesher habakkuk' in section_lower:
                    book_id = '1QpHab'
                elif 'midrash on the last days' in section_lower or 'florilegium' in section_lower:
                    book_id = '4Q174'
                elif 'messianic anthology' in section_lower:
                    book_id = '4Q521'  # or 4Q246
                elif 'blessings of jacob' in section_lower:
                    book_id = '4Q252'  # 4Q Patriarchal Blessings
                elif 'words of moses' in section_lower:
                    book_id = '1Q22'
                elif 'prayer of nabonidus' in section_lower:
                    book_id = '4Q242'
                elif 'commentary on hosea' in section_lower:
                    book_id = '4Q166'
                elif 'commentary on micah' in section_lower:
                    book_id = '4Q168'
                elif 'commentary on nahum' in section_lower:
                    book_id = '4Q169'
                elif 'commentaries on psalm' in section_lower:
                    book_id = '4Q171'  # 4QpPs37
                elif 'commentary on biblical laws' in section_lower:
                    book_id = '4Q251'

                if book_id:
                    # Check if this scroll exists in our DB
                    existing = conn.execute(
                        "SELECT id, verse FROM verses WHERE book_id=? ORDER BY verse",
                        (book_id,)
                    ).fetchall()
                    if existing:
                        # Store the section text in the first verse's text_resources
                        conn.execute(
                            "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'VERMES', ?, 'eng')",
                            (existing[0]['id'], section_text)
                        )
                        conn.execute("UPDATE verses SET text_english=? WHERE id=?", (section_text, existing[0]['id']))
                        total_updated += 1
                        print(f"    {book_id}: mapped {len(section_text)} chars to verse {existing[0]['id']}")
                else:
                    print(f"    Could not identify: {section_title[:60]}")

        conn.commit()

    # Make VERMES the default text_resource for DSS verses that have it
    conn.execute("""
        UPDATE text_resources SET is_default = 1
        WHERE verse_id LIKE 'dss.%' AND version = 'VERMES'
    """)
    conn.commit()

    # Verify
    dss_eng = conn.execute("""SELECT COUNT(*) FROM verses v
        WHERE v.book_id IN (SELECT id FROM books WHERE work_id='dss')
        AND v.text_english != ''""").fetchone()[0]
    vermes_count = conn.execute("""SELECT COUNT(*) FROM text_resources
        WHERE verse_id LIKE 'dss.%' AND version='VERMES'""").fetchone()[0]

    print(f"\n{'='*50}")
    print(f"Imported: {total_updated} English entries across {total_paragraphs} paragraphs")
    print(f"DSS verses with English: {dss_eng}")
    print(f"VERMES text_resources: {vermes_count}")
    conn.close()


if __name__ == '__main__':
    main()
