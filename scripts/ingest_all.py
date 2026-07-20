#!/usr/bin/env python3
"""
Batch ingest all missing texts: Philo, Josephus, 2 Baruch, Enuma Elish, Exagoge.

Usage:
  python3 scripts/ingest_all.py                    # Download and ingest all
  python3 scripts/ingest_all.py --download-only    # Only download, don't ingest
  python3 scripts/ingest_all.py --ingest-only      # Only ingest already-downloaded files
  python3 scripts/ingest_all.py --list             # List what's in the DB already
"""

import gzip
import json
import os
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
TEXT_DIR = BASE_DIR / "data" / "texts"
DB_PATH = DATA_DIR / "scripture.db"

# ── Text sources ──

SOURCES = [
    {
        "id": "josephus_antiquities",
        "work": "josephus",
        "work_title": "Josephus",
        "book": "antiquities",
        "book_title": "Antiquities of the Jews",
        "url": "https://www.gutenberg.org/files/2848/2848-0.txt",
        "chapters": 20,
    },
    {
        "id": "josephus_wars",
        "work": "josephus",
        "work_title": "Josephus",
        "book": "wars",
        "book_title": "The Wars of the Jews",
        "url": "https://www.gutenberg.org/files/2850/2850-0.txt",
        "chapters": 7,
    },
    {
        "id": "josephus_apion",
        "work": "josephus",
        "work_title": "Josephus",
        "book": "apion",
        "book_title": "Against Apion",
        "url": "https://www.gutenberg.org/files/2849/2849-0.txt",
        "chapters": 2,
    },
    {
        "id": "josephus_life",
        "work": "josephus",
        "work_title": "Josephus",
        "book": "life",
        "book_title": "The Life of Flavius Josephus",
        "url": "https://www.gutenberg.org/files/2846/2846-0.txt",
        "chapters": 1,
    },
    {
        "id": "philo",
        "work": "philo",
        "work_title": "Philo of Alexandria",
        "book": "philo_complete",
        "book_title": "Complete Works (Yonge Translation)",
        "url": "https://archive.org/stream/the-complete-works-of-philo-complete-and-unabridged/the-complete-works-of-philo-complete-and-unabridged_djvu.txt",
        "chapters": 36,
    },
    {
        "id": "baruch2",
        "work": "pseudepigrapha",
        "work_title": "Pseudepigrapha",
        "book": "baruch2",
        "book_title": "2 Baruch (Syriac Apocalypse)",
        "url": "https://www.pseudepigrapha.com/pseudepigrapha/2Baruch.html",
        "chapters": 87,
    },
    {
        "id": "enuma_elish",
        "work": "ane_texts",
        "work_title": "Ancient Near Eastern Texts",
        "book": "enuma_elish",
        "book_title": "Enuma Elish (Babylonian Creation Epic)",
        "url": "https://sacred-texts.com/ane/stc/stc.txt.gz",
        "chapters": 7,
    },
    {
        "id": "exagoge",
        "work": "hellenistic_jewish",
        "work_title": "Hellenistic Jewish Literature",
        "book": "exagoge",
        "book_title": "Ezekiel the Tragedian — Exagoge",
        "url": "https://archive.org/stream/eusebius-preparation-for-the-gospel-full-work-gifford-1903-trans/Eusebius%2C%20Preparation%20for%20the%20Gospel%20-%20English%20Translation%20%282%20vols%20in%201%20-%20Gifford%201903%20trans%29_djvu.txt",
        "chapters": 1,
    },
]


def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def download_all():
    """Download all source texts."""
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    
    for src in SOURCES:
        dest = TEXT_DIR / f"{src['id']}.txt"
        if dest.exists():
            print(f"  Already exists: {dest.name}")
            continue
        
        url = src["url"]
        print(f"  Downloading {dest.name} from {url[:80]}...")
        
        try:
            if url.endswith(".gz"):
                req = urllib.request.urlopen(url)
                compressed = req.read()
                text = gzip.decompress(compressed).decode("utf-8", errors="replace")
            else:
                req = urllib.request.urlopen(url)
                text = req.read().decode("utf-8", errors="replace")
            
            with open(dest, "w") as f:
                f.write(text)
            print(f"    Saved {len(text)} chars")
        except Exception as e:
            print(f"    FAILED: {e}")


