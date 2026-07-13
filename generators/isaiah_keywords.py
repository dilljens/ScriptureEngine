"""Isaiah keyword discovery — Hebrew root-based linking words.

Giliadi's method: find Hebrew words that appear in BOTH halves of the
seven-part antithetical structure. These words function as structural
keywords that link parallel passages, even if Giliadi never explicitly
named them as pseudonyms.

Also chains keywords transitively — if "forest" links A↔A' and "city"
links A'↔B (adjacent domino overlap), then "forest" is transitively
linked to "city", creating a keyword network across Isaiah.
"""

from collections import Counter

ISAIAH_BOOK = "isa"

# ─── Giliadi's Seven-Part Antithetical Structure ───
# Each pair: (name, first_half_start, first_half_end, second_half_start, second_half_end)
PARALLEL_PAIRS = [
    ("Ruin & Rebirth",        "isa.1.1",  "isa.5.30",  "isa.34.1",  "isa.35.10"),
    ("Rebellion & Compliance", "isa.6.1",  "isa.8.22",  "isa.36.1",  "isa.40.31"),
    ("Punishment & Deliverance","isa.9.1", "isa.12.6",  "isa.41.1",  "isa.46.13"),
    ("Humiliation & Exaltation","isa.13.1","isa.23.18", "isa.47.1",  "isa.47.15"),
    ("Suffering & Salvation",  "isa.24.1","isa.27.13", "isa.48.1",  "isa.54.17"),
    ("Disloyalty & Loyalty",   "isa.28.1","isa.31.9",  "isa.55.1",  "isa.59.21"),
    ("Disinheritance & Inheri","isa.32.1","isa.33.24", "isa.60.1",  "isa.66.24"),
]

# Adjacent domino pairs (for chaining): each pair's second half overlaps
# with the next pair's first half
DOMINO_OVERLAPS = [
    ("A→B",  "isa.5.30",  "isa.6.1"),    # end of pair 1 → start of pair 2
    ("B→C",  "isa.8.22",  "isa.9.1"),
    ("C→D",  "isa.12.6",  "isa.13.1"),
    ("D→E",  "isa.23.18", "isa.24.1"),
    ("E→F",  "isa.27.13", "isa.28.1"),
    ("F→G",  "isa.31.9",  "isa.32.1"),
    ("G→A'", "isa.33.24", "isa.34.1"),   # first half end → second half begin
    ("A'→B'","isa.35.10", "isa.36.1"),
    ("B'→C'","isa.40.31", "isa.41.1"),
    ("C'→D'","isa.46.13", "isa.47.1"),
    ("D'→E'","isa.47.15", "isa.48.1"),
    ("E'→F'","isa.54.17", "isa.55.1"),
    ("F'→G'","isa.59.21", "isa.60.1"),
]

# Hebrew lemmas that are too common to be meaningful linking words
STOP_LEMMAS = {
    "853", "5921", "5922", "3966", "3588", "3808", "4100",  # common particles
    "1697", "3068", "3069", "430", "3478", "1121", "6440",  # common nouns
    "3117", "776", "8064", "4325", "784", "376", # day, earth, heaven, water, fire, man
    "559", "1961", "6213", "1980", "7200", "8085", "3045",  # common verbs
    "5375", "5414", "7760", "1696", "7725", "7971", "413",  # more common verbs/particles
    "5921 a", "5922 a", "834 a", "3588 a", "1121 a",
    "6213 a", "3117 a",
    "l", "c/l", "c", "d", "b", "m", "k", "s", "i",          # prefix-only lemmas
}


def _verses_in_range(conn, start, end):
    """Get all verse IDs in a chapter/verse range."""
    p1 = start.split(".")
    p2 = end.split(".")
    book = p1[0]
    sc, sv = int(p1[1]), int(p1[2])
    ec, ev = int(p2[1]), int(p2[2])

    rows = conn.execute("""
        SELECT id FROM verses
        WHERE book_id = ? AND has_hebrew = 1
        AND (chapter > ? OR (chapter = ? AND verse >= ?))
        AND (chapter < ? OR (chapter = ? AND verse <= ?))
    """, (book, sc, sc, sv, ec, ec, ev)).fetchall()
    return [r["id"] for r in rows]


