"""Frequency generator — distribution-based connections.

Connects verses based on shared word frequency patterns:
- Words that appear exactly a sacred number of times (7, 12, 40, etc.)
- Connecting all verses containing such words
"""

import re
from collections import defaultdict, Counter
from lib.db import add_connection


SACRED_NUMBERS = {7, 10, 12, 40, 50, 70, 100}


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()


def run(conn, book_ids=None):
    """Generate frequency-based connections.

    Scans ALL word frequencies across the canon, not just the top N.
    Connects verses that share a word whose total frequency is a sacred number.
    """
    batch = []
    count = 0

    # Step 1: Build word frequency and verse index from ALL verses
    if book_ids:
        placeholders = ",".join("?" for _ in book_ids)
        rows = conn.execute(f"""
            SELECT id, text_english FROM verses
            WHERE text_english != '' AND book_id IN ({placeholders})
        """, book_ids).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, text_english FROM verses WHERE text_english != ''
        """).fetchall()

    word_verses = defaultdict(set)
    word_freq = Counter()

    for r in rows:
        words = set(re.findall(r"[a-zA-Z']+", r["text_english"].lower()))
        for w in words:
            if len(w) > 2:
                word_verses[w].add(r["id"])

    # Compute frequencies after building the full index
    for w, verses in word_verses.items():
        word_freq[w] = len(verses)

    # Step 2: Find words with sacred-number frequencies and connect their verses
    processed = 0
    for word, freq in word_freq.most_common():
        if freq in SACRED_NUMBERS and len(word_verses[word]) >= 2:
            verses = sorted(word_verses[word])
            type_name = f"{freq}_fold_pattern" if freq in (7, 12, 40, 10) else "key_word_count"

            # Connect all verses sharing this word (hub-and-spoke for large groups)
            if len(verses) > 20:
                hub = verses[0]
                for v in verses[1:]:
                    batch.append((
                        hub, v, "frequency",
                        type_name, word, 0.5, 0.5, "algorithm",
                        f'{{"word": "{word}", "frequency": {freq}, "note": "word appears {freq} times"}}'
                    ))
                    count += 1
                    if len(batch) >= 200:
                        _batch_insert(conn, batch)
                        batch = []
            else:
                for i in range(len(verses)):
                    for j in range(i + 1, len(verses)):
                        batch.append((
                            verses[i], verses[j], "frequency",
                            type_name, word, 0.5, 0.5, "algorithm",
                            f'{{"word": "{word}", "frequency": {freq}}}'
                        ))
                        count += 1
                        if len(batch) >= 200:
                            _batch_insert(conn, batch)
                            batch = []

            processed += 1

    if batch:
        _batch_insert(conn, batch)

    print(f"  Frequency: {count} connections from {processed} sacred-frequency words")
    return count