def add_work(conn, work_id, title, subtitle=""):
    existing = conn.execute("SELECT id FROM works WHERE id = ?", (work_id,)).fetchone()
    if existing:
        return
    max_pos = conn.execute("SELECT MAX(position) as mp FROM works").fetchone()["mp"] or 0
    conn.execute("INSERT INTO works (id, title, subtitle, position) VALUES (?, ?, ?, ?)",
                 (work_id, title[:100], subtitle[:200], max_pos + 1))
    conn.commit()
    print(f"  Created work: {work_id}")


def add_book(conn, work_id, book_id, title, subtitle=""):
    existing = conn.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing:
        return
    max_pos = conn.execute("SELECT MAX(position) as mp FROM books WHERE work_id = ?", (work_id,)).fetchone()["mp"] or 0
    conn.execute("INSERT INTO books (id, work_id, title, subtitle, position) VALUES (?, ?, ?, ?, ?)",
                 (book_id, work_id, title[:100], subtitle[:200], max_pos + 1))
    conn.commit()


def add_verse(conn, book_id, chapter, verse, text):
    vid = f"{book_id}.{chapter}.{verse}"
    try:
        conn.execute(
            "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
            (vid, book_id, chapter, verse, text[:5000])
        )
        return True
    except sqlite3.Error:
        return False


def ingest_josephus(conn, src):
    """Parse Josephus text — books have chapters with numbered sections."""
    path = TEXT_DIR / f"{src['id']}.txt"
    if not path.exists():
        print(f"  File not found: {path}")
        return 0
    
    text = path.read_text(encoding="utf-8", errors="replace")
    
    work_id = src["work"]
    book_id = src["book"]
    add_work(conn, work_id, src["work_title"])
    add_book(conn, work_id, book_id, src["book_title"])
    
    # Josephus format: "BOOK I", "BOOK II", etc. with "CHAPTER 1", "CHAPTER 2", etc.
    # And verses numbered 1, 2, 3, etc.
    lines = text.split("\n")
    current_book = 1
    current_chapter = 1
    current_section = 1
    section_text = ""
    added = 0
    in_josephus = False
    
    for line in lines:
        stripped = line.strip()
        
        # Skip Gutenberg header/footer
        if "*** START OF" in stripped or "*** END OF" in stripped:
            in_josephus = "START" in stripped
            continue
        
        if not in_josephus:
            continue
        
        # Detect book headers
        book_match = re.match(r'^BOOK\s+([IVXLCDM]+)', stripped, re.IGNORECASE)
        if book_match:
            if section_text.strip():
                add_verse(conn, book_id, current_book, current_section, section_text.strip())
                added += 1
            current_book = _roman_to_int(book_match.group(1))
            current_chapter = 1
            current_section = 1
            section_text = ""
            continue
        
        # Detect chapter headers
        chap_match = re.match(r'^CHAPTER\s+(\d+)', stripped, re.IGNORECASE)
        if chap_match:
            if section_text.strip():
                add_verse(conn, book_id, current_book, current_section, section_text.strip())
                added += 1
            current_chapter = int(chap_match.group(1))
            current_section = 1
            section_text = ""
            continue
        
        # Detect section numbers (Whiston uses "1.", "2.", etc.)
        sec_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
        if sec_match and len(stripped) < 200:
            if section_text.strip():
                add_verse(conn, book_id, current_book, current_section, section_text.strip())
                added += 1
            current_section = int(sec_match.group(1))
            section_text = sec_match.group(2)
        else:
            if section_text:
                section_text += " " + stripped
            elif stripped:
                section_text = stripped
    
    if section_text.strip():
        add_verse(conn, book_id, current_book, current_section, section_text.strip())
        added += 1
    
    conn.commit()
    return added


