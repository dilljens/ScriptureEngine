"""
Shared tool: connection queries — layer, intertextual, PaRDeS.

Used by MCP (scripture_connections, scripture_intertext, scripture_pardes),
HTTP API (/api/v1/verses/{ref}/connections, etc.),
and CLI (tools/connections.py, tools/intertext.py, tools/pardes.py).
"""

import json
from collections import defaultdict
from lib.connections.pardes import (
    get_pardes_level,
    LEVELS as PARDES_LEVELS,
    get_connections_by_level,
)
from lib.connections.types import LAYERS as CONNECTION_LAYERS

CONNECTION_TYPE_MAP = {
    "linguistic": "Linguistic",
    "numerical": "Numerical",
    "structural": "Structural",
    "intertextual": "Intertextual",
    "textual": "Textual",
    "geographic": "Geographic",
    "chronological": "Chronological",
    "interpretive": "Interpretive",
    "frequency": "Frequency",
    "symbolic": "Symbolic",
}


def _get_connections_raw(conn, verse_id, layer=None):
    """Get connections from SQLite, optionally filtered by layer."""
    sql = """
        SELECT c.*, v.text_english as target_text,
               b.title as target_book_title
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
    """
    params = [verse_id]
    if layer:
        sql += " AND c.layer = ?"
        params.append(layer)
    sql += " ORDER BY c.layer, c.strength DESC"
    return conn.execute(sql, params).fetchall()


def get_connections(conn, verse, layer=None, min_quality=None):
    """Get all connections for a verse, optionally filtered.

    Args:
        verse: Verse ID (gen.1.1)
        layer: Optional layer name filter
        min_quality: Optional minimum quality level

    Returns: dict with verse, layers list, connections grouped by layer
    """
    rows = _get_connections_raw(conn, verse, layer=layer)
    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["layer"]].append(dict(r))

    # Resolve from passage guide JSON if available (full metadata)
    guide = conn.execute(
        "SELECT connections_json FROM passage_guides WHERE verse_id = ?", (verse,)
    ).fetchone()
    if guide:
        data = json.loads(guide["connections_json"])
        if layer and layer in data:
            by_layer = {layer: data[layer]}
        elif not layer:
            by_layer = data
        if not by_layer:
            by_layer = data

    result = {}
    for lyr, items in by_layer.items():
        result[lyr] = {
            "count": len(items),
            "name": CONNECTION_TYPE_MAP.get(lyr, lyr),
            "connections": items,
        }

    # Enrich interpretive connections with hermeneutic labels
    if "interpretive" in result:
        hermen_rows = conn.execute(
            """
            SELECT target_verse, type, subtype, hermeneutic
            FROM connections
            WHERE source_verse = ? AND layer = 'interpretive' AND hermeneutic IS NOT NULL
            """,
            (verse,),
        ).fetchall()
        hermen_map = {}
        for r in hermen_rows:
            hermen_map[(r["target_verse"], r["type"], r["subtype"])] = r["hermeneutic"]
        for c in result["interpretive"]["connections"]:
            tv = c.get("target_verse") or c.get("target", "")
            key = (tv, c.get("type", ""), c.get("subtype", ""))
            if key in hermen_map:
                c["hermeneutic"] = hermen_map[key]

    return {"verse": verse, "layers": list(result.keys()), "connections": result}


def get_intertext(conn, verse):
    """Get intertextual connections for a verse — quotations, allusions, echoes.

    Args:
        verse: Verse ID

    Returns: dict with verse, count, connections list
    """
    rows = conn.execute(
        """
        SELECT c.type, c.subtype, c.strength, c.target_verse,
               v.text_english as target_text, b.title as target_book
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ? AND c.layer = 'intertextual'
    """,
        (verse,),
    ).fetchall()

    return {"verse": verse, "count": len(rows), "connections": [dict(r) for r in rows]}


def get_pardes(conn, verse, level=None):
    """Get connections grouped by PaRDeS interpretation level.

    Args:
        verse: Verse ID
        level: Optional filter — 'pshat', 'remez', 'drash', 'sod'

    Returns: dict with verse, levels grouped with connections
    """
    # Get the passage guide for full connection data
    guide = conn.execute(
        "SELECT connections_json FROM passage_guides WHERE verse_id = ?", (verse,)
    ).fetchone()
    if not guide:
        return {"error": f"Verse {verse} not found in passage guides"}

    data = json.loads(guide["connections_json"])

    by_level = {}
    for layer, items in data.items():
        for item in items:
            lvl = get_pardes_level(layer, item.get("type", ""))
            if level and lvl != level:
                continue
            if lvl not in by_level:
                info = PARDES_LEVELS.get(lvl, {})
                by_level[lvl] = {
                    "name": info.get("name", lvl),
                    "hebrew": info.get("hebrew", ""),
                    "color": info.get("color", "#999"),
                    "connections": [],
                }
            by_level[lvl]["connections"].append({**item, "layer": layer})

    if level and level not in by_level and level in PARDES_LEVELS:
        info = PARDES_LEVELS[level]
        by_level[level] = {
            "name": info["name"],
            "hebrew": info["hebrew"],
            "color": info.get("color", "#999"),
            "connections": [],
        }

    return {"verse": verse, "levels": by_level}
