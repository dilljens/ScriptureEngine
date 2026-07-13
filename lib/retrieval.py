"""
Search and retrieval — combined sparse (SQLite FTS) and dense (embeddings) search.

For the initial build, uses SQLite-based full-text search.
Embeddings can be added later with sentence-transformers.
"""

from .db import search_verses as db_search_verses


def search_text(conn, query, book_id=None, limit=20):
    """Full-text search across the scripture corpus."""
    return db_search_verses(conn, query, book_id=book_id, limit=limit)


def get_verse_context(conn, book_id, chapter, verse, context_verses=3):
    """Get a verse with its surrounding context."""
    from .db import get_chapter

    verses = get_chapter(conn, book_id, chapter)
    if not verses:
        return None

    # Find our target verse
    target_idx = None
    for i, v in enumerate(verses):
        if v["verse"] == verse:
            target_idx = i
            break

    if target_idx is None:
        return None

    start = max(0, target_idx - context_verses)
    end = min(len(verses), target_idx + context_verses + 1)

    return {
        "context": verses[start:end],
        "target_index": target_idx - start,
        "book_id": book_id,
        "chapter": chapter,
    }


def search_by_pattern(conn, pattern_type, book_id=None, limit=20):
    """Search for verses that match a specific pattern type."""

    sql = """
        SELECT v.*, b.title as book_title
        FROM patterns p
        JOIN verses v ON v.id >= p.start_verse AND v.id <= p.end_verse
        JOIN books b ON b.id = v.book_id
        WHERE p.pattern_type = ?
    """
    params = [pattern_type]
    if book_id:
        sql += " AND b.id = ?"
        params.append(book_id)
    sql += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_intertextual_chain(conn, verse_id, direction="both", max_depth=3):
    """Trace intertextual connections forward and backward.

    direction: 'forward' (this verse quotes earlier), 'backward' (later quotes this),
               'both' (everything)
    """
    from .db import get_connections

    connections = get_connections(conn, verse_id)

    # Filter by intertextual layer
    intertext = [c for c in connections if c["layer"] == "intertextual"]

    # Also get reverse connections (where this verse is the target)
    if direction in ("backward", "both"):
        rev_rows = conn.execute("""
            SELECT c.*, v.text_english as target_text,
                   b.title as target_book_title
            FROM connections c
            JOIN verses v ON v.id = c.source_verse
            JOIN books b ON b.id = v.book_id
            WHERE c.target_verse = ? AND c.layer = 'intertextual'
        """, (verse_id,)).fetchall()
        intertext.extend([dict(r) for r in rev_rows])

    return intertext


def search_gematria_value(conn, value, system="standard", limit=30):
    """Find all verses containing words with a specific gematria value.

    system: 'standard', 'ordinal', 'reduced', or 'any'
    """
    from .db import find_matching_gematria

    results = find_matching_gematria(conn, value, system=system, limit=limit)
    return results


def search_divine_name_value(conn, divine_name, limit=30):
    """Find verses whose gematria matches a divine name value."""
    from .gematria import DIVINE_NAMES

    name_map = {d["name"].lower(): d for d in DIVINE_NAMES}
    name_info = name_map.get(divine_name.lower())

    if not name_info:
        return {"error": f"Unknown divine name: {divine_name}", "matches": []}

    matches = search_gematria_value(conn, name_info["value_standard"],
                                    system="standard", limit=limit)

    return {
        "divine_name": name_info["name"],
        "hebrew": name_info["hebrew"],
        "value_standard": name_info["value_standard"],
        "matches_count": len(matches),
        "matches": matches,
    }
