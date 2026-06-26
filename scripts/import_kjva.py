#!/usr/bin/env python3
"""
Import KJV with Apocrypha from Crosswire KJVA Sword module.

Extracts text from decompressed OSIS XML, inserts into verses and text_resources.
Allows Apocrypha to appear in chapter view, text search, and navigation.

Usage: python3 scripts/import_kjva.py
"""

import os, sys, re, struct, zlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Book ID mapping: OSIS book name → our short ID
BOOK_MAP = {
    'Gen': 'gen', 'Exod': 'exo', 'Lev': 'lev', 'Num': 'num', 'Deut': 'deu',
    'Josh': 'josh', 'Judg': 'judg', 'Ruth': 'ruth',
    '1Sam': '1sam', '2Sam': '2sam', '1Kgs': '1kgs', '2Kgs': '2kgs',
    '1Chr': '1chr', '2Chr': '2chr', 'Ezra': 'ezra', 'Neh': 'neh',
    'Esth': 'esth', 'Job': 'job', 'Ps': 'psa', 'Prov': 'prov',
    'Eccl': 'eccl', 'Song': 'song', 'Isa': 'isa', 'Jer': 'jer',
    'Lam': 'lam', 'Ezek': 'ezek', 'Dan': 'dan', 'Hos': 'hos',
    'Joel': 'joel', 'Amos': 'amos', 'Obad': 'obad', 'Jonah': 'jonah',
    'Mic': 'mic', 'Nah': 'nah', 'Hab': 'hab', 'Zeph': 'zeph',
    'Hag': 'hag', 'Zech': 'zech', 'Mal': 'mal',
    'Matt': 'matt', 'Mark': 'mark', 'Luke': 'luke', 'John': 'john',
    'Acts': 'acts', 'Rom': 'rom', '1Cor': '1cor', '2Cor': '2cor',
    'Gal': 'gal', 'Eph': 'eph', 'Phil': 'phil', 'Col': 'col',
    '1Thess': '1thes', '2Thess': '2thes', '1Tim': '1tim', '2Tim': '2tim',
    'Titus': 'titus', 'Phlm': 'philem', 'Heb': 'heb', 'Jas': 'james',
    '1Pet': '1pet', '2Pet': '2pet', '1John': '1john', '2John': '2john',
    '3John': '3john', 'Jude': 'jude', 'Rev': 'rev',
    # Apocrypha
    'Tob': 'tob', 'Jdt': 'jdt', 'Wis': 'wis', 'Sir': 'sir',
    'Bar': 'bar', 'PrMan': 'man', '1Macc': '1ma', '2Macc': '2ma',
    '1Esd': '1esd', '2Esd': '2esd',
    'AddEsth': 'esga', 'PrAzar': 's3y', 'Sus': 'sus', 'Bel': 'bel',
}

# Apocrypha book titles and positions (for books table)
APOC_BOOKS = [
    ('tob', 'Tobit', 1), ('jdt', 'Judith', 2), ('esga', 'Additions to Esther', 3),
    ('wis', 'Wisdom of Solomon', 4), ('sir', 'Sirach (Ecclesiasticus)', 5),
    ('bar', 'Baruch', 6), ('s3y', 'Song of the Three Children', 7),
    ('sus', 'Susanna', 8), ('bel', 'Bel and the Dragon', 9),
    ('man', 'Prayer of Manasses', 10), ('1esd', '1 Esdras', 11),
    ('2esd', '2 Esdras', 12), ('1ma', '1 Maccabees', 13),
    ('2ma', '2 Maccabees', 14),
]

