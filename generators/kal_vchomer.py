"""Kal v'Chomer (קל וחומר) — "Light and Heavy" rabbinic reasoning pattern.

The most common rabbinic hermeneutical principle. An argument from lesser to
greater: "If X is true of the lesser case, then certainly Y is true of the
greater case."

Keyword detection (algorithmic):
  - English: "how much more", "much more", "more than", "if... then... certainly"
  - Greek: "πόσῳ μᾶλλον" (poso mallon)
  - Hebrew: "אף כי" (af ki), "כי לא" (ki lo)

Creates connections between the base case (lesser/light) and the extended
case (greater/heavy) within the same verse context.
"""

import re
from lib.db import add_connection


# ─── Detection patterns ───

# English patterns — match "how much more", "much more", "more than" 
# within a verse, then connect the two clauses
ENGLISH_PATTERNS = [
    r'(how much more|much more|how much rather)',
    r'(if\s+.+?,?\s+(then\s+)?(how much more|much more|how much rather))',
    r'(more (than|abundantly|exceedingly))',
]

# Greek isopsephy patterns (stored in gematria_greek table)
# πόσῳ μᾶλλον = "by how much more" (poso mallon)
GREEK_PATTERNS = [
    'ποσω μαλλον',    # poso mallon — unaccented search
    'πολλῳ μαλλον',   # pollo mallon — "much more"
]

# Hebrew patterns (stored in gematria table)
# אף כי = af ki — "how much more" / "even how much more"
# כי לא = ki lo — "for not" (often in kal v'chomer constructions)
HEBREW_PATTERNS = [
    'אף כי',
    'אף כי לא',
]


def find_kal_vchomer_english(conn):
    """Scan English text for 'how much more' patterns.
    
    Creates connections between the two clauses of each kal v'chomer
    argument found in the same verse.
    """
    count = 0
    batch = []
    
    # Find verses matching "how much more" patterns
    for pattern in ENGLISH_PATTERNS:
        # Use the core pattern without the optional groups for LIKE matching
        simple_patterns = ['how much more', 'much more', 'how much rather', 'more than']
        for sp in simple_patterns:
            rows = conn.execute("""
                SELECT id, text_english, book_id, chapter, verse
                FROM verses
                WHERE text_english LIKE ?
                LIMIT 200
            """, (f'%{sp}%',)).fetchall()
            
            for r in rows:
                vid = r["id"]
                text = r["text_english"] or ""
                
                # Skip very short verses (likely false positives)
                if len(text) < 40:
                    continue
                
                # Split on the pattern marker
                lower_text = text.lower()
                
                # Try to find the split point
                split_patterns = ['how much more', 'how much rather', 'much more']
                split_idx = -1
                used_marker = ""
                
                for sp in split_patterns:
                    idx = lower_text.find(sp)
                    if idx >= 0:
                        split_idx = idx
                        used_marker = sp
                        break
                
                if split_idx < 0:
                    continue
                
                # Split into base case (before marker) and extended case (after marker)
                base_text = text[:split_idx].strip()
                extended_text = text[split_idx + len(used_marker):].strip()
                
                if not base_text or not extended_text:
                    continue
                
                # Create connection within the same verse
                # Connect clauses through self-reference
                subtype = f"kal_vchomer_{used_marker.replace(' ', '_')}"
                
                batch.append((
                    vid, vid,
                    "interpretive", "rabbinic_midrash", subtype,
                    0.5, 0.4, "algorithm",
                    f'{{"pattern": "Kal v\'Chomer", "marker": "{used_marker}", "lesser": "{base_text[:100]}", "greater": "{extended_text[:100]}", "method": "English keyword detection"}}'
                ))
                count += 1
                
                if len(batch) >= 100:
                    _batch_insert(conn, batch)
                    batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Kal v'Chomer English: {count} connections")
    return count


def find_kal_vchomer_greek(conn):
    """Scan Greek text for πόσῳ μᾶλλον / πολλῷ μᾶλλον patterns."""
    count = 0
    batch = []
    
    for pattern in GREEK_PATTERNS:
        rows = conn.execute("""
            SELECT DISTINCT v.id, v.text_english, v.text_greek
            FROM gematria_greek g
            JOIN verses v ON v.id = g.verse_id
            WHERE LOWER(g.word_greek) LIKE ?
            LIMIT 100
        """, (f'%{pattern}%',)).fetchall()
        
        for r in rows:
            vid = r["id"]
            # Connect the verse to itself as a kal v'chomer marker
            batch.append((
                vid, vid,
                "interpretive", "rabbinic_midrash", "kal_vchomer_greek",
                0.5, 0.45, "algorithm",
                f'{{"pattern": "Kal v\'Chomer", "method": "Greek keyword detection", "marker": "{pattern}"}}'
            ))
            count += 1
            
            if len(batch) >= 100:
                _batch_insert(conn, batch)
                batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Kal v'Chomer Greek: {count} connections")
    return count


def find_kal_vchomer_hebrew(conn):
    """Scan Hebrew text for אף כי / אף כי לא patterns."""
    count = 0
    batch = []
    
    for pattern in HEBREW_PATTERNS:
        rows = conn.execute("""
            SELECT DISTINCT v.id, v.text_english, v.text_hebrew
            FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            WHERE g.word_hebrew LIKE ?
            LIMIT 100
        """, (f'%{pattern}%',)).fetchall()
        
        for r in rows:
            vid = r["id"]
            batch.append((
                vid, vid,
                "interpretive", "rabbinic_midrash", f"kal_vchomer_hebrew",
                0.5, 0.45, "algorithm",
                f'{{"pattern": "Kal v\'Chomer", "method": "Hebrew keyword detection", "marker": "{pattern}"}}'
            ))
            count += 1
            
            if len(batch) >= 100:
                _batch_insert(conn, batch)
                batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Kal v'Chomer Hebrew: {count} connections")
    return count


def run(conn, book_ids=None):
    """Run all Kal v'Chomer detection methods."""
    total = 0
    
    # Clear previous runs
    conn.execute("DELETE FROM connections WHERE subtype LIKE 'kal_vchomer_%'")
    conn.commit()
    
    total += find_kal_vchomer_english(conn)
    total += find_kal_vchomer_greek(conn)
    total += find_kal_vchomer_hebrew(conn)
    
    print(f"  Total Kal v'Chomer connections: {total}")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
