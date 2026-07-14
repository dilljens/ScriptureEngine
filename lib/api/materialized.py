"""Materialized view query tools — verse similarity + entity co-occurrence.

These queries use pre-computed tables created by:
  .venv/bin/python3 scripts/build_materialized_views.py
"""

from lib.db import get_db


def similar_verses(verse_id: str, limit: int = 20, min_score: float = 0.1):
    """Find verses similar to a given verse using pre-computed entity + connection overlap."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT
                CASE WHEN verse_a = ? THEN verse_b ELSE verse_a END AS similar_verse,
                combined_score, entity_overlap, connection_overlap,
                shared_entity_count, shared_connection_count,
                v.text_english, v.text_hebrew,
                b.title as book_title, v.chapter, v.verse
            FROM verse_similarity vs
            JOIN verses v ON v.id = CASE WHEN verse_a = ? THEN verse_b ELSE verse_a END
            JOIN books b ON b.id = v.book_id
            WHERE (? IN (verse_a, verse_b)) AND combined_score >= ?
            ORDER BY combined_score DESC
            LIMIT ?
        """, (verse_id, verse_id, verse_id, min_score, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        conn.close()
        return {"error": f"Materialized view not available. Run: python3 scripts/build_materialized_views.py ({e})"}


def entity_cooccurrence(entity_id: str, limit: int = 20):
    """Find entities that frequently co-occur with a given entity."""
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT
                CASE WHEN entity_a = ? THEN entity_b ELSE entity_a END AS related_entity,
                frequency, avg_confidence,
                el.english_name, el.entity_type,
                el.hebrew_name, el.greek_name
            FROM entity_cooccurrence ec
            JOIN entity_links el ON el.entity_id = CASE WHEN ec.entity_a = ? THEN ec.entity_b ELSE ec.entity_a END
            WHERE ? IN (ec.entity_a, ec.entity_b)
            ORDER BY frequency DESC
            LIMIT ?
        """, (entity_id, entity_id, entity_id, limit)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        conn.close()
        return {"error": f"Materialized view not available. Run: python3 scripts/build_materialized_views.py ({e})"}
