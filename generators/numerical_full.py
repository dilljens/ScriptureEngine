"""Numerical full generator — expands gematria connections.

Retained method only (Track B1 stop-list):
1. Rare-value word matches (same standard value in < 10 verses)

Retired and no longer generated:
- sacred_number verse totals (verse sum matching 7/12/40/... is a
  nine-bucket-style coincidence, not a reproducible traditional comparison).
  Existing rows are neutralized in calibration until the archive/purge
  migration runs.
"""

from collections import defaultdict

from lib.db import add_connection


def run(conn, book_ids=None):
    """Find verses sharing rare standard gematria word values.

    Returns count of connections created.
    """
    count = 0

    # Find words with rare gematria values (< 10 occurrences)
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
