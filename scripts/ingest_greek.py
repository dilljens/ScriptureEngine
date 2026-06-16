#!/usr/bin/env python3
"""Ingest SBL Greek New Testament into the database with isopsephy values."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.gematria_greek import compute_all


# SBLGNT BCV book code (01-27) → our book ID mapping
# The files use 61-87 prefixes, but the actual BCV field uses standard 01-27
SBLGNT_BOOK_MAP = {
    "01": "matt",  "02": "mark",  "03": "luke",  "04": "john",
    "05": "acts",  "06": "rom",   "07": "1cor",  "08": "2cor",
    "09": "gal",   "10": "eph",   "11": "phil",  "12": "col",
    "13": "1thes", "14": "2thes", "15": "1tim",  "16": "2tim",
    "17": "titus", "18": "philem","19": "heb",   "20": "james",
    "21": "1pet",  "22": "2pet",  "23": "1john", "24": "2john",
    "25": "3john", "26": "jude",  "27": "rev",
}


def parse_sblgnt_line(line):
    """Parse a single line from SBLGNT morph file.
    
    Format (space-delimited):
      BCV POS MORPH SURFACE WORD NORM LEMMA
      BCV = 6-digit book/chapter/verse (BBCCVV)
    """
    parts = line.strip().split()
    if len(parts) < 7:
        return None
    
    bcv = parts[0]
    pos = parts[1]       # Part of speech code
    morph = parts[2]     # Parsing code
    surface = parts[3]   # Text with punctuation
    word = parts[4]      # Word without punctuation
    normalized = parts[5]# Normalized form
    lemma = parts[6]     # Lemma (dictionary form)
    
    # Parse BCV
    try:
        sbl_book = bcv[0:2]
        chapter = int(bcv[2:4])
        verse = int(bcv[4:6])
    except (ValueError, IndexError):
        return None
    
    book_id = SBLGNT_BOOK_MAP.get(sbl_book)
    if not book_id:
        return None
    
    return {
        "book_id": book_id,
        "chapter": chapter,
        "verse": verse,
        "word": word,
        "lemma": lemma,
        "morph": f"{pos} {morph}".strip(),
    }


def process_book(conn, filepath):
    """Process one SBLGNT book file."""
    verses = {}  # verse_id → {english: str, greek_words: list}
    word_count = 0
    
    with open(filepath, 'r') as f:
        for line in f:
            parsed = parse_sblgnt_line(line)
            if not parsed:
                continue
            
            vid = f"{parsed['book_id']}.{parsed['chapter']}.{parsed['verse']}"
            
            if vid not in verses:
                verses[vid] = {
                    "greek_words": [],
                    "book_id": parsed["book_id"],
                    "chapter": parsed["chapter"],
                    "verse": parsed["verse"],
                }
            
            verses[vid]["greek_words"].append({
                "word": parsed["word"],
                "lemma": parsed["lemma"],
                "morph": parsed["morph"],
            })
            word_count += 1
    
    # Write to database
    verse_count = 0
    greek_gematria_count = 0
    
    for vid, data in verses.items():
        # Build Greek text string
        greek_text = " ".join(w["word"] for w in data["greek_words"])
        
        # Remove trailing punctuation that got concatenated
        greek_text = greek_text.replace(" ,", ",").replace(" .", ".").replace(" ;", ";")
        greek_text = greek_text.replace(" :", ":").replace(" -", "-")
        
        # Check verse exists in our DB
        exists = conn.execute("SELECT id FROM verses WHERE id = ?", (vid,)).fetchone()
        if not exists:
            continue
        
        # Update verses table
        conn.execute("""
            UPDATE verses SET text_greek = ?, has_greek = 1
            WHERE id = ?
        """, (greek_text, vid))
        
        # Insert Greek gematria for each word
        for idx, w in enumerate(data["greek_words"]):
            values = compute_all(w["word"])
            conn.execute("""
                INSERT INTO gematria_greek (verse_id, word_index, word_greek, lemma, morph,
                                           value_standard, value_ordinal, value_reduced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (vid, idx, w["word"], w["lemma"], w["morph"],
                  values["standard"], values["ordinal"], values["reduced"]))
            greek_gematria_count += 1
        
        verse_count += 1
        
        if verse_count % 100 == 0:
            conn.commit()
    
    conn.commit()
    return verse_count, greek_gematria_count


def main():
    print("=" * 60)
    print("Greek NT Ingestion — SBL Greek New Testament")
    print("=" * 60)
    
    sblgnt_dir = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "sblgnt")
    conn = get_db()
    
    total_verses = 0
    total_words = 0
    
    # Process each NT book
    sbl_files = sorted([
        f for f in os.listdir(sblgnt_dir) if f.endswith("-morphgnt.txt")
    ])
    
    for filename in sbl_files:
        book_code = filename.split("-")[1]  # "Mt", "Mk", etc.
        filepath = os.path.join(sblgnt_dir, filename)
        
        vc, wc = process_book(conn, filepath)
        total_verses += vc
        total_words += wc
        print(f"  {book_code:4s} ({filename}): {vc:4d} verses, {wc:5d} words")
    
    # Summary
    print("\n" + "=" * 60)
    greek_verses = conn.execute("SELECT COUNT(*) as c FROM verses WHERE has_greek=1").fetchone()["c"]
    greek_words = conn.execute("SELECT COUNT(*) as c FROM gematria_greek").fetchone()["c"]
    
    print(f"NT verses with Greek:    {greek_verses}")
    print(f"Greek words (isopsephy): {greek_words}")
    
    # Show sample
    print("\nSample: John 1:1 in Greek")
    row = conn.execute("""
        SELECT v.text_greek, v.text_english
        FROM verses v WHERE v.id = 'john.1.1'
    """).fetchone()
    if row:
        print(f"  Greek:   {row['text_greek']}")
        print(f"  English: {row['text_english']}")
    
    # Show isopsephy values for John 1:1
    print("\nIsopsephy for John 1:1:")
    words = conn.execute("""
        SELECT word_greek, lemma, value_standard
        FROM gematria_greek WHERE verse_id = 'john.1.1'
        ORDER BY word_index
    """).fetchall()
    for w in words:
        print(f"  {w['word_greek']:12s} (lemma: {w['lemma']:10s}) = {w['value_standard']}")
    
    total = sum(w["value_standard"] for w in words)
    print(f"  {'':12s} {'':13s} TOTAL: {total}")
    
    print("=" * 60)
    conn.close()


if __name__ == "__main__":
    main()
