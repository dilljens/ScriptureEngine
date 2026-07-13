#!/usr/bin/env python3
"""MCP Tool: scripture_pardes — Query connections by PaRDeS level.

Explore connections filtered by interpretive depth:
  P'shat — Literal/simple
  Remez — Alluded/hinted
  Drash — Comparative/interpretive
  Sod — Hidden/mystical

Usage:
  python3 pardes.py '{"verse": "gen.1.1"}'
  python3 pardes.py '{"verse": "gen.1.1", "level": "sod"}'
  python3 pardes.py '{"stats": true}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.connections.pardes import LEVELS, TYPE_PARDES, get_connections_by_level, get_layer_stats
from lib.db import get_connections_by_layer, get_db


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(sys.stdin.read())
    conn = get_db()

    if "stats" in args:
        result = get_layer_stats(conn)
        total = sum(v["count"] for v in result.values())
        print(json.dumps({
            "levels": result,
            "total": total,
            "level_info": LEVELS,
        }, indent=2, ensure_ascii=False))
        conn.close()
        return

    verse = args.get("verse", "")
    level_filter = args.get("level")  # Optional: filter to one level

    if not verse:
        print(json.dumps({"error": "Provide verse or stats"}))
        conn.close()
        return

    # Get the verse text
    vrow = conn.execute("""
        SELECT v.*, b.title as book_title FROM verses v
        JOIN books b ON b.id = v.book_id WHERE v.id = ?
    """, (verse,)).fetchone()

    if not vrow:
        print(json.dumps({"error": f"Verse {verse} not found"}))
        conn.close()
        return

    # Get all connections for this verse
    by_layer = get_connections_by_layer(conn, verse)

    # Group by PaRDeS level
    by_level = get_connections_by_level(by_layer)

    # Filter to one level if requested
    if level_filter:
        by_level = {level_filter: by_level[level_filter]} if level_filter in by_level else {}

    # Get connections grouped by level with details
    result = {
        "verse": verse,
        "text": vrow["text_english"][:200],
        "book": vrow["book_title"],
    }

    if level_filter:
        level_info = LEVELS.get(level_filter, {})
        result["level"] = {
            "name": level_info.get("name", level_filter),
            "hebrew": level_info.get("hebrew", ""),
            "description": level_info.get("description", ""),
        }
        data = by_level.get(level_filter, {})
        result["connections"] = data.get("count", 0)

        # Get detailed connections for this level
        details = []
        for layer_name in data.get("layers", []):
            conns = by_layer.get(layer_name, [])
            for c in conns if isinstance(conns, list) else []:
                if TYPE_PARDES.get(layer_name, {}).get(c.get("type", "")) == level_filter:
                    details.append({
                        "layer": layer_name,
                        "type": c.get("type", ""),
                        "target": c.get("target_verse", ""),
                        "strength": c.get("strength", 0),
                    })
        result["connections_detail"] = details[:30]
    else:
        result["levels"] = {}
        total = 0
        for lvl, data in by_level.items():
            result["levels"][lvl] = {
                "name": data.get("name", lvl),
                "hebrew": data.get("hebrew", ""),
                "count": data.get("count", 0),
                "layers": data.get("layers", []),
            }
            total += data.get("count", 0)
        result["total_connections"] = total

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
