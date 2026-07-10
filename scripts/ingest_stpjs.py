#!/usr/bin/env python3
"""Ingest STPJS.pdf — Scriptural Teachings of the Prophet Joseph Smith.

Extracts ~11,000 scripture cross-references from the book and populates:
  - js_sources: one entry for the book
  - js_scripture_refs: each reference mapped to a verse in our DB
"""

import sys, os, re, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db

PDF_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "STPJS.pdf")
TEXT_PATH = "/tmp/stpjs.txt"

# ── Book abbreviation → book_id mapping ──
# Covers: OT, NT, BoM, D&C, PGP
BOOK_MAP = {
    # OT
    "Gen": "gen", "Gen.": "gen",
    "Ex": "exo", "Ex.": "exo",
    "Lev": "lev", "Lev.": "lev",
    "Num": "num", "Num.": "num",
    "Deut": "deu", "Deut.": "deu",
    "Josh": "josh", "Josh.": "josh",
    "Judg": "judg",
    "Ruth": "ruth",
    "1 Sam": "1sam", "1 Sam.": "1sam", "1Sam": "1sam",
    "2 Sam": "2sam", "2 Sam.": "2sam", "2Sam": "2sam",
    "1 Kgs": "1kgs", "1 Kgs.": "1kgs", "1Kgs": "1kgs",
    "2 Kgs": "2kgs", "2 Kgs.": "2kgs", "2Kgs": "2kgs",
    "1 Chr": "1chr", "1 Chr.": "1chr", "1Chr": "1chr",
    "2 Chr": "2chr", "2 Chr.": "2chr", "2Chr": "2chr",
    "Ezra": "ezra",
    "Neh": "neh", "Neh.": "neh",
    "Esth": "esth",
    "Job": "job",
    "Ps": "psa", "Ps.": "psa", "Psa": "psa",
    "Prov": "prov", "Prov.": "prov",
    "Eccl": "eccl",
    "Song": "song",
    "Isa": "isa", "Isa.": "isa",
    "Jer": "jer", "Jer.": "jer",
    "Lam": "lam", "Lam.": "lam",
    "Ezek": "ezek", "Ezek.": "ezek",
    "Dan": "dan", "Dan.": "dan",
    "Hos": "hos", "Hos.": "hos",
    "Joel": "joel",
    "Amos": "amos",
    "Obad": "obad",
    "Jonah": "jonah",
    "Mic": "mic",
    "Nah": "nah",
    "Hab": "hab",
    "Zeph": "zeph",
    "Hag": "hag",
    "Zech": "zech",
    "Mal": "mal",
    # NT
    "Matt": "matt", "Matt.": "matt", "Matt": "matt",
    "Mark": "mark",
    "Luke": "luke",
    "John": "john",
    "Acts": "acts", "Acts.": "acts",
    "Rom": "rom", "Rom.": "rom",
    "1 Cor": "1cor", "1 Cor.": "1cor", "1Cor": "1cor",
    "2 Cor": "2cor", "2 Cor.": "2cor", "2Cor": "2cor",
    "Gal": "gal", "Gal.": "gal",
    "Eph": "eph", "Eph.": "eph",
    "Phil": "phil", "Phil.": "phil", "Philip": "phil",
    "Col": "col", "Col.": "col",
    "1 Thes": "1thes", "1 Thes.": "1thes", "1Thes": "1thes", "1 Thess": "1thes",
    "2 Thes": "2thes", "2 Thes.": "2thes", "2Thes": "2thes", "2 Thess": "2thes",
    "1 Tim": "1tim", "1 Tim.": "1tim", "1Tim": "1tim",
    "2 Tim": "2tim", "2 Tim.": "2tim", "2Tim": "2tim",
    "Titus": "titus",
    "Philem": "philem",
    "Heb": "heb", "Heb.": "heb",
    "James": "james",
    "1 Pet": "1pet", "1 Pet.": "1pet", "1Pet": "1pet", "1 Peter": "1pet",
    "2 Pet": "2pet", "2 Pet.": "2pet", "2Pet": "2pet", "2 Peter": "2pet",
    "1 Jn": "1john", "1 Jn.": "1john", "1 John": "1john",
    "2 Jn": "2john", "2 Jn.": "2john", "2 John": "2john",
    "3 Jn": "3john", "3 Jn.": "3john", "3 John": "3john",
    "Jude": "jude",
    "Rev": "rev", "Rev.": "rev",
    # PGP
    "Moses": "moses",
    "Abr": "abraham", "Abr.": "abraham", "Abraham": "abraham",
    # BoM
    "1 Ne": "1ne", "1 Ne.": "1ne", "1Nephi": "1ne", "1 Nephi": "1ne",
    "2 Ne": "2ne", "2 Ne.": "2ne", "2Nephi": "2ne", "2 Nephi": "2ne",
    "Jacob": "jacob",
    "Enos": "enos",
    "Jarom": "jarom",
    "Omni": "omni",
    "W of M": "wom", "Wom": "wom",
    "Mosiah": "mosiah",
    "Alma": "alma",
    "Hel": "hel", "Hel.": "hel",
    "3 Ne": "3ne", "3 Ne.": "3ne", "3Nephi": "3ne", "3 Nephi": "3ne",
    "4 Ne": "4ne", "4 Ne.": "4ne", "4Nephi": "4ne", "4 Nephi": "4ne",
    "Morm": "morm", "Morm.": "morm",
    "Ether": "ether", "Ether.": "ether",
    "Moro": "moro", "Moro.": "moro",
    # D&C
    "D&C": "dc", "Sec": "dc",
}