def ingest_philo(conn, src):
    """Parse Philo text — treatises with numbered sections."""
    path = TEXT_DIR / f"{src['id']}.txt"
    if not path.exists():
        print(f"  File not found: {path}")
        return 0
    
    text = path.read_text(encoding="utf-8", errors="replace")
    
    work_id = src["work"]
    book_id = src["book"]
    add_work(conn, work_id, src["work_title"])
    add_book(conn, work_id, book_id, src["book_title"])
    
    # Philo has section numbers like "I.", "II." etc within treatises
    # We'll split by major sections
    lines = text.split("\n")
    current_chapter = 1
    current_section = 1
    section_text = ""
    added = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Skip very long lines (OCR artifacts, headers)
        if len(stripped) > 2000:
            continue
        
        # Try to detect section numbers (Roman numerals at start)
        sec_match = re.match(r'^([IVXLCDM]+)\.\s+(.*)', stripped)
        if sec_match and len(sec_match.group(1)) <= 5:
            if section_text.strip():
                add_verse(conn, book_id, current_chapter, current_section, section_text.strip()[:5000])
                added += 1
            current_section += 1
            section_text = sec_match.group(2)
        else:
            if section_text:
                section_text += " " + stripped
            elif stripped:
                section_text = stripped
    
    if section_text.strip():
        add_verse(conn, book_id, current_chapter, current_section, section_text.strip()[:5000])
        added += 1
    
    conn.commit()
    return added


def ingest_baruch2(conn, src):
    """Parse 2 Baruch — 87 chapters with numbered verses."""
    path = TEXT_DIR / f"{src['id']}.txt"
    if not path.exists():
        print(f"  File not found: {path}")
        return 0
    
    text = path.read_text(encoding="utf-8", errors="replace")
    
    work_id = src["work"]
    book_id = src["book"]
    add_work(conn, work_id, src["work_title"])
    add_book(conn, work_id, book_id, src["book_title"])
    
    # 2 Baruch format: chapters like "Chapter 1" with verse numbers "1."
    lines = text.split("\n")
    current_chapter = 1
    current_verse = 1
    verse_text = ""
    added = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Chapter headers
        chap_match = re.match(r'(?:CHAPTER|Chapter|CHAP\.?|Chap\.?)\s+(\d+)', stripped)
        if chap_match:
            if verse_text.strip():
                add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
                added += 1
            current_chapter = int(chap_match.group(1))
            current_verse = 1
            verse_text = ""
            continue
        
        # Verse numbers
        verse_match = re.match(r'^(\d+)\.\s*(.*)', stripped)
        if verse_match:
            if verse_text.strip():
                add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
                added += 1
            current_verse = int(verse_match.group(1))
            verse_text = verse_match.group(2)
        else:
            if verse_text:
                verse_text += " " + stripped
            elif stripped:
                verse_text = stripped
    
    if verse_text.strip():
        add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
        added += 1
    
    conn.commit()
    return added


def ingest_enuma_elish(conn, src):
    """Parse Enuma Elish — 7 tablets with line numbers."""
    path = TEXT_DIR / f"{src['id']}.txt"
    if not path.exists():
        # Try the gzipped version
        gz_path = TEXT_DIR / f"{src['id']}.txt.gz"
        if gz_path.exists():
            import gzip
            text = gzip.decompress(gz_path.read_bytes()).decode("utf-8", errors="replace")
            path.write_text(text)
        else:
            print(f"  File not found: {path} or {gz_path}")
            return 0
    
    text = path.read_text(encoding="utf-8", errors="replace")
    
    work_id = src["work"]
    book_id = src["book"]
    add_work(conn, work_id, src["work_title"])
    add_book(conn, work_id, book_id, src["book_title"])
    
    # Enuma Elish: Tablets I-VII with line numbers
    lines = text.split("\n")
    current_tablet = 1
    current_line = 1
    line_text = ""
    added = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("["):
            continue
        
        # Tablet headers
        tablet_match = re.match(r'(?:TABLET|Tablet)\s+([IVXLCDM]+)', stripped)
        if tablet_match:
            if line_text.strip():
                add_verse(conn, book_id, current_tablet, current_line, line_text.strip())
                added += 1
            current_tablet = _roman_to_int(tablet_match.group(1))
            current_line = 1
            line_text = ""
            continue
        
        # Line numbers
        line_match = re.match(r'^(\d+)\s+(.*)', stripped)
        if line_match:
            if line_text.strip():
                add_verse(conn, book_id, current_tablet, current_line, line_text.strip())
                added += 1
            current_line = int(line_match.group(1))
            line_text = line_match.group(2)
        else:
            if line_text:
                line_text += " " + stripped
    
    if line_text.strip():
        add_verse(conn, book_id, current_tablet, current_line, line_text.strip())
        added += 1
    
    conn.commit()
    return added


