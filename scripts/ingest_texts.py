#!/usr/bin/env python3
"""
Ingest external texts into the scripture database.

Usage:
  # Ingest from a plain text file, auto-detecting structure
  python3 scripts/ingest_texts.py --file philo.txt --work hellenistic --book "Philo: On the Creation"
  
  # Ingest from URL (Project Gutenberg, Wikisource, etc.)
  python3 scripts/ingest_texts.py --url "https://..." --work hellenistic --book "Josephus: Antiquities"
  
  # Show all works currently in the database
  python3 scripts/ingest_texts.py --list-works
  
  # Batch ingestion from a directory of text files
  python3 scripts/ingest_texts.py --directory ./texts/ --work nag_hammadi
  
  # Download known texts by key
  python3 scripts/ingest_texts.py --known philo    # All of Philo
  python3 scripts/ingest_texts.py --known josephus # All of Josephus
  python3 scripts/ingest_texts.py --known all      # Everything available
"""

import json
import os
import re
import sqlite3
import sys
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"
DB_PATH = DATA_DIR / "scripture.db"

# ── Known text sources (public domain) ──

KNOWN_TEXTS = {
    "philo": {
        "works": "hellenistic",
        "source": "C.D. Yonge translation (1854-55), public domain",
        "books": [
            {"id": "philo_creation", "title": "On the Creation", "url": "https://raw.githubusercontent.com/...philo_creation.txt"},
            {"id": "philo_alleg1", "title": "Allegorical Interpretation 1", "url": ""},
            # Will fill from local files
        ],
    },
}


def get_conn():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def add_work(conn, work_id: str, title: str, subtitle: str = ""):
    """Add a new work to the works table."""
    existing = conn.execute("SELECT id FROM works WHERE id = ?", (work_id,)).fetchone()
    if existing:
        return existing["id"]
    
    # Find max position
    max_pos = conn.execute("SELECT MAX(position) as mp FROM works").fetchone()["mp"] or 0
    
    conn.execute(
        "INSERT INTO works (id, title, subtitle, position) VALUES (?, ?, ?, ?)",
        (work_id, title, subtitle, max_pos + 1),
    )
    conn.commit()
    print(f"  Added work: {work_id} — {title}")
    return work_id


def add_book(conn, work_id: str, book_id: str, title: str, subtitle: str = ""):
    """Add a book to a work."""
    existing = conn.execute("SELECT id FROM books WHERE id = ?", (book_id,)).fetchone()
    if existing:
        return existing["id"]
    
    max_pos = conn.execute("SELECT MAX(position) as mp FROM books WHERE work_id = ?", (work_id,)).fetchone()["mp"] or 0
    
    conn.execute(
        "INSERT INTO books (id, work_id, title, subtitle, position) VALUES (?, ?, ?, ?, ?)",
        (book_id, work_id, title, subtitle, max_pos + 1),
    )
    conn.commit()
    print(f"  Added book: {book_id} — {title}")
    return book_id


def add_verse(conn, book_id: str, chapter: int, verse: int, text: str):
    """Add a verse to the database."""
    verse_id = f"{book_id}.{chapter}.{verse}"
    existing = conn.execute("SELECT id FROM verses WHERE id = ?", (verse_id,)).fetchone()
    if existing:
        return False
    
    conn.execute(
        "INSERT INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
        (verse_id, book_id, chapter, verse, text),
    )
    return True


def ingest_text(conn, work_id: str, book_id: str, book_title: str, 
                text: str, work_title: str = "", work_subtitle: str = "",
                chapter_pattern: str = r"^[A-Z]+(\d+)", 
                verse_pattern: str = r"^(\d+)\.\s") -> dict:
    """
    Ingest a plain text into the database.
    
    Args:
        text: The full text content
        chapter_pattern: Regex to detect chapter breaks
        verse_pattern: Regex to detect verse numbers
    """
    add_work(conn, work_id, work_title or work_id, work_subtitle)
    add_book(conn, work_id, book_id, book_title)
    
    lines = text.split("\n")
    current_chapter = 1
    current_verse = 1
    verse_text = ""
    added = 0
    skipped = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Check for chapter header
        chapter_match = re.match(chapter_pattern, line, re.IGNORECASE)
        if chapter_match and len(line) < 60:
            # Save previous verse if any
            if verse_text.strip():
                add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
                added += 1
                verse_text = ""
            current_chapter = int(chapter_match.group(1))
            current_verse = 1
            continue
        
        # Check for verse number
        verse_match = re.match(verse_pattern, line)
        if verse_match:
            if verse_text.strip():
                add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
                added += 1
            current_verse = int(verse_match.group(1))
            verse_text = line[verse_match.end():].strip()
        else:
            if verse_text:
                verse_text += " " + line
            else:
                verse_text = line
    
    # Last verse
    if verse_text.strip():
        add_verse(conn, book_id, current_chapter, current_verse, verse_text.strip())
        added += 1
    
    conn.commit()
    return {"added": added, "skipped": skipped, "total_verses": added}


def list_works(conn):
    """List all works in the database."""
    works = conn.execute("SELECT id, title, subtitle, position FROM works ORDER BY position").fetchall()
    print(f"{'ID':15s} {'Title':40s} {'Books':6s} {'Verses':8s}")
    print("-" * 75)
    for w in works:
        bc = conn.execute("SELECT COUNT(*) as c FROM books WHERE work_id = ?", (w["id"],)).fetchone()["c"]
        vc = conn.execute("""
            SELECT COUNT(*) as c FROM verses v JOIN books b ON b.id=v.book_id WHERE b.work_id=?
        """, (w["id"],)).fetchone()["c"]
        print(f"{w['id']:15s} {w['title'][:38]:40s} {bc:6d} {vc:8d}")

def main():
    args = sys.argv[1:]
    
    if "--list-works" in args:
        conn = get_conn()
        list_works(conn)
        conn.close()
        return
    
    # Parse arguments
    file_path = None
    url = None
    work_id = None
    book_id = None
    book_title = None
    
    for i, arg in enumerate(args):
        if arg == "--file" and i+1 < len(args):
            file_path = args[i+1]
        elif arg == "--url" and i+1 < len(args):
            url = args[i+1]
        elif arg == "--work" and i+1 < len(args):
            work_id = args[i+1]
        elif arg == "--book" and i+1 < len(args):
            parts = args[i+1].split(":", 1)
            book_id = parts[0].strip().lower().replace(" ", "_").replace(":", "_")
            book_title = parts[-1].strip()
    
    if not work_id or not book_id:
        print("Usage: python3 scripts/ingest_texts.py --file <path> --work <work_id> --book '<book_id>: <title>'")
        print("       python3 scripts/ingest_texts.py --list-works")
        sys.exit(1)
    
    # Read text
    if file_path:
        with open(file_path, "r") as f:
            text = f.read()
    elif url:
        print(f"Fetching {url}...")
        req = urllib.request.urlopen(url)
        text = req.read().decode("utf-8")
    else:
        text = sys.stdin.read()
    
    print(f"Ingesting {len(text)} chars as {work_id}.{book_id}...")
    conn = get_conn()
    
    result = ingest_text(
        conn, work_id, book_id, book_title, text,
        work_title=work_id,
    )
    
    print(f"  Added {result['added']} verses ({result['skipped']} skipped)")
    conn.close()


if __name__ == "__main__":
    main()
