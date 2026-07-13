"""Interpretive disagreement model — surfaces contradictory interpretations."""


def get_disagreements(conn, verse):
    """Get interpretive disagreements for a verse.

    Args:
        verse: Verse ID (gen.1.1)

    Returns: dict with verse, count, disagreements list
    """
    rows = conn.execute(
        """SELECT id, tradition_a, tradition_b, description, resolved_by
           FROM interpretive_disagreements
           WHERE verse_id = ?
           ORDER BY id""",
        (verse,)
    ).fetchall()

    return {
        "verse": verse,
        "count": len(rows),
        "disagreements": [dict(r) for r in rows],
    }


def list_disagreements(conn, limit=20, offset=0):
    """List all disagreements, with optional pagination."""
    rows = conn.execute(
        "SELECT id, verse_id, tradition_a, tradition_b, description FROM interpretive_disagreements ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM interpretive_disagreements").fetchone()[0]
    return {"total": total, "disagreements": [dict(r) for r in rows]}


def add_disagreement(conn, verse_id, tradition_a, tradition_b, description, connection_a_id=None, connection_b_id=None):
    """Add a disagreement (for seeding)."""
    conn.execute(
        """INSERT INTO interpretive_disagreements
           (verse_id, tradition_a, tradition_b, description, connection_a_id, connection_b_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (verse_id, tradition_a, tradition_b, description, connection_a_id, connection_b_id)
    )
    conn.commit()
    return {"ok": True, "verse": verse_id}