def ingest_exagoge(conn, src):
    """Extract Ezekiel the Tragedian's Exagoge from Eusebius."""
    path = TEXT_DIR / f"{src['id']}.txt"
    if not path.exists():
        print(f"  File not found: {path}")
        return 0
    
    text = path.read_text(encoding="utf-8", errors="replace")
    
    work_id = src["work"]
    book_id = src["book"]
    add_work(conn, work_id, src["work_title"])
    add_book(conn, work_id, book_id, src["book_title"])
    
    # Extract Book 9, chapters 28-29 from Eusebius
    # Look for "BOOK 9" or "BOOK IX" and then find the Ezekiel sections
    book9_start = None
    for pattern in [r'BOOK\s+IX', r'BOOK\s+9', r'Book\s+IX', r'Book\s+9']:
        m = re.search(pattern, text)
        if m:
            book9_start = m.start()
            break
    
    if not book9_start:
        print("  Could not find Book 9 in Eusebius text")
        return 0
    
    book9 = text[book9_start:]
    
    # Find chapters 28-29: look for "Ezekiel" references
    lines = book9.split("\n")
    in_exagoge = False
    current_chapter = 1
    current_verse = 1
    verse_text = ""
    added = 0
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        
        # Find the Exagoge fragments
        if "Ezekiel" in stripped and ("traged" in stripped.lower() or "Exagoge" in stripped or "Exagogue" in stripped):
            in_exagoge = True
        
        if in_exagoge:
            # Each fragment is numbered
            frag_match = re.match(r'^(\d+)\.\s+(.*)', stripped)
            if frag_match:
                if verse_text.strip():
                    add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
                    added += 1
                current_verse = int(frag_match.group(1))
                verse_text = frag_match.group(2)
            else:
                if verse_text:
                    verse_text += " " + stripped
        
        # Stop at next book
        if re.match(r'^BOOK\s+X', stripped) or re.match(r'^BOOK\s+10', stripped):
            break
    
    if verse_text.strip():
        add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
        added += 1
    
    conn.commit()
    return added


def _roman_to_int(s):
    """Convert Roman numeral to integer."""
    roman = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    s = s.upper().strip()
    result = 0
    for i in range(len(s)):
        if i + 1 < len(s) and roman.get(s[i], 0) < roman.get(s[i + 1], 0):
            result -= roman.get(s[i], 0)
        else:
            result += roman.get(s[i], 0)
    return result


def list_db():
    """List what's in the database."""
    conn = get_conn()
    works = conn.execute("SELECT id, title FROM works ORDER BY position").fetchall()
    for w in works:
        vc = conn.execute("""
            SELECT COUNT(*) as c FROM verses v 
            JOIN books b ON b.id = v.book_id 
            WHERE b.work_id = ?
        """, (w["id"],)).fetchone()["c"]
        print(f"  {w['id']:20s}: {w['title'][:50]} ({vc} verses)")
    conn.close()


def main():
    args = sys.argv[1:]
    
    if "--list" in args:
        print("\n=== Current Database ===")
        list_db()
        return
    
    download_only = "--download-only" in args
    ingest_only = "--ingest-only" in args
    
    if not ingest_only:
        print("\n=== Downloading texts ===")
        download_all()
    
    if download_only:
        return
    
    print("\n=== Ingesting texts ===")
    conn = get_conn()
    
    # Remove the exagoge from the main list — we handle it separately
    exagoge_src = SOURCES[-1]
    main_sources = SOURCES[:-1]
    
    for src in main_sources:
        print(f"\n  --- {src['book_title']} ---")
        
        if src["book"] == "antiquities" or src["book"] == "wars" or src["book"] == "apion" or src["book"] == "life":
            count = ingest_josephus(conn, src)
        elif src["book"] == "philo_complete":
            count = ingest_philo(conn, src)
        elif src["book"] == "baruch2":
            count = ingest_baruch2(conn, src)
        elif src["book"] == "enuma_elish":
            count = ingest_enuma_elish(conn, src)
        else:
            print(f"  No parser for {src['book']}")
            count = 0
        
        print(f"  Ingested {count} verses")
    
    # Handle Exagoge separately
    print(f"\n  --- {exagoge_src['book_title']} ---")
    count = ingest_exagoge(conn, exagoge_src)
    print(f"  Ingested {count} verses")
    
    conn.close()
    
    print("\n=== Final Database State ===")
    list_db()


if __name__ == "__main__":
    main()
