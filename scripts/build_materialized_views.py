#!/usr/bin/env python3
"""Build materialized views for faster queries.

Pre-computes:
  1. entity_cooccurrence — which entities appear together in the same verse
  2. verse_similarity — which verses share the most entities + connection types

Usage:
  .venv/bin/python3 scripts/build_materialized_views.py
  .venv/bin/python3 scripts/build_materialized_views.py --reset
"""

import argparse
import sqlite3
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db


def build_entity_cooccurrence(conn, reset=False):
    """Pre-compute which entity pairs co-occur in the same verse.
    
    Table: entity_cooccurrence (entity_a, entity_b, frequency, verse_ids TEXT)
    """
    if reset:
        conn.execute("DROP TABLE IF EXISTS entity_cooccurrence")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS entity_cooccurrence (
            entity_a TEXT NOT NULL,
            entity_b TEXT NOT NULL,
            frequency INTEGER NOT NULL DEFAULT 0,
            avg_confidence REAL DEFAULT 0.0,
            verse_ids TEXT DEFAULT '[]',
            PRIMARY KEY (entity_a, entity_b)
        )
    """)

    # Compute co-occurrence from verse_entities table
    conn.execute("""
        DELETE FROM entity_cooccurrence
    """)

    conn.execute("""
        INSERT OR IGNORE INTO entity_cooccurrence (entity_a, entity_b, frequency, avg_confidence, verse_ids)
        SELECT
            ve1.entity_id AS entity_a,
            ve2.entity_id AS entity_b,
            COUNT(*) AS frequency,
            AVG((ve1.confidence + ve2.confidence) / 2.0) AS avg_confidence,
            json_group_array(DISTINCT ve1.verse_id) AS verse_ids
        FROM verse_entities ve1
        JOIN verse_entities ve2 ON ve1.verse_id = ve2.verse_id AND ve1.entity_id < ve2.entity_id
        GROUP BY ve1.entity_id, ve2.entity_id
        HAVING frequency >= 2
        ORDER BY frequency DESC
    """)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM entity_cooccurrence").fetchone()[0]
    print(f"  Entity co-occurrence pairs: {count}")
    return count


def build_verse_similarity(conn, reset=False):
    """Pre-compute verse similarity based on shared entities and connection types.
    
    Table: verse_similarity (verse_a, verse_b, entity_overlap, connection_overlap, combined_score)
    """
    if reset:
        conn.execute("DROP TABLE IF EXISTS verse_similarity")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS verse_similarity (
            verse_a TEXT NOT NULL,
            verse_b TEXT NOT NULL,
            entity_overlap REAL DEFAULT 0.0,
            connection_overlap REAL DEFAULT 0.0,
            combined_score REAL DEFAULT 0.0,
            shared_entity_count INTEGER DEFAULT 0,
            shared_connection_count INTEGER DEFAULT 0,
            PRIMARY KEY (verse_a, verse_b)
        )
    """)

    conn.execute("DELETE FROM verse_similarity")

    # Entity-based similarity: verses sharing entities
    conn.execute("""
        INSERT OR IGNORE INTO verse_similarity (verse_a, verse_b, entity_overlap, shared_entity_count)
        SELECT
            ve1.verse_id AS verse_a,
            ve2.verse_id AS verse_b,
            1.0 * COUNT(DISTINCT ve1.entity_id) / (
                SELECT MAX(cnt) FROM (
                    SELECT COUNT(DISTINCT entity_id) as cnt FROM verse_entities WHERE verse_id = ve1.verse_id
                    UNION
                    SELECT COUNT(DISTINCT entity_id) as cnt FROM verse_entities WHERE verse_id = ve2.verse_id
                )
            ) AS entity_overlap,
            COUNT(DISTINCT ve1.entity_id) AS shared_entity_count
        FROM verse_entities ve1
        JOIN verse_entities ve2 ON ve1.entity_id = ve2.entity_id AND ve1.verse_id < ve2.verse_id
        GROUP BY ve1.verse_id, ve2.verse_id
        HAVING shared_entity_count >= 2
    """)
    conn.commit()

    # Connection-based similarity: verses sharing connection types
    conn.execute("""
        UPDATE verse_similarity SET
            connection_overlap = COALESCE((
                SELECT 1.0 * COUNT(DISTINCT c1.type) / (
                    SELECT MAX(cnt) FROM (
                        SELECT COUNT(DISTINCT type) as cnt FROM connections WHERE source_verse = vs.verse_a AND deprecated=0
                        UNION
                        SELECT COUNT(DISTINCT type) as cnt FROM connections WHERE source_verse = vs.verse_b AND deprecated=0
                    )
                )
                FROM connections c1
                JOIN connections c2 ON c1.type = c2.type AND c1.source_verse = vs.verse_a AND c2.source_verse = vs.verse_b
                WHERE c1.deprecated=0 AND c2.deprecated=0
            ), 0.0),
            shared_connection_count = COALESCE((
                SELECT COUNT(DISTINCT c1.type)
                FROM connections c1
                JOIN connections c2 ON c1.type = c2.type AND c1.source_verse = vs.verse_a AND c2.source_verse = vs.verse_b
                WHERE c1.deprecated=0 AND c2.deprecated=0
            ), 0)
        FROM verse_similarity vs
        WHERE vs.verse_a = verse_a AND vs.verse_b = verse_b
    """)
    conn.commit()

    # Combined score: weighted combination
    conn.execute("""
        UPDATE verse_similarity SET
            combined_score = entity_overlap * 0.6 + connection_overlap * 0.4
        WHERE entity_overlap > 0 OR connection_overlap > 0
    """)
    conn.commit()

    count = conn.execute("SELECT COUNT(*) FROM verse_similarity").fetchone()[0]
    print(f"  Verse similarity pairs: {count}")
    return count


