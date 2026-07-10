#!/usr/bin/env python3
"""Generate self-referencing connections (intertextual) that the algorithm missed.

Targets known cross-canonical quotation blocks where one book explicitly
quotes another but the intertextual detector didn't catch it because:
  - It only checks 55 specific book pairs (BoM→OT not included)
  - The rare-word threshold is too high for adapted quotations
  - Cross-canon books aren't fully cross-checked

Known parallel blocks:
  1 Nephi 20-21   = Isaiah 48-49
  2 Nephi 12-24   = Isaiah 2-14
  2 Nephi 27      = Isaiah 29 (abridged)
  Jacob 6         = various (parable of vineyard)
  Mosiah 14       = Isaiah 53
  Mosiah 15       = Isaiah 53 (continued)
  D&C 29:10-11    = Malachi 4 (day of the Lord)
  D&C 110:13-16   = Malachi 4:5-6 (Elijah)
  D&C 42:45       = Isaiah 29:4
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db


# Known block-parallel book pairs: (source_book, source_ch_start, target_book, target_ch_start, num_chapters)
BLOCK_PARALLELS = [
    ("1ne", 20, "isa", 48, 2),
    ("2ne", 12, "isa", 2, 13),    # 2 Ne 12-24 = Isa 2-14
    ("mosiah", 14, "isa", 53, 2), # Mosiah 14-15 = Isaiah 53
]

# Known single-verse cross-references (verse_id, target_verse_id)
KNOWN_REFERENCES = [
    # D&C ↔ Malachi
    ("dc.110.13", "mal.4.5"),
    ("dc.110.14", "mal.4.6"),
    ("dc.29.11", "mal.4.1"),
    # D&C ↔ OT
    ("dc.76.22", "john.1.18"),
    ("dc.76.23", "acts.10.40"),
    ("dc.76.24", "job.38.7"),
    ("dc.76.41", "john.3.16"),
    ("dc.93.21", "john.1.14"),
    ("dc.93.29", "prov.8.23"),
    ("dc.1.6", "isa.29.14"),
    # Moses ↔ Genesis (JST expansions)
    ("moses.2.1", "gen.1.1"),
    ("moses.2.26", "gen.1.26"),
    ("moses.2.27", "gen.1.27"),
    ("moses.3.7", "gen.2.7"),
    ("moses.4.1", "gen.3.1"),
    ("moses.4.21", "gen.3.15"),
    ("moses.5.4", "gen.4.3"),
    ("moses.6.64", "gen.5.24"),
    # D&C ↔ Revelation
    ("dc.77.1", "rev.4.6"),
    ("dc.77.2", "rev.5.1"),
    ("dc.77.3", "rev.6.1"),
    ("dc.77.4", "rev.7.1"),
    ("dc.77.5", "rev.8.2"),
    ("dc.77.6", "rev.9.14"),
    ("dc.77.7", "rev.10.1"),
    ("dc.86.1", "matt.13.24"),
    ("dc.88.14", "john.1.9"),
    # BoM ↔ NT
    ("1ne.11.27", "matt.3.16"),
    ("1ne.11.32", "john.1.29"),
    ("1ne.13.40", "ezek.37.16"),
    ("mosiah.15.21", "1cor.15.22"),
    ("alma.7.12", "heb.4.15"),
    ("3ne.11.8", "acts.1.9"),
    ("3ne.12.1", "matt.5.1"),
    ("3ne.13.25", "matt.6.25"),
    # BoM ↔ OT prophets
    ("2ne.26.15", "isa.29.14"),
    ("2ne.6.6", "isa.49.22"),
    ("jacob.2.19", "prov.4.5"),
    ("alma.46.23", "gen.37.5"),
    ("hel.8.16", "deu.18.15"),
    ("3ne.29.1", "isa.29.14"),
    # ── Expanded D&C ↔ OT/NT references ──
    ("dc.42.45", "isa.29.4"),
    ("dc.43.25", "jer.6.19"),
    ("dc.49.6", "rev.14.6"),
    ("dc.56.16", "isa.5.8"),
    ("dc.58.42", "isa.43.25"),
    ("dc.63.21", "1pet.3.7"),
    ("dc.64.10", "matt.6.14"),
    ("dc.68.25", "deu.6.7"),
    ("dc.74.1", "1cor.7.14"),
    ("dc.76.12", "rev.4.1"),
    ("dc.84.6", "1kgs.19.8"),
    ("dc.89.5", "prov.20.1"),
    ("dc.101.17", "jer.31.17"),
    ("dc.101.24", "mal.4.1"),
    ("dc.104.13", "psa.24.1"),
    ("dc.107.1", "heb.5.6"),
    ("dc.112.10", "matt.10.40"),
    ("dc.121.45", "psa.24.4"),
    ("dc.124.28", "1kgs.8.27"),
    ("dc.124.39", "num.16.40"),
    ("dc.127.6", "1cor.15.29"),
    ("dc.128.16", "1cor.15.29"),
    ("dc.130.22", "john.14.16"),
    ("dc.132.19", "matt.22.30"),
    ("dc.133.8", "isa.40.3"),
    ("dc.133.13", "exod.15.8"),
    ("dc.136.1", "exod.13.21"),
    ("dc.138.2", "1pet.3.18"),
    ("dc.138.8", "john.5.25"),
    ("dc.138.17", "job.19.26"),
    # ── BoM ↔ NT ──
    ("1ne.10.19", "john.16.13"),
    ("2ne.2.25", "rom.5.12"),
    ("2ne.9.25", "luke.12.48"),
    ("2ne.25.23", "rom.3.20"),
    ("mosiah.16.9", "john.8.12"),
    ("alma.5.19", "psa.24.3"),
    ("alma.32.21", "heb.11.1"),
    ("3ne.27.20", "john.3.5"),
    ("moro.10.4", "james.1.5"),
    # ── Moses/Abraham ↔ OT ──
    ("moses.8.22", "gen.6.5"),
    ("abraham.3.22", "job.38.7"),
    ("abraham.2.8", "gen.12.1"),
    # ── BoM ↔ NT  (expanded) ──
    ("1ne.1.20", "acts.10.34"),
    ("1ne.14.7", "rev.14.6"),
    ("mosiah.3.8", "mic.5.2"),
    ("mosiah.3.13", "matt.9.6"),
    ("mosiah.3.19", "1cor.15.53"),
    ("mosiah.5.2", "2cor.3.18"),
    ("alma.5.9", "acts.16.34"),
    ("alma.5.14", "2cor.5.17"),
    ("alma.12.32", "gen.3.22"),
    ("alma.26.16", "luke.15.10"),
    ("alma.40.23", "1cor.15.42"),
    ("alma.41.11", "rom.8.7"),
    ("alma.42.10", "rom.5.12"),
    ("hel.5.12", "matt.7.24"),
    ("3ne.11.7", "matt.3.17"),
    ("ether.12.6", "heb.11.1"),
    ("moro.7.7", "matt.7.11"),
    # ── D&C ↔ OT/NT (expanded) ──
    ("dc.1.17", "rev.1.1"),
    ("dc.6.34", "matt.6.25"),
    ("dc.8.2", "1cor.2.11"),
    ("dc.9.8", "james.1.5"),
    ("dc.10.5", "matt.26.41"),
    ("dc.18.10", "luke.15.7"),
    ("dc.19.16", "matt.26.39"),
    ("dc.29.42", "gen.3.23"),
    ("dc.38.25", "eph.4.32"),
    ("dc.42.23", "matt.5.28"),
    ("dc.43.25", "isa.55.6"),
    ("dc.59.9", "exod.20.8"),
    ("dc.64.9", "matt.6.14"),
    ("dc.76.25", "isa.14.12"),
    ("dc.121.34", "luke.22.24"),
    ("dc.124.27", "1kgs.8.22"),
    ("dc.130.22", "acts.7.55"),
    # ── PGP ↔ OT (expanded) ──
    ("moses.1.1", "isa.6.1"),
    ("moses.1.39", "john.5.29"),
    ("moses.4.1", "john.8.44"),
    ("moses.7.30", "job.38.4"),
    ("abraham.3.22", "jer.1.5"),
    ("abraham.5.13", "gen.3.6"),
]


def process_block_parallels(conn):
    """Create direct_quotation connections for block-level chapter parallels."""
    count = 0
    for src_book, src_ch_start, tgt_book, tgt_ch_start, num_ch in BLOCK_PARALLELS:
        for offset in range(num_ch):
            src_ch = src_ch_start + offset
            tgt_ch = tgt_ch_start + offset
            
            src_verses = conn.execute(
                "SELECT id, text_english FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
                (src_book, src_ch)
            ).fetchall()
            
            tgt_verses = conn.execute(
                "SELECT id, text_english FROM verses WHERE book_id=? AND chapter=? ORDER BY verse",
                (tgt_book, tgt_ch)
            ).fetchall()
            
            max_v = min(len(src_verses), len(tgt_verses))
            for i in range(max_v):
                src_vid = src_verses[i][0]
                tgt_vid = tgt_verses[i][0]
                src_text = src_verses[i][1] or ''
                tgt_text = tgt_verses[i][1] or ''
                
                # Skip if both texts are empty
                if not src_text or not tgt_text:
                    continue
                
                # Calculate text overlap to confirm it's a genuine parallel
                src_words = set(src_text.lower().split())
                tgt_words = set(tgt_text.lower().split())
                overlap = len(src_words & tgt_words) / max(len(src_words | tgt_words), 1)
                
                if overlap > 0.3:
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO connections
                                (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                            VALUES (?, ?, 'intertextual', 'direct_quotation', 'canonical_parallel', ?, ?, 'algorithm', ?)
                        """, (src_vid, tgt_vid,
                              min(0.9, 0.4 + overlap * 0.5),
                              min(0.9, 0.4 + overlap * 0.5),
                              '{"source_book": "' + src_book + '", "target_book": "' + tgt_book + '", "overlap": ' + str(round(overlap, 2)) + ', "note": "Block parallel: ' + src_book + '.' + str(src_ch) + ' = ' + tgt_book + '.' + str(tgt_ch) + '"}'))
                        count += 1
                    except Exception:
                        pass
        
        print(f"  {src_book}.{src_ch_start}-{src_ch_start+num_ch-1} → {tgt_book}.{tgt_ch_start}-{tgt_ch_start+num_ch-1}: {count} connections so far")
    
    conn.commit()
    return count


