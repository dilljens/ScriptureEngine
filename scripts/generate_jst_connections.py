#!/usr/bin/env python3
"""Batch generate inspired_revision connections for JST blocks.

Moses chapters 2-8 parallel Genesis 1-6 (expanded versions).
Abraham chapters 4-5 parallel Genesis 1-2 (alternate account).

Each connection maps JST verse → KJV verse with the revision type.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db

# Known chapter blocks: (jst_book, jst_ch_start, kjv_book, kjv_ch_start, num_ch)
BLOCKS = [
    ("moses", 2, "gen", 1, 7),   # Moses 2-8 = Genesis 1-6 (ch 8 is expansion of Gen 6:5-7:24)
    ("abraham", 4, "gen", 1, 2), # Abraham 4-5 = Genesis 1-2
]

# Verse-type mapping for known expansions
# (jst_book, jst_ch, jst_v) -> revision subtype
NOTABLE_VERSES = {
    ("moses", 1, 1): "moses_commission",
    ("moses", 1, 39): "gods_work_and_glory",
    ("moses", 7, 69): "zion_translated",
    ("moses", 8, 22): "noah_wickedness",
}


def run():
    conn = get_db()
    conn.execute("PRAGMA journal_mode=DELETE")
    
    total = 0
    
    for jst_book, jst_ch_start, kjv_book, kjv_ch_start, num_ch in BLOCKS:
        for offset in range(num_ch):
            jst_ch = jst_ch_start + offset
            kjv_ch = kjv_ch_start + offset
            
            jst_verses = conn.execute(
                "SELECT id, text_english FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
                (jst_book, jst_ch)
            ).fetchall()
            
            kjv_verses = conn.execute(
                "SELECT id, text_english FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
                (kjv_book, kjv_ch)
            ).fetchall()
            
            if not jst_verses or not kjv_verses:
                continue
            
            max_v = min(len(jst_verses), len(kjv_verses))
            
            for i in range(max_v):
                jst_id = jst_verses[i][0]
                kjv_id = kjv_verses[i][0]
                jst_text = jst_verses[i][1] or ''
                kjv_text = kjv_verses[i][1] or ''
                
                # Skip if either text is empty
                if not jst_text or not kjv_text:
                    continue
                
                # Calculate overlap to confirm this is a genuine parallel
                words_jst = set(jst_text.lower().split())
                words_kjv = set(kjv_text.lower().split())
                overlap = len(words_jst & words_kjv) / max(len(words_jst | words_kjv), 1)
                
                # Skip if text is very different (not parallel)
                if overlap < 0.15:
                    continue
                
                # Determine revision subtype
                key = (jst_book, jst_ch, i + 1)
                subtype = NOTABLE_VERSES.get(key, "jst_expansion")
                
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO connections
                            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                        VALUES (?, ?, 'textual', 'inspired_revision', ?, ?, ?, 'algorithm', ?)
                    """, (kjv_id, jst_id,  # source=KJV, target=JST
                          subtype,
                          round(0.5 + overlap * 0.3, 2),
                          round(0.55 + overlap * 0.3, 2),
                          json.dumps({"overlap": round(overlap, 2), "jst_book": jst_book, "jst_chapter": jst_ch, "kjv_book": kjv_book, "kjv_chapter": kjv_ch})))
                    total += 1
                except Exception:
                    pass
        
        print(f"  {jst_book}.{jst_ch_start}-{jst_ch_start+num_ch-1} → {kjv_book}.{kjv_ch_start}-{kjv_ch_start+num_ch-1}: {total} so far")
    
    conn.commit()
    print(f"\nTotal JST connections created: {total}")
    
    # Verify
    final = conn.execute("SELECT COUNT(*) FROM connections WHERE type='inspired_revision'").fetchone()[0]
    print(f"Final inspired_revision count: {final}")
    
    conn.close()


if __name__ == "__main__":
    run()
