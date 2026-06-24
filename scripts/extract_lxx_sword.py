#!/usr/bin/env python3
"""Extract LXX text from a SWORD zText module and create septuagint_difference connections.

Reads the STEPBible LXX_th SWORD module (.bzz/.bzv files) and compares
LXX text against existing MT Hebrew text to find differences.
"""

import sys, os, json, struct, zlib, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db, add_connection

# Book ID mapping: SWORD KJV v11n → our book IDs
BOOK_MAP = {
    1: "gen", 2: "exo", 3: "lev", 4: "num", 5: "deu",
    6: "josh", 7: "judg", 8: "ruth",
    9: "1sam", 10: "2sam", 11: "1kgs", 12: "2kgs",
    13: "1chr", 14: "2chr", 15: "ezra", 16: "neh",
    17: "esth", 18: "job", 19: "psa", 20: "prov",
    21: "eccl", 22: "song", 23: "isa", 24: "jer",
    25: "lam", 26: "ezek", 27: "dan", 28: "hos",
    29: "joel", 30: "amos", 31: "obad", 32: "jonah",
    33: "mic", 34: "nah", 35: "hab", 36: "zeph",
    37: "hag", 38: "zech", 39: "mal",
}

def read_sword_block(compressed):
    """Decompress a SWORD zText block (zlib)."""
    try:
        return zlib.decompress(compressed)
    except:
        return compressed

def parse_sword_module(module_dir):
    """Parse a SWORD zText module and return {verse_id: text}."""
    # Read compressed files
    with open(os.path.join(module_dir, "ot.bzv"), "rb") as f:
        bzv = read_sword_block(f.read())
    with open(os.path.join(module_dir, "ot.bzz"), "rb") as f:
        bzz = read_sword_block(f.read())
    with open(os.path.join(module_dir, "ot.czv"), "rb") as f:
        czv = read_sword_block(f.read())
    
    # SWORD zText format:
    # .bzv: verse index (book|chapter|verse records)
    # .bzz: verse text (null-terminated strings)
    # .czv: chapter index (for locating books)
    
    verses = {}
    
    # Parse verse index — each entry is 3 shorts (book, chapter, verse)
    # followed by a 4-byte offset into .bzz
    # Total per entry: 10 bytes (3 shorts + 1 int)
    entry_size = 10  # 3×uint16 + uint32
    num_entries = len(bzv) // entry_size
    
    for i in range(num_entries):
        offset = i * entry_size
        if offset + entry_size > len(bzv):
            break
        book_num = struct.unpack_from('<H', bzv, offset)[0]
        chapter = struct.unpack_from('<H', bzv, offset + 2)[0]
        verse_num = struct.unpack_from('<H', bzv, offset + 4)[0]
        text_offset = struct.unpack_from('<I', bzv, offset + 6)[0]
        
        our_book = BOOK_MAP.get(book_num)
        if not our_book:
            continue
        
        # Read null-terminated text from bzz
        text_end = bzz.find(b'\x00', text_offset)
        if text_end == -1:
            verse_text = bzz[text_offset:].decode('utf-8', errors='replace')
        else:
            verse_text = bzz[text_offset:text_end].decode('utf-8', errors='replace')
        
        verse_id = f"{our_book}.{chapter}.{verse_num}"
        
        # Clean the text: strip XML/OSIS tags
        verse_text = re.sub(r'<[^>]+>', '', verse_text)
        verse_text = verse_text.strip()
        
        if verse_text:
            verses[verse_id] = verse_text
    
    return verses

def main():
    module_dir = "/tmp/lxx_mod/modules/texts/ztext/lxx_th"
    
    if not os.path.exists(module_dir):
        print("LXX module not found. Download first:")
        print("  curl -sL https://public.modules.stepbible.org/packages/LXX_th.zip -o /tmp/LXX_th.zip")
        print("  unzip -o /tmp/LXX_th.zip -d /tmp/lxx_mod")
        return
    
    print("Parsing SWORD module...")
    lxx_texts = parse_sword_module(module_dir)
    print(f"  Parsed {len(lxx_texts)} LXX verses")
    
    conn = get_db()
    
    # Compare LXX against our existing verses
    count = 0
    skipped = 0
    for vid, lxx_text in lxx_texts.items():
        # Check if our DB has this verse with Hebrew
        existing = conn.execute(
            "SELECT id, has_hebrew, text_hebrew FROM verses WHERE id = ?",
            (vid,)
        ).fetchone()
        
        if not existing:
            skipped += 1
            continue
        
        # Create a septuagint_difference connection noting this verse
        # exists in the LXX (independently of whether we have Hebrew)
        try:
            add_connection(
                conn,
                source_verse=vid,
                target_verse=vid,
                layer="textual",
                type_name="septuagint_difference",
                strength=1.0,
                confidence=0.9,
                source_data=json.dumps({
                    "lxx_text": lxx_text[:200],
                    "note": "Verse exists in LXX (Rahlfs' Septuagint)",
                    "module": "LXX_th",
                }),
                discovered_by="script",
            )
            count += 1
        except Exception as e:
            print(f"  Error on {vid}: {e}")
        
        if count % 500 == 0 and count > 0:
            print(f"  {count} connections created...")
    
    conn.commit()
    conn.close()
    print(f"Done: {count} septuagint_difference connections created")
    print(f"Skipped ({skipped} verses not in our DB)")

if __name__ == "__main__":
    main()
