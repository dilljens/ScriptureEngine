"""
Shared tool: database and system statistics.

Used by MCP (scripture_info),
HTTP API (/api/v1/info),
and CLI (tools/*).
"""


def get_stats(conn):
    """Get database statistics — total verses, connections per layer, quality.

    Returns: dict with counts and distributions
    """
    layers = conn.execute(
        "SELECT layer, COUNT(*) as c FROM connections GROUP BY layer ORDER BY layer"
    ).fetchall()

    quality = conn.execute(
        "SELECT quality_level, COUNT(*) as c FROM connections GROUP BY quality_level"
    ).fetchall()

    pg = conn.execute("SELECT COUNT(*) as c FROM passage_guides").fetchone()["c"]
    verses = conn.execute("SELECT COUNT(*) as c FROM verses").fetchone()["c"]
    gematria = conn.execute("SELECT COUNT(*) as c FROM gematria").fetchone()["c"]
    greek = conn.execute("SELECT COUNT(*) as c FROM gematria_greek").fetchone()["c"]
    entities = conn.execute("SELECT COUNT(*) as c FROM entity_links").fetchone()["c"]
    verse_entities = conn.execute(
        "SELECT COUNT(*) as c FROM verse_entities"
    ).fetchone()["c"] if _table_exists(conn, "verse_entities") else 0

    return {
        "total_connections": sum(r["c"] for r in layers),
        "total_verses": verses,
        "hebrew_gematria": gematria,
        "greek_isopsephy": greek,
        "passage_guides": pg,
        "entity_links": entities,
        "verse_entity_links": verse_entities,
        "layers": {r["layer"]: r["c"] for r in layers},
        "quality": {r["quality_level"]: r["c"] for r in quality},
    }


def _table_exists(conn, table_name):
    """Check if a table exists in the database."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None
