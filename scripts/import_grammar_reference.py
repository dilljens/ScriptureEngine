#!/usr/bin/env python3
"""Import Joüon's Hebrew Grammar as a searchable reference.

Reads the TSV from the cloned Joüon grammar repo and creates
a grammar_reference table in memorize.db for search/lookup.

Usage:
    python3 scripts/import_grammar_reference.py
"""

import csv
import json
import re
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"
JOUON_TSV = Path("/tmp/Joun-Hebrew-Grammar/data/jouon_grammaire.tsv")


def extract_hebrew_examples(html):
    """Extract Hebrew words from HTML span.heb elements."""
    heb_words = re.findall(r'<span class="heb"[^>]*>([^<]+)</span>', html)
    return heb_words[:10]  # limit to 10 examples per paragraph


def html_to_plain_text(html):
    """Strip HTML tags, keep structure."""
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]  # limit to 500 chars for summary


def extract_section_info(html):
    """Extract section and subsection info."""
    section = ""
    subsection = ""
    m = re.search(r'<h2>([^<]+)</h2>', html)
    if m:
        section = m.group(1).strip()
        # Try to extract just the section name
        parts = section.split('/')
        if len(parts) > 1:
            section = parts[0]
            subsection = parts[1] if len(parts) > 1 else ""
    return section, subsection


def main():
    if not JOUON_TSV.exists():
        print(f"Error: {JOUON_TSV} not found. Clone it first:")
        print("  git clone https://github.com/areopage/Joun-Hebrew-Grammar.git /tmp/Joun-Hebrew-Grammar")
        return

    conn = sqlite3.connect(str(MEM_DB))
    
    # Create the grammar reference table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS grammar_reference (
            paragraph_id INTEGER PRIMARY KEY,
            section TEXT,
            subsection TEXT,
            summary TEXT,
            hebrew_examples TEXT,
            html_content TEXT,
            has_details INTEGER DEFAULT 1
        )
    """)
    
    # Count existing
    existing = conn.execute("SELECT COUNT(*) FROM grammar_reference").fetchone()[0]
    if existing > 0:
        print(f"Grammar reference already has {existing} paragraphs. Delete table to re-import.")
        conn.close()
        return
    
    # Read TSV
    csv.field_size_limit(10 * 1024 * 1024)  # 10MB max field size
    
    count = 0
    with open(JOUON_TSV, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        for row in reader:
            if len(row) < 2:
                continue
            try:
                para_id = int(row[0])
                html = row[1]
            except (ValueError, IndexError):
                continue
            
            section, subsection = extract_section_info(html)
            summary = html_to_plain_text(html)
            heb_examples = extract_hebrew_examples(html)
            
            conn.execute(
                "INSERT OR REPLACE INTO grammar_reference (paragraph_id, section, subsection, summary, hebrew_examples, html_content) VALUES (?, ?, ?, ?, ?, ?)",
                (para_id, section, subsection, summary, json.dumps(heb_examples), html)
            )
            count += 1
    
    conn.commit()
    
    # Verify
    total = conn.execute("SELECT COUNT(*) FROM grammar_reference").fetchone()[0]
    sections = conn.execute("SELECT DISTINCT section FROM grammar_reference ORDER BY section").fetchall()
    
    conn.close()
    
    print(f"Imported {count} grammar paragraphs into {total} total")
    print(f"Sections: {[s[0] for s in sections]}")


if __name__ == '__main__':
    main()
