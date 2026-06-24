"""Bible version management — list and switch translations."""


def list_versions(conn):
    """List all available Bible text versions."""
    rows = conn.execute("""
        SELECT version, language, is_default, COUNT(*) as verse_count
        FROM text_resources
        GROUP BY version, language, is_default
        ORDER BY is_default DESC, version
    """).fetchall()

    return {
        "versions": [
            {
                "id": r["version"],
                "language": r["language"],
                "is_default": bool(r["is_default"]),
                "verses_available": r["verse_count"],
            }
            for r in rows
        ],
        "text_english_default": "WEB" if any(r["is_default"] for r in rows) else "KJV",
    }


def get_verse_text(conn, verse, version="WEB"):
    """Get the text of a verse in a specific version."""
    row = conn.execute(
        "SELECT text, language FROM text_resources WHERE verse_id = ? AND version = ?",
        (verse, version)
    ).fetchone()

    if not row:
        # Fall back to text_english from verses table
        row2 = conn.execute(
            "SELECT text_english FROM verses WHERE id = ?", (verse,)
        ).fetchone()
        if row2:
            return {"text": row2["text_english"], "version": "KJV", "language": "eng"}
        return {"error": "Verse not found"}

    return {"text": row["text"], "version": version, "language": row["language"]}
