"""Linguistic generator — same_lemma connections.

Connects verses that share a rare Hebrew lemma (Strong's number).
Rare = appears in fewer than 10 verses across the canon.
This creates a web of connections between passages using the same
rare Hebrew word, which often indicates a meaningful intertextual link.
"""

from collections import defaultdict

# Skip very common lemmas that would create too many noisy connections
COMMON_LEMMAS = {
    "H853", "H5921", "H5922", "H3966", "H3588", "H3808", "H4100",
    "H1697", "H3068", "H430", "H3478", "H3069", "H1121", "H6440",
    "H3117", "H776", "H8064", "H4325", "H784",  # water, fire, etc.
    "H376", "H1320", "H5315",  # man, flesh, soul
    "H559", "H1961", "H6213", "H1980",  # said, was, did, went
    "H7200", "H8085", "H3045",  # said, saw, heard, knew
    "H5375", "H5414", "H7760",  # lift, put, set
    "H1696", # speak, word
    "H7725", "H7971",  # return, send
    "H3118",  # day, daily
    # YHWH, Elohim (too common)
    # Israel, children
    "H413",  # face, upon, to
}


def run(conn, book_ids=None, max_lemma_count=10):
    """Connect verses sharing rare Hebrew lemmas.

    For each lemma that appears between 2 and `max_lemma_count` verses,
    connect all verses that share it.

    Returns count of connections created.
    """
    count = 0

    # Step 1: Find all verse IDs per lemma
    # Only consider lemmas that appear in 2-10 verses
    lemma_verses = conn.execute("""
        SELECT g.lemma, g.verse_id
        FROM gematria g
        GROUP BY g.lemma, g.verse_id
    """).fetchall()

    # Group verses by lemma
    lemma_groups = defaultdict(set)
    for r in lemma_verses:
        lemma = r["lemma"].strip()
        if not lemma:
            continue
        # Skip prefixed lemmas (e.g., "b/7225", "c/853")
        # We want the root Strong's number
        clean_lemma = lemma.split("/")[-1].split()[0] if lemma else ""
        if not clean_lemma or clean_lemma in COMMON_LEMMAS:
            continue
        lemma_groups[clean_lemma].add(r["verse_id"])

    # Step 2: Connect verses within each lemma group
    # Use batch INSERT to avoid per-connection commits
    batch = []
    processed_groups = 0

    for lemma, verses in lemma_groups.items():
        size = len(verses)
        if size < 2 or size > max_lemma_count:
            continue

        processed_groups += 1
        verse_list = sorted(verses)
        strength = min(0.9, 0.4 + 0.05 * (max_lemma_count - size))

        for i in range(len(verse_list)):
            for j in range(i + 1, len(verse_list)):
                batch.append((
                    verse_list[i], verse_list[j], "linguistic",
                    "same_lemma", lemma, strength, 0.7, "algorithm",
                    '{"lemma": "' + lemma + '", "verse_count": ' + str(size) + '}'
                ))
                count += 1

                if len(batch) >= 200:
                    _batch_insert(conn, batch)
                    batch = []

        if processed_groups % 200 == 0:
            print(f"    {processed_groups} lemma groups processed...", flush=True)

    if batch:
        _batch_insert(conn, batch)

    print(f"  Linguistic (same_lemma): {count} connections from {processed_groups} lemma groups")
    return count


def _batch_insert(conn, batch):
    """Batch INSERT connections without per-row commits."""
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
