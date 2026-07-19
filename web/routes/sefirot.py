"""Sefirot (Kabbalistic Tree of Life) API routes."""

from fastapi import APIRouter, HTTPException, Query

from lib.db import get_db
from lib.api.sefirot import lookup_sefirot, get_sefirah_info

router = APIRouter()


@router.get("/api/v1/sefirot/{verse_ref}")
def get_verse_sefirot(verse_ref: str):
    """Get sefirah labels for a verse.

    Args:
        verse_ref: Verse ID (gen.1.1, john.1.1, etc.)
    """
    result = lookup_sefirot(verse_ref)
    if result["total"] == 0:
        # Check if verse exists
        conn = get_db()
        verse = conn.execute(
            "SELECT id FROM verses WHERE id = ?", (verse_ref,)
        ).fetchone()
        conn.close()
        if not verse:
            raise HTTPException(404, f"Verse '{verse_ref}' not found")
    return result


@router.get("/api/v1/sefirot")
def list_sefirot():
    """List all 10 sefirot with verse counts."""
    conn = get_db()
    from generators.sefirot_mapper import SEFIROT
    results = []
    for sefirah, info in SEFIROT.items():
        count = conn.execute(
            "SELECT COUNT(DISTINCT verse_id) as c FROM sefirah_verse_labels WHERE sefirah = ?",
            (sefirah,),
        ).fetchone()
        results.append({
            "sefirah": sefirah,
            "name": info["name"],
            "hebrew_name": info["hebrew_name"],
            "meaning": info["meaning"],
            "description": info["description"],
            "color": info["color"],
            "verse_count": count["c"] if count else 0,
        })
    conn.close()
    return {"sefirot": results, "total": len(results)}


@router.get("/api/v1/sefirot/{sefirah}/verses")
def get_sefirah_verses(sefirah: str, limit: int = Query(50, ge=1, le=500)):
    """Get all verses tagged with a specific sefirah."""
    conn = get_db()

    # Validate sefirah
    from generators.sefirot_mapper import SEFIROT
    if sefirah not in SEFIROT:
        conn.close()
        raise HTTPException(404, f"Sefirah '{sefirah}' not found. Options: {', '.join(SEFIROT.keys())}")

    verses = conn.execute(
        """SELECT svl.verse_id, svl.matched_keyword, svl.strength,
                  v.text_english, b.title as book_title, v.chapter, v.verse
           FROM sefirah_verse_labels svl
           JOIN verses v ON v.id = svl.verse_id
           JOIN books b ON b.id = v.book_id
           WHERE svl.sefirah = ?
           ORDER BY v.book_id, v.chapter, v.verse
           LIMIT ?""",
        (sefirah, limit),
    ).fetchall()

    conn.close()

    return {
        "sefirah": sefirah,
        "info": {
            "name": SEFIROT[sefirah]["name"],
            "hebrew_name": SEFIROT[sefirah]["hebrew_name"],
            "meaning": SEFIROT[sefirah]["meaning"],
            "color": SEFIROT[sefirah]["color"],
        },
        "verses": [
            {
                "verse": v["verse_id"],
                "reference": f"{v['book_title']} {v['chapter']}:{v['verse']}",
                "text": (v["text_english"] or "")[:150],
                "matched_keyword": v["matched_keyword"],
                "strength": v["strength"],
            }
            for v in verses
        ],
        "total": len(verses),
    }
