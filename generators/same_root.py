"""Same-root generator — connects verses sharing a Hebrew root.

Connects verses that use DIFFERENT lemmas from the same root family
(e.g., connects a verse using "melek" (king) with a verse using
"malkah" (queen) because they share the root מלך).

Does NOT connect verses using the same lemma — that's what same_lemma does.
"""

from collections import defaultdict


def run(conn, book_ids=None):
    """Connect verses that use DIFFERENT lemmas sharing a Hebrew root.

    For each root with 2-10 member lemmas, hub-and-spoke connect verses
    from different lemmas. Limits to first 5 lemmas and 30 verses per lemma
    to keep connections meaningful.

    Returns count of connections created.
    """
    count = 0

    # Step 1: Get roots with 2-10 member lemmas from lexicon
    root_lemmas = conn.execute("""
        SELECT root_letters, GROUP_CONCAT(lemma) as lemmas
        FROM lexicon
        WHERE root_letters IS NOT NULL AND root_letters != ''
        GROUP BY root_letters
        HAVING COUNT(*) BETWEEN 2 AND 10
    """).fetchall()

    # Step 2: Get ALL lemma→verse mappings in one query
    all_mappings = conn.execute("""
        SELECT DISTINCT g.lemma, g.verse_id
        FROM gematria g
        WHERE g.lemma IS NOT NULL AND g.lemma != ''
    """).fetchall()

    # Build in-memory index
    lemma_to_verses = defaultdict(set)
    for r in all_mappings:
        lemma_to_verses[r["lemma"]].add(r["verse_id"])

    # Step 3: Connect verses from DIFFERENT lemmas within each root
    processed = 0
    batch = []

    for r in root_lemmas:
        root = r["root_letters"]
        lemmas = r["lemmas"].split(",")

        if len(lemmas) < 2:
            continue

        processed += 1

        # Collect verses per lemma (limit to first 5 lemmas, 30 verses each)
        lemma_verse_sets = []
        for lemma in lemmas[:5]:
            verses = lemma_to_verses.get(lemma, set())
            if len(verses) > 30:
                verses = set(sorted(verses)[:30])
            if verses:
                lemma_verse_sets.append(verses)

        if len(lemma_verse_sets) < 2:
            continue

        # Connect verses from DIFFERENT lemma sets only
        for i in range(len(lemma_verse_sets)):
            for j in range(i + 1, len(lemma_verse_sets)):
                for va in lemma_verse_sets[i]:
                    for vb in lemma_verse_sets[j]:
                        if va >= vb:
                            continue
                        batch.append((
                            va, vb, "linguistic",
                            "same_root", root, 0.4, 0.5, "algorithm",
                            '{"root": "' + root + '"}'
                        ))
                        count += 1

                        if len(batch) >= 500:
                            _batch_insert(conn, batch)
                            batch = []

        if processed % 500 == 0:
            print(f"    {processed} root families processed ({count} connections)...", flush=True)

    if batch:
        _batch_insert(conn, batch)

    print(f"  Same-root connections: {count} from {processed} root families")
    return count


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