# Normalize book abbreviation for lookup
def lookup_book(abbrev):
    """Look up a book abbreviation, return (book_id, is_dc) or None."""
    # Try exact match first
    if abbrev in BOOK_MAP:
        bid = BOOK_MAP[abbrev]
        return bid, bid == "dc"
    
    # Try with trailing period stripped
    if abbrev.endswith('.'):
        stripped = abbrev[:-1]
        if stripped in BOOK_MAP:
            bid = BOOK_MAP[stripped]
            return bid, bid == "dc"
    
    # Try without spaces
    no_space = abbrev.replace(' ', '')
    if no_space in BOOK_MAP:
        bid = BOOK_MAP[no_space]
        return bid, bid == "dc"
    
    return None, False


def _expand_verse_range(verse_part):
    """Expand a verse range like '44-48' or '12,14' into a list of ints.
    
    Handles: '44-48', '12,14', '12-15', '1,3,5', '1214' (if sep_omitted=True detected).
    Returns list of verse ints.
    """
    verses = set()
    parts = re.split(r'[,;]', verse_part)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        range_m = re.match(r'(\d+)\s*[-–]\s*(\d+)$', p)
        if range_m:
            start, end = int(range_m.group(1)), int(range_m.group(2))
            verses.update(range(start, end + 1))
        elif re.match(r'^\d+$', p):
            verses.add(int(p))
    return sorted(verses)


