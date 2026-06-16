#!/usr/bin/env python3
"""
MCP Tool: scripture_connections
Get all typed connections for a verse, grouped by layer.

Usage: python3 connections.py '{"verse": "gen.1.1"}'
       python3 connections.py '{"verse": "gen.1.1", "layer": "numerical"}'
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db, get_connections_by_layer, get_connections
from lib.connections.graph import get_all_layers_for_verse, get_connection_summary
from lib.connections.types import LAYERS


def main():
    if len(sys.argv) < 2:
        args = json.loads(sys.stdin.read())
    else:
        args = json.loads(sys.argv[1])

    verse_id = args.get("verse", "")
    layer_filter = args.get("layer")
    format_type = args.get("format", "full")  # "full", "summary", "layers"

    if not verse_id:
        print(json.dumps({"error": "Provide a verse ID (e.g., gen.1.1)"}))
        return

    conn = get_db()

    if format_type == "summary":
        result = get_connection_summary(conn, verse_id)
        result["verse_id"] = verse_id
    elif format_type == "layers":
        result = get_all_layers_for_verse(conn, verse_id)
        result["verse_id"] = verse_id
    else:
        if layer_filter:
            all_layers = get_connections_by_layer(conn, verse_id)
            filtered = {layer_filter: all_layers.get(layer_filter, [])}
            result = {"verse_id": verse_id, "connections": filtered}
        else:
            all_layers = get_connections_by_layer(conn, verse_id)
            result = {"verse_id": verse_id, "connections": all_layers}

    # Add layer descriptions
    result["available_layers"] = [
        {"id": lid, "name": info["name"], "description": info["description"]}
        for lid, info in LAYERS.items()
    ]

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
