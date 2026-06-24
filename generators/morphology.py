"""Morphology generator — same_morphology connections.

Connects verses that share a rare morphological form (same verb stem,
tense, person, number, noun gender/number/state, etc.).

Uses the WLC/Treebank morphological codes in the gematria.morph column.
Content-word forms (verbs, nouns, adjectives, adverbs) appearing in
2-50 verses are considered significant.

Uses hub-and-spoke pattern for groups > 10 verses to avoid O(n²) explosion.
"""

from collections import defaultdict


# Prefixes indicating content words (skip function words like prepositions,
# conjunctions, particles, pronouns)
CONTENT_PREFIXES = ("HV", "HN", "HA", "HD")

# Maximum verse count for a morph pattern to be considered rare
MAX_VERSE_COUNT = 50

# Hub-and-spoke threshold: for groups larger than this, use hub-and-spoke
# instead of full mesh
HUB_THRESHOLD = 10


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Connect verses sharing rare morphological forms.

    For each content-word morph pattern appearing in 2-50 verses,
    connect verses that contain a word with that pattern.

    Returns count of connections created.
    """
    count = 0
    batch = []

    # Step 1: Find verse IDs per morph pattern (content words only)
    # Filter content-word prefixes in SQL for efficiency
    prefix_conditions = " OR ".join(
        f"g.morph LIKE '{p}%'" for p in CONTENT_PREFIXES
    )

    query = f"""
        SELECT g.morph, g.verse_id
        FROM gematria g
        WHERE (g.morph != '' AND ({prefix_conditions}))
    """
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        query += f" AND g.verse_id LIKE ?"

    rows = conn.execute(query).fetchall()
    print(f"    Processing {len(rows)} content-word morph rows...", flush=True)

    # Group verses by morph pattern
    morph_groups = defaultdict(set)
    for r in rows:
        verse_id = r[1]
        morph_groups[r[0]].add(verse_id)

    print(f"    Found {len(morph_groups)} unique morph patterns", flush=True)

    # Step 2: Connect verses within each morph group
    processed = 0
    skipped_common = 0
    skipped_range = 0

    for morph, verses in morph_groups.items():
        size = len(verses)

        # Skip tiny groups (only 1 verse) and very common patterns
        if size < 2:
            continue
        if size > MAX_VERSE_COUNT:
            skipped_common += 1
            continue

        processed += 1
        verse_list = sorted(verses)

        # Rarer patterns get higher strength
        strength = round(min(0.8, 0.35 + 0.01 * (MAX_VERSE_COUNT - size)), 2)

        if size <= HUB_THRESHOLD:
            # Full mesh for small groups
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    batch.append((
                        verse_list[i], verse_list[j], "linguistic",
                        "same_morphology", morph, strength, 0.6, "algorithm",
                        '{"morph": "' + morph + '", "verse_count": ' + str(size) + '}'
                    ))
                    count += 1

                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
        else:
            # Hub-and-spoke for larger groups
            hub = verse_list[0]
            for v in verse_list[1:]:
                batch.append((
                    hub, v, "linguistic",
                    "same_morphology", morph, strength, 0.6, "algorithm",
                    '{"morph": "' + morph + '", "verse_count": ' + str(size) + '}'
                ))
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

        if processed % 200 == 0:
            print(f"    {processed} morph groups processed ({count} connections)...", flush=True)

    if batch:
        _batch_insert(conn, batch)

    print(f"  Morphology: {count} connections from {processed} morph patterns "
          f"(skipped {skipped_common} too common, {skipped_range} out of range)")
    return count