def process_known_references(conn):
    """Create direct_quotation connections for known single-verse cross-references."""
    count = 0
    for src, tgt in KNOWN_REFERENCES:
        src_text = conn.execute("SELECT text_english FROM verses WHERE id=?", (src,)).fetchone()
        tgt_text = conn.execute("SELECT text_english FROM verses WHERE id=?", (tgt,)).fetchone()
        
        if not src_text or not tgt_text:
            continue
        
        src_words = set((src_text[0] or '').lower().split())
        tgt_words = set((tgt_text[0] or '').lower().split())
        overlap = len(src_words & tgt_words) / max(len(src_words | tgt_words), 1)
        
        try:
            conn.execute("""
                INSERT OR IGNORE INTO connections
                    (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
                VALUES (?, ?, 'intertextual', 'direct_quotation', 'known_cross_reference', ?, ?, 'llm', ?)
            """, (src, tgt,
                  min(0.85, 0.4 + overlap * 0.5),
                  min(0.9, 0.4 + overlap * 0.5),
                  '{"source_book": "' + src.split('.')[0] + '", "target_book": "' + tgt.split('.')[0] + '", "overlap": ' + str(round(overlap, 2)) + '}'))
            count += 1
        except Exception:
            pass
    
    conn.commit()
    return count


def main():
    print("=" * 60)
    print("  SELF-REFERENCING CONNECTION GENERATOR")
    print("=" * 60)
    
    conn = get_db()
    
    # Phase 1: Block-level chapter parallels
    print("\nPhase 1: Block parallels...")
    block_count = process_block_parallels(conn)
    print(f"  Total block parallel connections: {block_count}")
    
    # Phase 2: Known single-verse cross-references
    print("\nPhase 2: Known cross-references...")
    ref_count = process_known_references(conn)
    print(f"  Known reference connections: {ref_count}")
    
    # Phase 3: Clean up duplicate echo/allusion connections
    # If a direct_quotation already exists, don't create another
    # (handled by INSERT OR IGNORE)
    
    total = conn.execute("SELECT COUNT(*) FROM connections WHERE subtype IN ('canonical_parallel', 'known_cross_reference')").fetchone()[0]
    print(f"\nTotal self-reference connections created: {total}")
    conn.close()


if __name__ == "__main__":
    main()
