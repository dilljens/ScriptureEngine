"""Inclusio Detection generator — finds repeated phrases bookending passages.

An inclusio (or inclusio) is a literary device where the same word or phrase
appears at the beginning and end of a section, marking it as a literary unit.
This generator scans for repeated phrases at chapter/section boundaries.

Uses the existing structural formula data and chapter-level text patterns.
"""

from collections import defaultdict

# ─── Known inclusio markers ───
# These are phrases commonly used to open and close literary units
INCLUSIO_PATTERNS = [
    # Torah
    ("These are the generations of", "toledot", "gen"),
    ("These are the names", "names", "exo"),
    # Historical formulas
    ("And it came to pass", "wayehi", "all"),
    ("And the LORD said", "wyomer", "all"),
    ("And God said", "wyomer_elohim", "all"),
    # Poetic formulas
    ("Blessed be the LORD", "baruch", "all"),
    ("Praise ye the LORD", "hallelujah", "all"),
    ("Hallelujah", "hallelujah", "all"),
    ("For the LORD is good", "ki_tov", "all"),
    ("His mercy endureth for ever", "hesed_olam", "all"),
    # Prophetic formulas
    ("The word of the LORD came", "dvar_adonai", "all"),
    ("Thus says the LORD", "ko_amar", "all"),
    ("Hear the word of the LORD", "shimu_dvar", "all"),
    ("In that day", "bayom_hahu", "all"),
    ("Behold, the days come", "hinei_yamim", "all"),
    ("The burden of", "masa", "all"),
    # Wisdom formulas
    ("The fear of the LORD", "yirat", "all"),
    ("Hear, O my son", "shema_bni", "all"),
    ("My son, hear", "bni_shma", "all"),
    # Temple formulas
    ("Holy, holy, holy", "kadosh", "all"),
    ("The glory of the LORD", "kvod_adonai", "all"),
    # NT formulas
    ("Verily, verily I say unto you", "amen_amen", "nt"),
    ("It is written", "kata_gegraptai", "all"),
    ("Fear not", "me_phobou", "all"),
    # BoM formulas
    ("And thus we see", "ve_hineh", "bom"),
    ("And it came to pass that", "wayehi", "bom"),
]


def run(conn, book_ids=None):
    """Detect inclusio patterns and create connections.

    For each known pattern, scans chapter boundaries for occurrences
    and connects opening → closing verses when the same formula appears
    at both ends of a section.
    """
    count = 0
    batch = []

    # Get all books
    conn.execute("""
        SELECT b.id, b.work_id FROM books b
        ORDER BY b.work_id, b.position
    """).fetchall()


    for pattern, name, scope in INCLUSIO_PATTERNS:
        # Find all verses with this pattern
        # Hebrew text
        heb_verses = []
        if scope in ("all", "ot", "bom"):
            rows = conn.execute(
                "SELECT id, book_id, chapter, verse FROM verses WHERE text_hebrew LIKE ? AND has_hebrew = 1 ORDER BY id",
                (f'%{pattern}%',)
            ).fetchall()
            heb_verses = [dict(r) for r in rows]

        # English text
        eng_verses = []
        if scope in ("all", "nt", "bom", "dc", "pgp"):
            rows = conn.execute(
                "SELECT id, book_id, chapter, verse FROM verses WHERE text_english LIKE ? ORDER BY id",
                (f'%{pattern}%',)
            ).fetchall()
            eng_verses = [dict(r) for r in rows]

        all_verses = heb_verses + eng_verses

        if len(all_verses) < 2:
            continue

        # Group by book and look for opening/closing uses
        by_book = defaultdict(list)
        for v in all_verses:
            by_book[v["book_id"]].append(v)

        for book_id, verses in by_book.items():
            if len(verses) < 2:
                continue

            # Get the first and last occurrences in this book
            verses.sort(key=lambda v: (v["chapter"], v["verse"]))
            first = verses[0]
            last = verses[-1]

            if first["id"] == last["id"]:
                continue

            # Only connect if the first occurrence is in the first 5 chapters
            # and the last in the last 5 chapters (avoids trivial connections)
            if first["chapter"] <= 5 and last["chapter"] >= 8:
                batch.append((
                    first["id"], last["id"],
                    "structural", "inclusio", name,
                    0.5, 0.45, "algorithm",
                    f'{{"pattern": "{pattern}", "book": "{book_id}", "first": "{first["id"]}", "last": "{last["id"]}"}}'
                ))
                count += 1

            if len(batch) >= 200:
                _flush(conn, batch)
                batch = []

    if batch:
        _flush(conn, batch)

    print(f"  Inclusio: {count} connections across {len(INCLUSIO_PATTERNS)} patterns")
    return count


def _flush(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
    batch.clear()