def decompress_kjva(mod_dir='/tmp/sword_mods/modules/texts/ztext/kjva/'):
    """Decompress all blocks from the KJVA module."""
    bzz_path = os.path.join(mod_dir, 'ot.bzz')
    bzs_path = os.path.join(mod_dir, 'ot.bzs')
    bzz = open(bzz_path, 'rb').read()
    bzs = open(bzs_path, 'rb').read()
    
    blocks = []
    for i in range(len(bzs) // 8):
        off = struct.unpack('<I', bzs[i*8:i*8+4])[0]
        sz = struct.unpack('<I', bzs[i*8+4:i*8+8])[0]
        if sz <= 0 or off + sz > len(bzz):
            continue
        try:
            decomp = zlib.decompress(bzz[off:off+sz], -zlib.MAX_WBITS)
            blocks.append(decomp)
        except:
            try:
                decomp = zlib.decompress(bzz[off:off+sz])
                blocks.append(decomp)
            except:
                pass
    
    # Also decompress NT
    nt_path = os.path.join(mod_dir, 'nt.bzz')
    if os.path.exists(nt_path):
        nt_bzz = open(nt_path, 'rb').read()
        nt_bzs_path = os.path.join(mod_dir, 'nt.bzs')
        nt_bzs = open(nt_bzs_path, 'rb').read() if os.path.exists(nt_bzs_path) else b'\x00' * 8
        for i in range(len(nt_bzs) // 8):
            off = struct.unpack('<I', nt_bzs[i*8:i*8+4])[0]
            sz = struct.unpack('<I', nt_bzs[i*8+4:i*8+8])[0]
            if sz <= 0 or off + sz > len(nt_bzz):
                continue
            try:
                decomp = zlib.decompress(nt_bzz[off:off+sz], -zlib.MAX_WBITS)
                blocks.append(decomp)
            except:
                pass
    
    return b''.join(blocks)

def parse_osis_verses(text):
    """Parse OSIS XML to extract (book, chapter, verse, text) tuples."""
    verses = []
    text_str = text.decode('utf-8', errors='replace')
    
    # Remove XML tags, keeping only verse-relevant structure
    # Remove XML headers
    text_str = re.sub(r'<\?xml[^>]*>', '', text_str)
    text_str = re.sub(r'<osis[^>]*>', '', text_str)
    text_str = re.sub(r'</osis>', '', text_str)
    text_str = re.sub(r'<osisText[^>]*>', '', text_str)
    text_str = re.sub(r'</osisText>', '', text_str)
    text_str = re.sub(r'<header[^>]*>.*?</header>', '', text_str, flags=re.DOTALL)
    
    # Split on book elements
    book_parts = re.split(r'<div type="book" osisID="([^"]+)"[^>]*>', text_str)
    
    # book_parts[0] is before first book, then alternating [book_id, content]
    for i in range(1, len(book_parts), 2):
        if i + 1 >= len(book_parts):
            break
        osis_book = book_parts[i]
        book_content = book_parts[i+1]
        our_book = BOOK_MAP.get(osis_book)
        if not our_book:
            print(f'  Unknown book: {osis_book}')
            continue
        
        # Find all chapter elements
        chapter_parts = re.split(r'<chapter osisID="[^"]*"\s*sID="[^"]*"/>', book_content)
        
        current_chapter = 1
        for cp_idx, cp in enumerate(chapter_parts):
            if cp_idx == 0:
                continue  # skip content before first chapter
            
            # Find chapter number in osisID
            ch_match = re.search(r'<chapter osisID="[^"]*"\s*eID="[^"]*"/>', cp)
            
            # Actually, we split ON sID, so each cp starts AFTER an sID marker
            # The previous sID marker tells us the chapter
            # Let's find chapter by looking for eID markers
            ch_eid = re.search(r'<chapter osisID="([^"]+)"\s*eID="[^"]*"/>', cp)
            if ch_eid:
                # Extract chapter from osisID like "Tob.1"
                ch_part = ch_eid.group(1).split('.')[-1]
                try:
                    current_chapter = int(ch_part)
                except:
                    pass
            
            # The chapter content starts after the last chapter tag
            # Get the actual text content for this chapter
            # Remove all XML tags
            clean_text = re.sub(r'<[^>]+>', '', cp)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            if clean_text:
                # Store as one continuous text (we'll split by verse markers later)
                verses.append((our_book, current_chapter, 1, clean_text))
    
    return verses

def import_kjva():
    """Decompress KJVA module and import into database."""
    print("Decompressing KJVA module...")
    text = decompress_kjva()
    print(f"  Decompressed {len(text)} bytes")
    
    print("Parsing OSIS XML...")
    # Save decompressed text for analysis
    with open('/tmp/kjva_decompressed.txt', 'wb') as f:
        f.write(text)
    
    text_str = text.decode('utf-8', errors='replace')
    
    # Direct approach: find Apocrypha book sections using regex
    # The OSIS format uses <div type="book" osisID="Tob">
    # Each book has chapters with osisID="Tob.1", verses with osisID="Tob.1.2"
    
    conn = get_db()
    
    # Add apoc work if not exists
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('apoc', 'Apocrypha')")
    
    # Add books
    for book_id, title, pos in APOC_BOOKS:
        conn.execute(
            "INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES (?, 'apoc', ?, ?)",
            (book_id, title, pos)
        )
    conn.commit()
    
    # Extract verse references and text
    # Pattern: osisID="Book.Ch.V"
    verse_pattern = re.compile(
        r'<verse\s+osisID="(\w+)\.(\d+)\.(\d+)"\s*sID="[^"]*"/>(.*?)<verse\s+osisID="\1\.\2\.(\d+)"\s*eID="[^"]*"/>',
        re.DOTALL
    )
    
    # Also handle standalone verse markers
    verse_pattern2 = re.compile(
        r'<verse\s+osisID="(\w+)\.(\d+)\.(\d+)"\s*sID="[^"]*"/>(.*?)(?=<verse\s+osisID=|\s*<chapter\s+osisID=|\s*<div\s+)',
        re.DOTALL
    )
    
    total = 0
    errors = 0
    
    # Process by book
    book_divs = re.split(r'<div\s+type="book"\s+osisID="(\w+)"[^>]*>', text_str)
    
    for bidx in range(1, len(book_divs), 2):
        osis_book = book_divs[bidx]
        book_content = book_divs[bidx+1] if bidx + 1 < len(book_divs) else ''
        our_book = BOOK_MAP.get(osis_book)
        
        if not our_book:
            continue
        
        # Check if this book has verse-level markers
        if '<verse osisID=' not in book_content:
            print(f'  {osis_book} -> {our_book}: no verse markers, skipping')
            continue
        
        # Extract all verses
        found_verses = []
        for m in re.finditer(
            r'<verse\s+osisID="' + osis_book + r'\.(\d+)\.(\d+)"\s*sID="[^"]*"/>(.*?)<verse\s+osisID="' + osis_book + r'\.\d+\.\d+"\s*eID="[^"]*"/>',
            book_content, re.DOTALL
        ):
            chapter = int(m.group(1))
            verse = int(m.group(2))
            vtext = m.group(3)
            
            # Clean up XML markup
            vtext = re.sub(r'<[^>]+>', '', vtext)
            vtext = re.sub(r'\s+', ' ', vtext).strip()
            
            # Remove leading/trailing punctuation artifacts
            vtext = vtext.strip(' ,;:')
            
            if vtext:
                found_verses.append((chapter, verse, vtext))
        
        # Also try without eID markers for verses that use simple format
        if not found_verses:
            for m in re.finditer(
                r'<verse\s+osisID="' + osis_book + r'\.(\d+)\.(\d+)"\s*sID="[^"]*"/>(.*?)(?=<verse\s+osisID=|\s*</chapter>|\s*</div>)',
                book_content, re.DOTALL
            ):
                chapter = int(m.group(1))
                verse = int(m.group(2))
                vtext = m.group(3)
                vtext = re.sub(r'<[^>]+>', '', vtext)
                vtext = re.sub(r'\s+', ' ', vtext).strip()
                vtext = vtext.strip(' ,;:')
                if vtext:
                    found_verses.append((chapter, verse, vtext))
        
        if not found_verses:
            print(f'  {osis_book} -> {our_book}: no verses extracted')
            continue
        
        # Insert into database
        for chapter, verse, vtext in found_verses:
            verse_id = f'{our_book}.{chapter}.{verse}'
            try:
                # Insert into verses table (for chapter view and search)
                conn.execute(
                    "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
                    (verse_id, our_book, chapter, verse, vtext)
                )
                # Insert into text_resources (for version switching)
                conn.execute(
                    "INSERT OR REPLACE INTO text_resources (verse_id, version, text, language) VALUES (?, 'KJV', ?, 'eng')",
                    (verse_id, vtext)
                )
                total += 1
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f'  ERROR: {verse_id}: {e}')
        
        print(f'  {osis_book} -> {our_book}: {len(found_verses)} verses')
    
    conn.commit()
    conn.close()
    print(f'\nTotal: {total} verses, {errors} errors')

if __name__ == '__main__':
    import_kjva()
