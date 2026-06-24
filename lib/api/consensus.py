"""Ecumenical consensus scoring — tracks how many traditions connect to each verse."""

def get_consensus(conn, verse):
    """Get tradition consensus data for a verse.

    Returns which traditions have made interpretive connections to this verse.

    Args:
        verse: Verse ID (gen.1.1)

    Returns: dict with verse, tradition_count, traditions, agreements, disagreements
    """
    rows = conn.execute(
        """SELECT DISTINCT c.subtype as tradition, c.target_verse, c.type, c.strength
           FROM connections c
           WHERE c.source_verse = ? AND c.layer = 'interpretive'
           ORDER BY c.subtype""",
        (verse,)
    ).fetchall()

    traditions = {}
    for r in rows:
        t = r["tradition"]
        if t not in traditions:
            traditions[t] = []
        traditions[t].append({
            "target": r["target_verse"],
            "type": r["type"],
            "strength": r["strength"],
        })

    dis = conn.execute(
        """SELECT id, tradition_a, tradition_b, description
           FROM interpretive_disagreements WHERE verse_id = ?""",
        (verse,)
    ).fetchall()

    return {
        "verse": verse,
        "tradition_count": len(traditions),
        "traditions": list(traditions.keys()),
        "tradition_details": traditions,
        "disagreement_count": len(dis),
        "disagreements": [dict(d) for d in dis] if dis else [],
    }


def verse_consensus(conn, book, chapter, verse):
    """Get consensus data for a verse by reference (used by verse output)."""
    verse_id = f"{book}.{chapter}.{verse}"
    return get_consensus(conn, verse_id)
