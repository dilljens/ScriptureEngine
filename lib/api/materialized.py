"""Materialized view query tools — verse similarity + entity co-occurrence.

These queries use pre-computed tables created by:
  .venv/bin/python3 scripts/build_materialized_views.py
"""

import json

from lib.db import get_db


def _materialized_error(what):
    return {"error": f"Materialized view not available. Run: python3 scripts/build_materialized_views.py ({what})"}


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


def entity_card(conn=None, entity=None):
    """Get the pre-computed materialized card for an entity.

    The card bundles entity metadata, aliases, all verses mentioning the
    entity, connections among those verses, top co-occurring entities, and
    gematria where the entity is a Hebrew surface.

    Registry contract signature: (conn, entity). Opens its own connection when
    conn is None (direct API style).

    Args:
        conn: SQLite connection (optional — one is opened if not given).
        entity: canonical entity ID (person.abraham, place.zion, ...)

    Returns: dict card, or {"error": ...} if the view is not built / unknown.
    """
    if not entity:
        return {"error": "entity required"}
    close_conn = conn is None
    if conn is None:
        conn = get_db()
    try:
        row = conn.execute(
            "SELECT entity_id, card_json, built_at FROM entity_cards WHERE entity_id = ?",
            (entity,),
        ).fetchone()
        if not row:
            return {"error": f"Entity card not found: {entity}"}
        card = json.loads(row["card_json"])
        card["built_at"] = row["built_at"]
        return card
    except Exception as e:
        return _materialized_error(e)
    finally:
        if close_conn:
            conn.close()