def parse_verse_ref(ref_text):
    """Parse a reference like 'Gen. 1:1' or 'D&C 132:19' into verse ID(s).
    
    Handles:
      - Single: 'Gen. 1:1' → [gen.1.1]
      - Range:  'Alma 5:12-14' → [alma.5.12, alma.5.13, alma.5.14]
      - List:   'D&C 98:12,15' → [dc98.98.12, dc98.98.15]
      - Numbered books: '1 Chr. 13:9-10' → [1chr.13.9, 1chr.13.10]
      - Chapter-only: 'Abraham 3' → [abraham.3.1]
      - D&C: 'D&C 132:19' → [dc132.132.19]
      - D&C (no verse): 'Sec. 88' → [dc88.88.1]
    
    Returns (list_of_verse_ids, is_valid) tuple.
    """
    ref_text = ref_text.strip()
    
    # D&C format: "D&C 132:19" or "D&C 98:12,15" or "Sec. 88"
    dc_match = re.match(r'(?:D&C|Sec)\s*\.?\s*(\d+)(?:[:.](\d[\d,;.\-\s]*\d|\d))?', ref_text)
    if dc_match:
        section = dc_match.group(1)
        raw_verse = dc_match.group(2)
        if raw_verse:
            # Strip leading zeros from compound issues: "12,15" stays, "1215" needs analysis
            raw_verse = re.sub(r'[^0-9,\-]', '', raw_verse)  # Remove dots, spaces
            verses = _expand_verse_range(raw_verse)
            if verses:
                return [f"dc{section}.{section}.{v}" for v in verses], True
        return [f"dc{section}.{section}.1"], True
    
    # Standard format: "Book Ch:V" — with optional number prefix (e.g., "1 Chr. 13:9-10")
    m = re.match(r'((?:[12]\s*)?[A-Za-z][A-Za-z\s.]+?)\s*(\d+):([\d,\-.\s]+)', ref_text)
    if m:
        book_abbrev = m.group(1).strip()
        chapter = int(m.group(2))
        raw_verse = m.group(3).strip()
        # Clean the verse part — remove trailing dots/spaces
        raw_verse = re.sub(r'\s+', '', raw_verse)
        raw_verse = re.sub(r'\.$', '', raw_verse)
        verses = _expand_verse_range(raw_verse)
        bid, is_dc = lookup_book(book_abbrev)
        if bid and verses:
            if is_dc:
                return [f"dc{chapter}.{chapter}.{v}" for v in verses], True
            return [f"{bid}.{chapter}.{v}" for v in verses], True
        # Even if range expansion fails, try single verse
        if bid and raw_verse.isdigit():
            v = int(raw_verse)
            if is_dc:
                return [f"dc{chapter}.{chapter}.{v}"], True
            return [f"{bid}.{chapter}.{v}"], True
    
    # Try just "Book Ch" (no verse) — with number prefix
    m2 = re.match(r'((?:[12]\s*)?[A-Za-z][A-Za-z\s.]+?)\s*(\d+)$', ref_text)
    if m2:
        book_abbrev = m2.group(1).strip()
        chapter = int(m2.group(2))
        bid, is_dc = lookup_book(book_abbrev)
        if bid:
            if is_dc:
                return [f"dc{chapter}.{chapter}.1"], True
            return [f"{bid}.{chapter}.1"], True
    
    return [], False


def extract_all_refs(text):
    """Extract all scripture references from the extracted text.
    
    Returns a set of (verse_id, original_ref) tuples.
    """
    refs = set()
    
    lines = text.split('\n')
    skip_until_content = True
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Skip front matter
        if skip_until_content:
            if line == "TEACHINGS" or "Title Page of The Book of Mormon" in line:
                skip_until_content = False
            continue
        
        # Remove leading footnote markers: "1. Alma 24:14" or "1 Acts 2:41" or "12. Alma 5:12"
        clean_line = re.sub(r'^\d+\.?\s*', '', line).strip()
        
        # Skip short lines that aren't refs
        if len(clean_line) < 3:
            continue
        
        # Find all book references in this line
        # Capture compound ranges too: "Alma 5:12-14", "D&C 98:12,15", "1 Chr. 13:9-10"
        for m in re.finditer(
            # D&C: D&C 132:19 or D&C 98:12,15
            r'(?:D&C|Sec)\s*\.?\s*\d+(?::[\d,\-.\s]+)?|'
            # Standard: Gen. 1:1, Alma 5:12-14, 1 Chr. 13:9-10  
            r'(?:[12]\s*)?[A-Z][a-z]+\.?\s*(?:\d+)(?::[\d,\-.\s]+)?',
            clean_line
        ):
            raw_ref = m.group(0).strip()
            
            # Clean up trailing punctuation/semicolons
            raw_ref = re.sub(r'[;,.\s]+$', '', raw_ref)
            
            # Skip if this looks like a page number or date
            if re.match(r'^\d+$', raw_ref):
                continue
            
            verse_ids, valid = parse_verse_ref(raw_ref)
            if valid and verse_ids:
                for vid in verse_ids:
                    refs.add((vid, raw_ref))
    
    return refs


