#!/usr/bin/env python3
"""MCP Tool: scripture_skeptic — View connections with confidence filtering.

Shows only connections that meet a minimum quality level.
The user sees which connections are verified vs. speculative.

Usage:
  python3 skeptic.py '{"verse": "gen.1.1"}'
  python3 skeptic.py '{"verse": "gen.1.1", "min_quality": "probable"}'
  python3 skeptic.py '{"verse": "gen.1.1", "min_confidence": 0.7}'
  python3 skeptic.py '{"stats": true}'
"""

import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.controls.calibration import QUALITY_LEVELS, get_quality_color, get_quality_stars
from lib.connections.pardes import LEVELS as PARDES_LEVELS


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(sys.stdin.read())
    conn = get_db()

    if "stats" in args:
        rows = conn.execute("""
            SELECT quality_level, COUNT(*) as c
            FROM connections GROUP BY quality_level ORDER BY quality_level
        """).fetchall()
        result = {"quality_distribution": {}}
        for r in rows:
            info = QUALITY_LEVELS.get(r["quality_level"], {})
            result["quality_distribution"][r["quality_level"]] = {
                "count": r["c"],
                "label": info.get("label", r["quality_level"]),
                "emoji": info.get("emoji", ""),
                "color": info.get("color", "#999"),
            }
        total = sum(r["c"] for r in rows)
        result["total"] = total
        print(json.dumps(result, indent=2))
        conn.close()
        return

    verse = args.get("verse", "")
    min_quality = args.get("min_quality", "suggested")  # Show all by default
    min_confidence = args.get("min_confidence", 0.0)

    if not verse:
        print(json.dumps({"error": "Provide verse or stats"}))
        conn.close()
        return

    # Get the verse
    vrow = conn.execute("""
        SELECT v.*, b.title as book_title FROM verses v
        JOIN books b ON b.id = v.book_id WHERE v.id = ?
    """, (verse,)).fetchone()

    if not vrow:
        print(json.dumps({"error": f"Verse {verse} not found"}))
        conn.close()
        return

    # Determine minimum rank for filtering
    min_rank = QUALITY_LEVELS.get(min_quality, {}).get("rank", 5)
    
    # Get connections with quality filtering
    rows = conn.execute("""
        SELECT c.*, v.text_english as target_text,
               b.title as target_book_title
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
    """, (verse,)).fetchall()

    by_quality = {}
    hidden_count = 0
    
    for r in rows:
        r = dict(r)
        quality = r.get("quality_level", "suggested")
        confidence = r.get("confidence", 0.0) or 0.0
        q_rank = QUALITY_LEVELS.get(quality, {}).get("rank", 5)
        
        # Filter
        if q_rank > min_rank or confidence < min_confidence:
            hidden_count += 1
            continue
        
        if quality not in by_quality:
            info = QUALITY_LEVELS.get(quality, {})
            by_quality[quality] = {
                "label": info.get("label", quality),
                "emoji": info.get("emoji", ""),
                "color": info.get("color", "#999"),
                "connections": [],
            }
        
        by_quality[quality]["connections"].append({
            "type": r["type"],
            "layer": r["layer"],
            "target": r["target_verse"],
            "target_text": (r.get("target_text") or "")[:100],
            "target_book": r.get("target_book_title", ""),
            "strength": r.get("strength", 0),
            "confidence": r.get("confidence", 0),
            "p_value": r.get("p_value"),
            "quality": quality,
            "preregistered": bool(r.get("preregistered")),
        })

    result = {
        "verse": verse,
        "text": vrow["text_english"][:200],
        "book": vrow["book_title"],
        "filter": {
            "min_quality": min_quality,
            "min_confidence": min_confidence,
            "hidden": hidden_count,
        },
        "by_quality": by_quality,
        "total_shown": sum(len(v["connections"]) for v in by_quality.values()),
    }
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
    conn.close()


if __name__ == "__main__":
    main()
