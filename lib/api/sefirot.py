"""
Sefirot — Kabbalistic Tree of Life lookups.

Provides:
  scripture_sefirot(verse_ref) — get sefirah labels for a verse
"""

from typing import Optional

from lib.db import get_db


def lookup_sefirot(verse_ref: str) -> dict:
    """Get sefirah labels for a verse reference.

    Args:
        verse_ref: Verse reference (e.g., 'gen.1.1')

    Returns:
        dict with sefirah labels, connections to other tagged verses
    """
    conn = get_db()

    # Get sefirah labels for this verse
    labels = conn.execute(
        """SELECT svl.sefirah, svl.matched_keyword, svl.strength,
                  sk.name as sefirah_name, sk.meaning, sk.description, sk.color
           FROM sefirah_verse_labels svl
           LEFT JOIN (
               SELECT 'keter' as sefirah, 'Keter' as name, 'Crown' as meaning, 'Divine will' as description, 'white' as color
               UNION ALL SELECT 'chokhmah','Chokhmah','Wisdom','Primordial wisdom','grey'
               UNION ALL SELECT 'binah','Binah','Understanding','Analytical understanding','black'
               UNION ALL SELECT 'chesed','Chesed','Mercy','Unbounded love','blue'
               UNION ALL SELECT 'gevurah','Gevurah','Judgment','Divine discipline','red'
               UNION ALL SELECT 'tiferet','Tiferet','Beauty','Harmonious balance','gold'
               UNION ALL SELECT 'netzach','Netzach','Victory','Eternal triumph','green'
               UNION ALL SELECT 'hod','Hod','Splendor','Radiant splendor','orange'
               UNION ALL SELECT 'yesod','Yesod','Foundation','The covenant channel','purple'
               UNION ALL SELECT 'malkhut','Malkhut','Kingdom','Divine presence','blue-violet'
           ) sk ON sk.sefirah = svl.sefirah
           WHERE svl.verse_id = ?
           ORDER BY svl.sefirah""",
        (verse_ref,),
    ).fetchall()

    if not labels:
        conn.close()
        return {"verse": verse_ref, "sefirot": [], "total": 0}

    result = []
    for r in labels:
        # Get other verses sharing this sefirah
        related = conn.execute(
            """SELECT verse_id FROM sefirah_verse_labels
               WHERE sefirah = ? AND verse_id != ?
               LIMIT 10""",
            (r["sefirah"], verse_ref),
        ).fetchall()

        result.append({
            "sefirah": r["sefirah"],
            "name": r["sefirah_name"],
            "meaning": r["meaning"],
            "description": r["description"],
            "color": r["color"],
            "matched_keyword": r["matched_keyword"],
            "strength": r["strength"],
            "related_verses": [v["verse_id"] for v in related],
        })

    conn.close()
    return {"verse": verse_ref, "sefirot": result, "total": len(result)}


def get_sefirah_info(sefirah: str) -> dict:
    """Get information about a specific sefirah.

    Args:
        sefirah: Sefirah name (keter, chokhmah, etc.)

    Returns:
        dict with sefirah info
    """
    conn = get_db()

    # Get verse count for this sefirah
    count = conn.execute(
        "SELECT COUNT(DISTINCT verse_id) as c FROM sefirah_verse_labels WHERE sefirah = ?",
        (sefirah,),
    ).fetchone()
    verse_count = count["c"] if count else 0

    conn.close()

    # Static info for all sefirot
    from generators.sefirot_mapper import SEFIROT
    info = SEFIROT.get(sefirah)
    if not info:
        return {"error": f"Sefirah '{sefirah}' not found"}

    return {
        "sefirah": sefirah,
        "name": info["name"],
        "hebrew_name": info["hebrew_name"],
        "meaning": info["meaning"],
        "description": info["description"],
        "color": info["color"],
        "verse_count": verse_count,
    }
