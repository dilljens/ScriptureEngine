#!/usr/bin/env python3
"""
MCP Tool: scripture_layers — Multi-layer connection viewer.

Query all connection layers for a verse or passage at once.
Supports filtering by layer, type, strength, and discovery method.

Usage:
  python3 layers.py '{"verse": "isa.6.1"}'
  python3 layers.py '{"verse": "gen.1.1", "layers": ["linguistic", "symbolic"]}'
  python3 layers.py '{"verse": "gen.1.1", "min_strength": 0.6}'
  python3 layers.py '{"stats": true}'
  python3 layers.py '{"compare": {"verse_a": "gen.1.1", "verse_b": "john.1.1", "layers": ["intertextual", "symbolic"]}}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.connections.types import LAYERS


def get_verse_layers(conn, verse_id, layer_filter=None, min_strength=0):
    """Get all connections for a verse, grouped and filtered."""
    rows = conn.execute("""
        SELECT c.*, v.text_english as target_text,
               b.title as target_book_title
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
        ORDER BY c.layer, c.type, c.strength DESC
    """, (verse_id,)).fetchall()

    by_layer = {}
    for r in rows:
        r = dict(r)
        if layer_filter and r["layer"] not in layer_filter:
            continue
        if r.get("strength", 0) < min_strength:
            continue

        layer = r["layer"]
        if layer not in by_layer:
            layer_info = LAYERS.get(layer, {})
            by_layer[layer] = {
                "name": layer_info.get("name", layer),
                "description": layer_info.get("description", ""),
                "total": 0,
                "types": {},
            }

        t = r["type"]
        if t not in by_layer[layer]["types"]:
            by_layer[layer]["types"][t] = {
                "count": 0,
                "strength_avg": 0,
                "connections": [],
            }

        by_layer[layer]["types"][t]["count"] += 1
        by_layer[layer]["types"][t]["connections"].append({
            "target": r["target_verse"],
            "target_text": r.get("target_text", "")[:120],
            "target_book": r.get("target_book_title", ""),
            "subtype": r.get("subtype", ""),
            "strength": r["strength"],
            "discovered_by": r["discovered_by"],
        })
        by_layer[layer]["total"] += 1

    # Compute averages
    for layer_data in by_layer.values():
        for t, tdata in layer_data["types"].items():
            strengths = [c["strength"] for c in tdata["connections"]]
            tdata["strength_avg"] = round(sum(strengths) / max(len(strengths), 1), 2)

    return by_layer


def get_layer_stats(conn):
    """Get comprehensive layer statistics."""
    stats = {}

    # Per-layer counts
    rows = conn.execute("""
        SELECT layer, COUNT(*) as c FROM connections
        GROUP BY layer ORDER BY layer
    """).fetchall()

    for r in rows:
        layer = r["layer"]
        info = LAYERS.get(layer, {})
        stats[layer] = {
            "name": info.get("name", layer),
            "total": r["c"],
        }

        # Per-type breakdown within layer
        types = conn.execute("""
            SELECT type, COUNT(*) as c, ROUND(AVG(strength), 2) as avg_strength
            FROM connections WHERE layer = ?
            GROUP BY type ORDER BY c DESC
        """, (layer,)).fetchall()
        stats[layer]["types"] = {r["type"]: {"count": r["c"], "avg_strength": r["avg_strength"]} for r in types}

    # Top connected verses
    top_verses = conn.execute("""
        SELECT source_verse, COUNT(*) as c, GROUP_CONCAT(DISTINCT layer) as layers
        FROM connections
        GROUP BY source_verse
        ORDER BY c DESC LIMIT 10
    """).fetchall()

    stats["top_verses"] = []
    for r in top_verses:
        vrow = conn.execute("""
            SELECT v.text_english, b.title as book_title
            FROM verses v JOIN books b ON b.id = v.book_id WHERE v.id = ?
        """, (r["source_verse"],)).fetchone()
        stats["top_verses"].append({
            "verse": r["source_verse"],
            "connections": r["c"],
            "layers": r["layers"].split(",") if r["layers"] else [],
            "text": vrow["text_english"][:100] if vrow else "",
            "book": vrow["book_title"] if vrow else "",
        })

    # Unpopulated layers
    all_layers = list(LAYERS.keys())
    populated = set(stats.keys())
    stats["layers_unpopulated"] = [l for l in all_layers if l not in populated]

    return stats


def compare_verses(conn, verse_a, verse_b, layer_filter=None):
    """Compare two verses by their connections across layers."""
    layers_a = get_verse_layers(conn, verse_a, layer_filter)
    layers_b = get_verse_layers(conn, verse_b, layer_filter)

    # Find shared layers and types
    shared = []
    for layer in set(list(layers_a.keys()) + list(layers_b.keys())):
        a_types = set(layers_a.get(layer, {}).get("types", {}).keys()) if layer in layers_a else set()
        b_types = set(layers_b.get(layer, {}).get("types", {}).keys()) if layer in layers_b else set()
        common = a_types & b_types
        if common:
            shared.append({
                "layer": layer,
                "name": LAYERS.get(layer, {}).get("name", layer),
                "shared_types": list(common),
                "verse_a_count": layers_a.get(layer, {}).get("total", 0),
                "verse_b_count": layers_b.get(layer, {}).get("total", 0),
            })

    return {
        "verse_a": verse_a,
        "verse_b": verse_b,
        "shared_layers": shared,
        "verse_a_layers": {l: d["total"] for l, d in layers_a.items()},
        "verse_b_layers": {l: d["total"] for l, d in layers_b.items()},
    }


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(sys.stdin.read())

    conn = get_db()

    if "stats" in args:
        result = get_layer_stats(conn)

    elif "compare" in args:
        c = args["compare"]
        result = compare_verses(conn, c.get("verse_a"), c.get("verse_b"),
                               c.get("layers"))

    elif "verse" in args:
        result = get_verse_layers(conn, args["verse"],
                                 args.get("layers"),
                                 args.get("min_strength", 0))

    else:
        result = {"error": "Provide verse, compare, or stats"}

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
