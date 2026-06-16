"""Numerical full generator — expands gematria connections.

Currently we have 302 numerical connections matching divine name values.
This expands to:
1. All sacred numbers (7, 12, 40, 10, 70, etc.)
2. Rare-value matches (values that appear in < 10 verses)
3. Verse total matches with sacred numbers
"""

from collections import defaultdict
from lib.db import add_connection


SACRED_VALUES = {7, 10, 12, 40, 50, 70, 100, 120, 400, 1000, 613}


def run(conn, book_ids=None):
    """Expand numerical connections beyond divine name values.

    1. Find all verses with sacred-number gematria totals
    2. Connect them to each other

    Returns count of connections created.
    """
    count = 0

    # Strategy 1: Find verses whose total gematria is a sacred number
    # For Hebrew verses, sum the gematria of all words in the verse
    verse_totals = conn.execute("""
        SELECT g.verse_id, SUM(g.value_standard) as total
        FROM gematria g
        GROUP BY g.verse_id
    """).fetchall()

    # Group verses by their total gematria
    total_groups = defaultdict(list)
    for r in verse_totals:
        total = r["total"]
        if total in SACRED_VALUES:
            total_groups[total].append(r["verse_id"])

    for total, verses in total_groups.items():
        if len(verses) < 2:
            continue
        for i in range(len(verses)):
            for j in range(i + 1, len(verses)):
                try:
                    add_connection(conn, verses[i], verses[j],
                                  layer="numerical",
                                  type_name="sacred_number",
                                  subtype=f"verse_total_{total}",
                                  strength=0.6,
                                  confidence=0.7,
                                  discovered_by="algorithm",
                                  metadata={
                                      "verse_total": total,
                                      "note": f"Both verses have total gematria {total} (sacred number)",
                                  })
                    count += 1
                except Exception:
                    pass

    # Strategy 2: Find words with rare gematria values (< 10 occurrences)
    # and connect verses sharing those values
    value_verses = conn.execute("""
        SELECT value_standard, verse_id
        FROM gematria
        WHERE value_standard > 0
    """).fetchall()

    val_groups = defaultdict(set)
    for r in value_verses:
        val_groups[r["value_standard"]].add(r["verse_id"])

    for value, verses in val_groups.items():
        if 2 <= len(verses) <= 10 and value not in (26, 86, 65, 345):
            # Rare value not already covered by divine names
            verse_list = sorted(verses)
            for i in range(len(verse_list)):
                for j in range(i + 1, len(verse_list)):
                    try:
                        add_connection(conn, verse_list[i], verse_list[j],
                                      layer="numerical",
                                      type_name="same_gematria_standard",
                                      subtype=f"value_{value}",
                                      strength=0.5,
                                      confidence=0.5,
                                      discovered_by="algorithm",
                                      metadata={
                                          "value": value,
                                          "verse_count": len(verses),
                                      })
                        count += 1
                    except Exception:
                        pass

    conn.commit()
    print(f"  Numerical (full): {count} additional connections")
    return count


def _batch_insert(conn, batch):
    conn.executemany("""
        INSERT OR IGNORE INTO connections
            (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, batch)
    conn.commit()