def _lemmas_in_range(conn, verse_ids):
    """Get all lemmas appearing in a set of verses, with frequency."""
    if not verse_ids:
        return Counter()

    placeholders = ",".join("?" for _ in verse_ids)
    rows = conn.execute(f"""
        SELECT lemma, COUNT(DISTINCT verse_id) as c
        FROM gematria
        WHERE verse_id IN ({placeholders})
          AND lemma IS NOT NULL AND lemma != ''
        GROUP BY lemma
    """, verse_ids).fetchall()

    return Counter({r["lemma"]: r["c"] for r in rows})


def _normalize_lemma(raw):
    """Strip prefixes like c/, d/, l/ to get base lemma."""
    if not raw:
        return ""
    # Strip letter prefix followed by /
    if "/" in raw:
        return raw.split("/")[-1].strip()
    return raw.strip()


def discover_keywords(conn):
    """Discover Hebrew linking keywords from the parallel structure.

    For each antithetical pair, find lemmas that appear in BOTH halves,
    filtered for significance. These are the implicit structural keywords.

    Returns dict: stem → {pairs: [pair_names], hebrew: "..."}
    """
    # Additional Hebrew stop words to filter
    EXTRA_STOPS = {
        "1931", "הוא", "היא",  # he/she/it
        "2009", "הנה",         # behold (already in stop list as 2009? no)
        "3605", "כל", # all/every
        "5704", "עד",          # until
        "4310", "מי",          # who
        "4100", "מה",          # what
        "3808", "לא",          # not
        "3588", "כי",          # for/because
        "859", "אתה",          # you
        "595", "אנכי",         # I
        "3644", "כמו",         # like/as
        "1571", "גם",          # also
        "637", "אף",           # also/indeed
        "389", "אך",           # surely/but
        "408", "אל",           # not (prohibition)
        "5921", "על",          # upon
        "413", # to/toward
        "854", "את",           # with (prep)
        "996", "בין",          # between
        "310", "אחר",          # after
        "227", "אז",           # then
        "6256", "עת",          # time
        "3117", "יום",         # day
        "3915", "לילה",        # night
        "6440", "פנים",        # face
    }
    ALL_STOPS = STOP_LEMMAS | EXTRA_STOPS

    # Cache Hebrew words per stem for metadata
    stem_hebrew = {}
    for r in conn.execute("""
        SELECT lemma, word_hebrew
        FROM gematria
        WHERE word_hebrew IS NOT NULL AND word_hebrew != ''
          AND lemma IS NOT NULL AND lemma != ''
        GROUP BY lemma
    """).fetchall():
        stem = _normalize_lemma(r["lemma"])
        if stem and stem not in stem_hebrew:
            stem_hebrew[stem] = r["word_hebrew"][:10]

    all_keywords = {}

    for pair_name, h1_start, h1_end, h2_start, h2_end in PARALLEL_PAIRS:
        h1_verses = _verses_in_range(conn, h1_start, h1_end)
        h2_verses = _verses_in_range(conn, h2_start, h2_end)

        h1_lemmas = _lemmas_in_range(conn, h1_verses)
        h2_lemmas = _lemmas_in_range(conn, h2_verses)

        h1_stems = {_normalize_lemma(lemma) for lemma in h1_lemmas}
        h2_stems = {_normalize_lemma(lemma) for lemma in h2_lemmas}

        shared = h1_stems & h2_stems

        for stem in shared:
            if stem in ALL_STOPS or len(stem) < 2:
                continue
            if stem not in all_keywords:
                heb = stem_hebrew.get(stem, "")
                all_keywords[stem] = {"pairs": [], "hebrew": heb}
            all_keywords[stem]["pairs"].append(pair_name)

    return all_keywords


