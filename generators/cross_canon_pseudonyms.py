"""Cross-canon pseudonym detection — applies Giliadi's keyword methodology
to non-Isaiah books using Hebrew Strong's numbers and English translations.

For Hebrew books (OT prophets): search by Strong's lemma
For English books (BoM, D&C): search by English keyword translation
"""

# ─── OT PROPHETS WITH HEBREW ───
HEBREW_BOOKS = ['jer', 'ezek', 'dan', 'hos', 'joel', 'amos', 'obad', 'jonah', 'mic', 'nah', 'hab', 'zeph', 'hag', 'zech', 'mal']

# ─── BOOK OF MORMON ───
BOM_BOOKS = ['1ne', '2ne', 'jacob', 'enos', 'jarom', 'omni', 'wom', 'mosiah', 'alma', 'hel', '3ne', '4ne', 'morm', 'ether', 'moro']

# ─── D&C ───
DC_BOOKS = None  # All dc* books

# ─── HUB VERSES (same as Isaiah) ───
SERVANT_HUB = "isa.42.1"
TYRANT_HUB = "isa.10.5"

# ─── PSEUDONYM DATA ───
# Format: (name, strongs_nums, english_keywords, actor)
# actor: 'servant', 'tyrant', or 'both'
PSEUDONYM_MAP = [
    # Twin-pair pseudonyms (same term, different actor)
    ("Hand", ["3027", "3225"], ["hand", "hands"], "both"),
    ("Ensign", ["5251"], ["ensign", "banner", "standard"], "both"),
    ("Rod", ["7626", "4294"], ["rod", "staff"], "both"),
    ("Staff", ["4938", "7626"], ["staff", "rod"], "both"),
    ("Sword", ["2719"], ["sword"], "both"),
    ("Fire", ["784"], ["fire", "flame"], "both"),
    ("Mouth", ["6310"], ["mouth"], "both"),
    ("Voice", ["6963"], ["voice"], "both"),
    ("Light", ["216", "215"], ["light"], "servant"),
    ("Darkness", ["2822"], ["darkness"], "tyrant"),
    ("Sea", ["3220", "3221"], ["sea"], "both"),
    ("River", ["5104"], ["river", "flood", "stream"], "both"),
    ("Arm", ["2220"], ["arm"], "servant"),
    ("Breath", ["7307", "5397"], ["breath", "wind", "blast"], "both"),
    
    # Single-actor pseudonyms
    ("Anger", ["639"], ["anger", "angry"], "tyrant"),
    ("Wrath", ["5678", "2534"], ["wrath", "fury"], "tyrant"),
    ("Righteousness", ["6664", "6666"], ["righteousness", "righteous"], "servant"),
    ("Salvation", ["3467", "3444"], ["salvation", "salvation"], "servant"),
    ("Death", ["4194", "4191"], ["death"], "tyrant"),
    ("Yoke", ["5923"], ["yoke"], "tyrant"),
    ("Covenant", ["1285"], ["covenant"], "servant"),
    ("Trumpet", ["7782", "2689"], ["trumpet"], "servant"),
    ("Arrow", ["2671"], ["arrow"], "servant"),
    ("Witness", ["5707"], ["witness", "testimony"], "servant"),
]


def run(conn, book_ids=None):
    """Search non-Isaiah books for pseudonym keywords and connect to Isaiah hubs."""
    total = 0
    batch = []
    
    # Clear previous runs
    conn.execute("DELETE FROM connections WHERE subtype IN ('cross_canon_pseudonym')")
    conn.commit()
    
    for name, strongs, eng_keywords, actor in PSEUDONYM_MAP:
        # ── Hebrew OT Prophets ──
        for strong in strongs:
            for book in HEBREW_BOOKS:
                rows = conn.execute("""
                    SELECT DISTINCT g.verse_id
                    FROM gematria g
                    JOIN verses v ON v.id = g.verse_id
                    WHERE v.book_id = ? AND g.lemma LIKE ?
                    LIMIT 20
                """, (book, f"%{strong}%")).fetchall()
                
                for r in rows:
                    hub = TYRANT_HUB if actor == "tyrant" else SERVANT_HUB
                    vid = r["verse_id"]
                    if vid.startswith("isa."):
                        continue  # Skip Isaiah (already done)
                    batch.append((
                        hub, vid,
                        "symbolic", "name_symbolic", "cross_canon_pseudonym",
                        0.45, 0.4, "algorithm",
                        f'{{"pseudonym": "{name}", "actor": "{actor}", "source_book": "{book}", "match": "hebrew", "hub": "{hub}"}}'
                    ))
                    total += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        
        # ── English BoM + D&C ──
        for keyword in eng_keywords:
            # Search BoM
            for book in BOM_BOOKS:
                rows = conn.execute("""
                    SELECT id FROM verses
                    WHERE book_id = ? AND text_english LIKE ?
                    LIMIT 15
                """, (book, f"%{keyword}%")).fetchall()
                
                for r in rows:
                    hub = TYRANT_HUB if actor == "tyrant" else SERVANT_HUB
                    vid = r["id"]
                    batch.append((
                        hub, vid,
                        "symbolic", "name_symbolic", "cross_canon_pseudonym",
                        0.4, 0.35, "algorithm",
                        f'{{"pseudonym": "{name}", "actor": "{actor}", "source_book": "{book}", "match": "english", "hub": "{hub}"}}'
                    ))
                    total += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
            
            # Search D&C
            rows = conn.execute("""
                SELECT id FROM verses
                WHERE book_id LIKE 'dc%' AND text_english LIKE ?
                LIMIT 20
            """, (f"%{keyword}%",)).fetchall()
            
            for r in rows:
                hub = TYRANT_HUB if actor == "tyrant" else SERVANT_HUB
                vid = r["id"]
                batch.append((
                    hub, vid,
                    "symbolic", "name_symbolic", "cross_canon_pseudonym",
                    0.4, 0.35, "algorithm",
                    f'{{"pseudonym": "{name}", "actor": "{actor}", "source_book": "dc", "match": "english", "hub": "{hub}"}}'
                ))
                total += 1
                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []
    
    if batch:
        _batch_insert(conn, batch)
    
    print(f"  Cross-canon pseudonyms: {total} connections from {len(PSEUDONYM_MAP)} pseudonym terms")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
