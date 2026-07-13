#!/usr/bin/env python3
"""Import Joseph Smith discourses / teachings as a searchable corpus.

Sources:
- Restoration Archives: https://www.restorationarchives.com/collections/people/joseph-smith/
- Words of Joseph Smith (Ehat & Cook, 1980) — archive.org PDFs
- Teachings of the Prophet Joseph Smith (1938) — public domain

Usage:
    python3 scripts/import_js_discourses.py
    python3 scripts/import_js_discourses.py --dry-run
"""

import contextlib
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "processed" / "scripture.db"

# Source URLs for JS discourses text
SOURCES = [
    {
        "name": "Words of Joseph Smith (Ehat & Cook)",
        "url": "https://causeofzion.home.blog/wp-content/uploads/2021/12/the-words-of-joseph-smith-original.pdf",
        "type": "pdf",
    },
    {
        "name": "Teachings of the Prophet Joseph Smith",
        "url": "https://www.restorationarchives.net/josephsmith/Teachings_of_the_Prophet_Joseph_Smith.pdf",
        "type": "pdf",
    },
    # The Joseph Smith Papers discourses are available web-only, no direct download
    # But we can add a manual import path for plain text files
]


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using pdftotext or fallback."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        pass

    # Fallback: try with Python libraries
    try:
        import PyPDF2
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        pass

    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        pass

    print("  WARNING: Cannot extract PDF text. Install pdftotext or PyPDF2.")
    return ""


def download_and_parse(source, dry_run=False):
    """Download a source PDF and extract text chunks."""
    print(f"\n  Source: {source['name']}")
    print(f"  URL: {source['url']}")

    if dry_run:
        print("  [dry-run] Would download and process")
        return []

    # Download PDF
    try:
        req = urllib.request.Request(source['url'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            pdf_data = resp.read()
    except Exception as e:
        print(f"  ERROR downloading: {e}")
        return []

    # Save to temp file and extract
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        f.write(pdf_data)
        pdf_path = f.name

    print(f"  Downloaded {len(pdf_data)} bytes")
    text = extract_text_from_pdf(pdf_path)

    # Clean up temp file
    os.unlink(pdf_path)

    if not text:
        return []

    print(f"  Extracted {len(text)} characters")

    # Split into discourse-sized chunks
    # Typically a discourse starts with a date or heading like "1839" or "DISCOURSE"
    sections = []

    # Try splitting by date patterns first
    date_patterns = [
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d+,\s+\d{4}',
        r'\b(18[3-5]\d)\b',  # Years 1830-1859
        r'DISC\s*\d+|DISCOURSE\s*\d+',
        r'HISTORY\s+OF\s+THE\s+CHURCH',
    ]

    current_section = []
    current_title = "Untitled"

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        # Check if this line starts a new discourse
        is_new = False
        for pat in date_patterns:
            if re.search(pat, line, re.IGNORECASE):
                is_new = True
                break

        if is_new and current_section:
            content = '\n'.join(current_section)
            if len(content) > 100:  # Only keep substantial sections
                sections.append({
                    "title": current_title,
                    "content": content,
                })
            current_section = []
            current_title = line[:100]

        current_section.append(line)

    # Last section
    if current_section:
        content = '\n'.join(current_section)
        if len(content) > 100:
            sections.append({
                "title": current_title,
                "content": content,
            })

    print(f"  Extracted {len(sections)} discourse sections")
    return sections


def main():
    dry_run = "--dry-run" in sys.argv

    print("=" * 60)
    print("Joseph Smith Discourses Import")
    print("=" * 60)

    all_sections = []
    for source in SOURCES:
        sections = download_and_parse(source, dry_run=dry_run)
        all_sections.extend(sections)

    if dry_run:
        print(f"\nWould import {len(all_sections)} discourse sections from {len(SOURCES)} sources")
        return

    # Store in database
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))

    # Create JS discourses table if needed
    conn.execute("""
        CREATE TABLE IF NOT EXISTS js_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            source TEXT,
            content TEXT,
            content_tsvector TEXT,
            year INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Add FTS index for search
    with contextlib.suppress(Exception):
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS js_texts_fts USING fts5(
                title, content, content=js_texts, content_rowid=id
            )
        """)

    inserted = 0
    for sec in all_sections:
        # Extract year if present
        year_match = re.search(r'(18[3-5]\d)', sec['title'])
        year = int(year_match.group(1)) if year_match else None

        conn.execute(
            "INSERT INTO js_texts (title, source, content, year) VALUES (?, ?, ?, ?)",
            (sec['title'][:200], SOURCES[0]['name'], sec['content'], year)
        )
        inserted += 1

    conn.commit()

    # Update FTS index
    try:
        conn.execute("""
            INSERT INTO js_texts_fts (rowid, title, content)
            SELECT id, title, content FROM js_texts
        """)
        conn.commit()
    except Exception:
        pass

    conn.close()

    print(f"\nImported {inserted} discourse sections")
    print(f"Sources: {', '.join(s['name'] for s in SOURCES)}")


if __name__ == "__main__":
    main()