def generate_keyword_connections(conn):
    """Create connections for discovered structural keywords.

    For each keyword found in a parallel pair, connect verses from
    the first half to the second half where that keyword appears.
    """
    all_keywords = discover_keywords(conn)
    batch = []
    count = 0
    keyword_count = 0

    for stem, data in sorted(all_keywords.items()):
        pairs = data["pairs"]
        hebrew = data["hebrew"]
        if not pairs:
            continue
        keyword_count += 1

        for pair_name, h1_start, h1_end, h2_start, h2_end in PARALLEL_PAIRS:
            if pair_name not in pairs:
                continue

            # Find verses with this keyword in first half
            p1 = h1_start.split(".")
            p2 = h1_end.split(".")
            sc, sv = int(p1[1]), int(p1[2])
            ec, ev = int(p2[1]), int(p2[2])

            h1_matches = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = ? AND g.lemma LIKE ?
                  AND v.chapter >= ? AND v.chapter <= ?
                  AND (v.chapter > ? OR (v.chapter = ? AND v.verse >= ?))
                  AND (v.chapter < ? OR (v.chapter = ? AND v.verse <= ?))
                LIMIT 20
            """, (ISAIAH_BOOK, f"%{stem}%", sc, ec, sc, sc, sv, ec, ec, ev)).fetchall()

            # Find verses with this keyword in second half
            p1 = h2_start.split(".")
            p2 = h2_end.split(".")
            sc, sv = int(p1[1]), int(p1[2])
            ec, ev = int(p2[1]), int(p2[2])

            h2_matches = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = ? AND g.lemma LIKE ?
                  AND v.chapter >= ? AND v.chapter <= ?
                  AND (v.chapter > ? OR (v.chapter = ? AND v.verse >= ?))
                  AND (v.chapter < ? OR (v.chapter = ? AND v.verse <= ?))
                LIMIT 20
            """, (ISAIAH_BOOK, f"%{stem}%", sc, ec, sc, sc, sv, ec, ec, ev)).fetchall()

            h1_ids = [r["verse_id"] for r in h1_matches]
            h2_ids = [r["verse_id"] for r in h2_matches]

            if not h1_ids or not h2_ids:
                continue

            # Hub-and-spoke
            hub = h1_ids[0]
            for target in h2_ids:
                batch.append((
                    hub, target, "linguistic",
                    "keyword_linking", "isaiah_keyword",
                    0.5, 0.5, "algorithm",
                    f'{{"keyword": "{stem}", "hebrew": "{hebrew}", "pair": "{pair_name}", "type": "parallel_link", "book": "isa"}}'
                ))
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Isaiah keywords discovered: {keyword_count} stems, {count} connections")
    return count


def generate_domino_chains(conn):
    """Create domino chain connections — keywords that span adjacent pairs.

    If the SAME keyword appears in two adjacent parallel pairs, it creates
    a transitive bridge linking verses across those pairs. This produces
    "forest→city→people" patterns where shared keywords chain across the
    domino structure.

    For example: if keyword "righteousness" appears in both pair C (Isa 9-12)
    and pair C' (Isa 41-46), and also in the adjacent pair D (Isa 13-23),
    then righteousness chains from C→C'→D, linking all three sections.
    """
    all_keywords = discover_keywords(conn)
    batch = []
    count = 0
    pair_names = [p[0] for p in PARALLEL_PAIRS]

    for stem, data in all_keywords.items():
        pairs = data["pairs"]
        hebrew = data["hebrew"]
        if len(pairs) < 2:
            continue

        indices = sorted([i for i, pn in enumerate(pair_names) if pn in pairs])

        # Chain across ALL pair indices where this keyword appears
        for i in range(len(indices) - 1):
            idx_a, idx_b = indices[i], indices[i + 1]
            if idx_b - idx_a > 1:  # Only adjacent pairs
                continue

            pn1 = pair_names[idx_a]
            pn2 = pair_names[idx_b]

            # Get the whole first pair's range
            PARALLEL_PAIRS[idx_a][1]  # first half start
            PARALLEL_PAIRS[idx_a][4]  # second half end

            verses_a = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = ? AND g.lemma LIKE ?
                ORDER BY RANDOM()
                LIMIT 2
            """, (ISAIAH_BOOK, f"%{stem}%")).fetchall()

            verses_b = conn.execute("""
                SELECT DISTINCT g.verse_id
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = ? AND g.lemma LIKE ?
                ORDER BY RANDOM()
                LIMIT 2
            """, (ISAIAH_BOOK, f"%{stem}%")).fetchall()

            for va in verses_a:
                for vb in verses_b:
                    if va["verse_id"] >= vb["verse_id"]:
                        continue
                    batch.append((
                        va["verse_id"], vb["verse_id"], "linguistic",
                        "keyword_linking", "isaiah_domino_chain",
                        0.4, 0.4, "algorithm",
                        f'{{"keyword": "{stem}", "hebrew": "{hebrew}", "chain": ["{pn1}", "{pn2}"], "book": "isa"}}'
                    ))
                    count += 1

                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Domino chain links: {count}")
    return count


def run(conn, book_ids=None):
    """Run all Isaiah keyword discovery generators.

    Clears previous Isaiah keyword connections first for clean rebuild.
    """
    # Clear previous runs
    conn.execute("DELETE FROM connections WHERE subtype IN ('isaiah_keyword', 'isaiah_domino_chain')")
    conn.commit()
    total = 0
    total += generate_keyword_connections(conn)
    total += generate_domino_chains(conn)
    print(f"  Total Isaiah keyword connections: {total}")
    return total


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
