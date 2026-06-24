"""Shared Hebrew/Greek matching utilities for generators.

Provides functions to match verses by Hebrew lemma (gematria table),
Greek lemma (gematria_greek table), and English fallback for cross-canon.
"""

CROSS_CANON_BOOKS = (
    '1ne','2ne','jacob','enos','jarom','omni','wom','mosiah',
    'alma','hel','3ne','4ne','ether','moro',
    'dc','moses','abraham','jsm','jsh','aoff',
)


def get_ot_by_lemmas(conn, lemmas_and):
    """Find OT verses where ALL specified lemmas appear (AND logic).
    
    Args:
        conn: DB connection
        lemmas_and: list of lemma strings (e.g., ['4397', '3068'])
    
    Returns:
        list of verse_id strings
    """
    if not lemmas_and:
        return []
    if len(lemmas_and) == 1:
        rows = conn.execute(
            "SELECT DISTINCT verse_id FROM gematria WHERE lemma = ?",
            (lemmas_and[0],)
        ).fetchall()
        return [r["verse_id"] for r in rows]
    
    # Multiple lemmas: JOIN to find verses where ALL appear
    joins = []
    for i in range(2, len(lemmas_and) + 1):
        joins.append(
            f"JOIN gematria g{i} ON g1.verse_id = g{i}.verse_id AND g1.word_index != g{i}.word_index"
        )
    where = " AND ".join(f"g{i}.lemma = ?" for i in range(1, len(lemmas_and) + 1))
    
    sql = f"""
        SELECT DISTINCT g1.verse_id FROM gematria g1
        {" ".join(joins)}
        WHERE {where}
    """
    rows = conn.execute(sql, lemmas_and).fetchall()
    return [r["verse_id"] for r in rows]


def get_ot_by_lemma(conn, lemma):
    """Find OT verses by a single Hebrew lemma."""
    rows = conn.execute(
        "SELECT DISTINCT verse_id FROM gematria WHERE lemma = ?",
        (lemma,)
    ).fetchall()
    return [r["verse_id"] for r in rows]


def get_nt_by_greek(conn, lemma_pattern):
    """Find NT verses by Greek lemma pattern."""
    rows = conn.execute(
        "SELECT DISTINCT verse_id FROM gematria_greek WHERE lemma LIKE ?",
        (f'%{lemma_pattern}%',)
    ).fetchall()
    return [r["verse_id"] for r in rows]


def get_cross_canon(conn, keyword_pattern):
    """Find BoM/D&C verses by English keyword (fallback)."""
    placeholders = ",".join("?" for _ in CROSS_CANON_BOOKS)
    rows = conn.execute(f"""
        SELECT id FROM verses 
        WHERE text_english LIKE ? 
        AND book_id IN ({placeholders})
    """, (f'%{keyword_pattern}%',) + CROSS_CANON_BOOKS)
    return [r["id"] for r in rows]


MAX_GROUP_SIZE = 50


def add_connections_for_group(conn, verse_ids, layer, type_name, subtype,
                               strength=0.5, confidence=0.4, 
                               discovered_by="algorithm", metadata="{}"):
    """Connect every pair of verses in a group (capped at MAX_GROUP_SIZE)."""
    verse_ids = list(verse_ids)[:MAX_GROUP_SIZE]
    count = 0
    for i in range(len(verse_ids)):
        for j in range(i + 1, len(verse_ids)):
            try:
                existing = conn.execute(
                    """SELECT COUNT(*) FROM connections 
                       WHERE source_verse = ? AND target_verse = ? 
                       AND type = ? AND subtype = ?""",
                    (verse_ids[i], verse_ids[j], type_name, subtype)
                ).fetchone()[0]
                if existing == 0:
                    from lib.db import add_connection
                    add_connection(conn, verse_ids[i], verse_ids[j], layer=layer,
                                  type_name=type_name, subtype=subtype,
                                  strength=strength, confidence=confidence,
                                  discovered_by=discovered_by,
                                  metadata=metadata)
                    count += 1
            except:
                pass
    return count