def main():
    # Ensure text is extracted
    if not os.path.exists(TEXT_PATH):
        print("Extracting PDF text...")
        os.system(f"pdftotext '{PDF_PATH}' {TEXT_PATH}")
    
    with open(TEXT_PATH) as f:
        text = f.read()
    
    print(f"Loaded {len(text):,} characters")
    
    conn = get_db()
    
    # Create a single source entry for the book
    book_title = "Scriptural Teachings of the Prophet Joseph Smith"
    source_ref = "js.stpjs"
    
    existing = conn.execute("SELECT 1 FROM js_sources WHERE ref_id=?", (source_ref,)).fetchone()
    if not existing:
        # Extract first ~5000 chars as a sample of the text
        sample_text = text[:5000]
        conn.execute("""
            INSERT INTO js_sources (ref_id, title, date, source_type, location, source, text, metadata)
            VALUES (?, ?, '1938', 'writing', 'Salt Lake City, Utah', ?, ?, ?)
        """, (
            source_ref,
            book_title,
            "Compiled by Joseph Fielding Smith; annotated by Richard C. Galbraith. Originally published as 'Teachings of the Prophet Joseph Smith' (1938).",
            sample_text,
            json.dumps({"source": "STPJS.pdf", "full_text_chars": len(text), "notes": "Scriptural Teachings of the Prophet Joseph Smith - contains JS teachings organized by scripture reference."})
        ))
        conn.commit()
        print(f"Created source entry: {source_ref}")
    
    # Extract all scripture references
    print("Extracting scripture references...")
    refs = extract_all_refs(text)
    print(f"Found {len(refs)} unique scripture references")
    
    # Filter to only those that exist in our verses table
    valid_refs = []
    for verse_id, raw_ref in refs:
        exists = conn.execute("SELECT 1 FROM verses WHERE id=?", (verse_id,)).fetchone()
        if exists:
            valid_refs.append((verse_id, raw_ref))
    
    print(f"  {len(valid_refs)} match known verses")
    
    # Insert into js_scripture_refs
    count_inserted = 0
    count_skipped = 0
    batch = []
    
    for verse_id, raw_ref in valid_refs:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO js_scripture_refs (js_ref_id, verse_id, ref_type, certainty, notes)
                VALUES (?, ?, 'reference', 0.8, ?)
            """, (source_ref, verse_id, f"STPJS: {raw_ref}"))
            count_inserted += 1
        except Exception:
            count_skipped += 1
        
        if count_inserted % 1000 == 0:
            conn.commit()
            print(f"  ... {count_inserted} inserted")
    
    conn.commit()
    
    print(f"\nResults:")
    print(f"  Source: {source_ref} ({book_title})")
    print(f"  Total references extracted: {len(refs)}")
    print(f"  Valid (matching DB verses): {len(valid_refs)}")
    print(f"  Inserted into js_scripture_refs: {count_inserted}")
    print(f"  Skipped (duplicates): {count_skipped}")
    
    # Stats
    total_refs = conn.execute("SELECT COUNT(*) FROM js_scripture_refs").fetchone()[0]
    total_sources = conn.execute("SELECT COUNT(*) FROM js_sources").fetchone()[0]
    print(f"\nTotal js_sources: {total_sources}")
    print(f"Total js_scripture_refs: {total_refs}")
    
    conn.close()


if __name__ == "__main__":
    main()