def get_similar_verses(conn, verse_id, limit=20, min_score=0.1):
    """Get verses similar to a given verse, using materialized view."""
    # Direct similarity
    rows = conn.execute("""
        SELECT
            CASE WHEN verse_a = ? THEN verse_b ELSE verse_a END AS similar_verse,
            combined_score,
            entity_overlap,
            connection_overlap,
            shared_entity_count,
            shared_connection_count,
            v.text_english, v.text_hebrew,
            b.title as book_title, v.chapter, v.verse
        FROM verse_similarity vs
        JOIN verses v ON v.id = CASE WHEN verse_a = ? THEN verse_b ELSE verse_a END
        JOIN books b ON b.id = v.book_id
        WHERE (? IN (verse_a, verse_b)) AND combined_score >= ?
        ORDER BY combined_score DESC
        LIMIT ?
    """, (verse_id, verse_id, verse_id, min_score, limit)).fetchall()

    return [dict(r) for r in rows]


def get_entity_cooccurrence(conn, entity_id, limit=20):
    """Get entities that co-occur with a given entity."""
    rows = conn.execute("""
        SELECT
            CASE WHEN entity_a = ? THEN entity_b ELSE entity_a END AS related_entity,
            frequency,
            avg_confidence,
            el.english_name, el.entity_type,
            el.hebrew_name, el.greek_name
        FROM entity_cooccurrence ec
        JOIN entity_links el ON el.entity_id = CASE WHEN ec.entity_a = ? THEN ec.entity_b ELSE ec.entity_a END
        WHERE ? IN (ec.entity_a, ec.entity_b)
        ORDER BY frequency DESC
        LIMIT ?
    """, (entity_id, entity_id, entity_id, limit)).fetchall()

    return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser(description="Build materialized views")
    parser.add_argument("--reset", action="store_true", help="Rebuild from scratch")
    args = parser.parse_args()

    print("=" * 60)
    print("  Building Materialized Views")
    print("=" * 60)

    conn = get_db()

    print("\n--- Entity Co-occurrence ---")
    build_entity_cooccurrence(conn, reset=args.reset)

    print("\n--- Verse Similarity ---")
    build_verse_similarity(conn, reset=args.reset)

    # Stats
    ec_count = conn.execute("SELECT COUNT(*) FROM entity_cooccurrence").fetchone()[0]
    vs_count = conn.execute("SELECT COUNT(*) FROM verse_similarity").fetchone()[0]
    print(f"\n  Summary:")
    print(f"    entity_cooccurrence: {ec_count} pairs")
    print(f"    verse_similarity:    {vs_count} pairs")

    conn.close()
    print("\n  Done. These views are queried at runtime (no JOIN aggregation needed).")


if __name__ == "__main__":
    main()
