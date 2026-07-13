"""Semuchin (סמוכין) — adjacent verse connections.

Rabbinic principle: adjacent passages interpret each other. Two verses
or short passages that are next to each other and share rare keywords
may be intentionally juxtaposed.

This generator finds adjacent verse pairs within the same book that
share rare Hebrew lemmas, indicating a possible semuchin relationship.
"""

from collections import defaultdict


def run(conn, book_ids=None):
    """Connect adjacent verses that share rare lemmas.

    For each book, look at verse N and its neighbors (N-1, N+1, N+2).
    If they share a lemma that's relatively rare (appears < 100x in the canon),
    create a semuchin connection.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # Get all verse IDs ordered per book
    book_query = """
        SELECT id, book_id, chapter, verse
        FROM verses
        ORDER BY book_id, chapter, verse
    """
    verses = conn.execute(book_query).fetchall()

    # Build a map: verse_id → (book_id, chapter, verse)
    {v["id"]: (v["book_id"], v["chapter"], v["verse"]) for v in verses}

    # Group verses by book for adjacency checking
    by_book = defaultdict(list)
    for v in verses:
        if book_ids and v["book_id"] not in book_ids:
            continue
        by_book[v["book_id"]].append(v)

    # For each book, find adjacent pairs and check shared lemmas
    # Pre-load rare lemma frequency (appear in 2-100 verses)
    lemma_freq = conn.execute("""
        SELECT lemma, COUNT(DISTINCT verse_id) as freq
        FROM gematria
        WHERE lemma IS NOT NULL AND lemma != ''
        GROUP BY lemma
        HAVING freq BETWEEN 3 AND 100
    """).fetchall()
    rare_lemmas = {r["lemma"]: r["freq"] for r in lemma_freq}

    # Load all lemma→verse mappings for rare lemmas
    lemma_verses = conn.execute("""
        SELECT DISTINCT g.lemma, g.verse_id
        FROM gematria g
        WHERE g.lemma IS NOT NULL AND g.lemma != ''
    """).fetchall()

    verse_lemmas = defaultdict(set)
    for r in lemma_verses:
        if r["lemma"] in rare_lemmas:
            verse_lemmas[r["verse_id"]].add(r["lemma"])

    total_pairs = 0
    connected_pairs = 0

    for book, vlist in by_book.items():
        for i in range(len(vlist) - 1):
            va = vlist[i]["id"]
            vb = vlist[i + 1]["id"]
            total_pairs += 1

            # Check for shared rare lemmas
            va_lemmas = verse_lemmas.get(va, set())
            vb_lemmas = verse_lemmas.get(vb, set())
            shared = va_lemmas & vb_lemmas

            if len(shared) >= 1:
                batch.append((
                    va, vb, "structural",
                    "keyword_linking", "semuchin",
                    0.3 + 0.1 * min(len(shared), 5), 0.5, "algorithm",
                    f'{{"shared_lemmas": {len(shared)}, "book": "{book}"}}'
                ))
                connected_pairs += 1
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

    if batch:
        _batch_insert(conn, batch)

    print(f"  Semuchin: {connected_pairs}/{total_pairs} adjacent verse pairs share rare lemmas")
    return count


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
