"""Cross-canon chaos motif detection — applies Isaiah's de-creation
motifs to non-Isaiah books using Hebrew Strong's numbers and English.

Chaos motifs are terms Isaiah uses to describe God's de-creation of
wicked entities: dust, chaff, stubble, mire, clay, dross, smoke, etc.
"""

# ─── TARGET BOOKS ───
HEBREW_BOOKS = ['jer', 'ezek', 'dan', 'hos', 'joel', 'amos', 'obad', 'jonah', 'mic', 'nah', 'hab', 'zeph', 'hag', 'zech', 'mal']
BOM_BOOKS = ['1ne', '2ne', 'jacob', 'enos', 'jarom', 'omni', 'wom', 'mosiah', 'alma', 'hel', '3ne', '4ne', 'morm', 'ether', 'moro']

# ─── CHAOS MOTIFS ───
# Format: (name, strongs_nums, english_keywords, description)
CHAOS_MOTIFS = [
    ("dust", ["6083", "80"], ["dust", "ashes"], "Reduction to nothing"),
    ("chaff", ["4671", "2842"], ["chaff", "husk"], "Driven by wind"),
    ("stubble", ["7179"], ["stubble"], "Consumed by fire"),
    ("mire", ["2916", "1206"], ["mire", "mud", "clay"], "Sunk in degradation"),
    ("clay", ["2563", "2916"], ["clay", "potter"], "Molded and cast away"),
    ("dross", ["5509"], ["dross"], "Impurities smelted out"),
    ("refuse", ["5215"], ["refuse", "rubbish", "filth"], "Thrown away as worthless"),
    ("smoke", ["6227", "7008"], ["smoke"], "Vanishing pollution"),
    ("wind", ["7307", "7306"], ["wind", "vapor"], "Powerless scattering"),
    ("hail", ["1259", "68"], ["hail", "hailstone"], "Divine judgment"),
    ("straw", ["8401", "8402"], ["straw"], "Burned up"),
    ("waste", ["2723", "4875"], ["waste", "desolate", "desolation"], "Laid waste"),
]


def run(conn, book_ids=None):
    """Search non-Isaiah books for chaos motif keywords."""
    total = 0
    batch = []
    
    conn.execute("DELETE FROM connections WHERE subtype IN ('cross_canon_chaos')")
    conn.commit()
    
    for name, strongs, eng_keywords, desc in CHAOS_MOTIFS:
        # ── Hebrew OT Prophets ──
        for strong in strongs:
            for book in HEBREW_BOOKS:
                rows = conn.execute("""
                    SELECT DISTINCT g.verse_id
                    FROM gematria g
                    JOIN verses v ON v.id = g.verse_id
                    WHERE v.book_id = ? AND g.lemma LIKE ?
                    LIMIT 15
                """, (book, f"%{strong}%")).fetchall()
                
                for r in rows:
                    vid = r["verse_id"]
                    if vid.startswith("isa."):
                        continue
                    batch.append((
                        vid, "isa.24.1",
                        "linguistic", "same_lemma", "cross_canon_chaos",
                        0.35, 0.35, "algorithm",
                        f'{{"motif": "{name}", "description": "{desc}", "source_book": "{book}", "match": "hebrew"}}'
                    ))
                    total += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        
        # ── English BoM ──
        for keyword in eng_keywords:
            for book in BOM_BOOKS:
                rows = conn.execute("""
                    SELECT id FROM verses
                    WHERE book_id = ? AND text_english LIKE ?
                    LIMit 15
                """, (book, f"%{keyword}%")).fetchall()
                
                for r in rows:
                    vid = r["id"]
                    batch.append((
                        vid, "isa.24.1",
                        "linguistic", "same_lemma", "cross_canon_chaos",
                        0.3, 0.3, "algorithm",
                        f'{{"motif": "{name}", "description": "{desc}", "source_book": "{book}", "match": "english"}}'
                    ))
                    total += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
            
            # D&C
            rows = conn.execute("""
                SELECT id FROM verses
                WHERE book_id LIKE 'dc%' AND text_english LIKE ?
                LIMIT 15
            """, (f"%{keyword}%",)).fetchall()
            
            for r in rows:
                vid = r["id"]
                batch.append((
                    vid, "isa.24.1",
                    "linguistic", "same_lemma", "cross_canon_chaos",
                    0.3, 0.3, "algorithm",
                    f'{{"motif": "{name}", "description": "{desc}", "source_book": "dc", "match": "english"}}'
                ))
                total += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Cross-canon chaos: {total} connections from {len(CHAOS_MOTIFS)} motifs")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
