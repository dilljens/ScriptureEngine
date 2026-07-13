"""
Shared tool: connection queries — layer, intertextual, PaRDeS.

Used by MCP (scripture_connections, scripture_intertext, scripture_pardes),
HTTP API (/api/v1/verses/{ref}/connections, etc.),
and CLI (tools/connections.py, tools/intertext.py, tools/pardes.py).
"""

import json
from collections import defaultdict

from lib.connections.pardes import (
    LEVELS as PARDES_LEVELS,
)
from lib.connections.pardes import (
    get_pardes_level,
)

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


def research_topic(conn, seed_verse, theme="", max_depth=3, layers=None, max_verses=30):
    """Multi-hop thematic research — walk the graph from a seed verse, collect findings.

    Accepts a theme/topic + seed verse, walks the connection graph,
    and returns a structured research brief with all discovered verses,
    their texts, and the connection paths between them.

    Args:
        seed_verse: Starting verse ID (gen.1.1)
        theme: Optional theme description for context
        max_depth: Max hops to traverse (default 3)
        layers: Optional list of layers to follow
        max_verses: Max verses to collect (default 30)

    Returns: dict with research brief
    """
    from collections import deque

    visited = {seed_verse}
    collected = []
    queue = deque([(seed_verse, 0, None, None)])  # (verse, depth, came_from, connection_info)

    layer_filter = ""
    if layers:
        placeholders = ",".join(f"'{layer}'" for layer in layers)
        layer_filter = f" AND c.layer IN ({placeholders})"

    while queue and len(collected) < max_verses:
        current, depth, came_from, conn_info = queue.popleft()

        # Collect current verse info
        info = _get_verse_info_simple(conn, current)
        if info:
            entry = {
                "verse": current,
                "text": info.get("text", ""),
                "book": info.get("book", ""),
                "depth": depth,
            }
            if came_from:
                entry["reached_via"] = {
                    "from": came_from,
                    "type": conn_info.get("type", ""),
                    "layer": conn_info.get("layer", ""),
                    "strength": conn_info.get("strength", 0),
                }
            collected.append(entry)

        if depth >= max_depth:
            continue

        # Walk outgoing connections
        rows = conn.execute(
            f"""
            SELECT c.target_verse, c.layer, c.type, c.strength
            FROM connections c
            WHERE c.source_verse = ? {layer_filter}
            ORDER BY c.strength DESC
            LIMIT 20
        """,
            (current,),
        ).fetchall()

        for r in rows:
            tv = r["target_verse"]
            if tv not in visited and len(collected) < max_verses:
                visited.add(tv)
                queue.append((tv, depth + 1, current, dict(r)))

        # Also walk incoming connections (bidirectional)
        if depth < 1:  # only for first hop from seed to keep it focused
            in_rows = conn.execute(
                f"""
                SELECT c.source_verse, c.layer, c.type, c.strength
                FROM connections c
                WHERE c.target_verse = ? {layer_filter}
                ORDER BY c.strength DESC
                LIMIT 10
            """,
                (current,),
            ).fetchall()
            for r in in_rows:
                sv = r["source_verse"]
                if sv not in visited and len(collected) < max_verses:
                    visited.add(sv)
                    queue.append((sv, depth + 1, current, dict(r)))

    # Build the research brief
    brief = {
        "seed_verse": seed_verse,
        "theme": theme,
        "max_depth": max_depth,
        "layers_used": layers or "all",
        "total_verses_found": len(collected),
        "verses": collected,
    }

    # Add seed verse info at the top
    seed_info = _get_verse_info_simple(conn, seed_verse)
    if seed_info:
        brief["seed"] = {
            "verse": seed_verse,
            "text": seed_info.get("text", ""),
            "book": seed_info.get("book", ""),
        }

    # Group by depth for LLM readability
    by_depth = defaultdict(list)
    for v in collected:
        by_depth[v["depth"]].append(v)
    brief["by_depth"] = {
        f"hop_{d}": verses
        for d, verses in sorted(by_depth.items())
    }

    # Collect unique layers encountered
    layers_found = set()
    for v in collected:
        if v.get("reached_via"):
            layers_found.add(v["reached_via"]["layer"])
    brief["layers_encountered"] = sorted(layers_found) if layers_found else None

    return brief


def _get_verse_info_simple(conn, verse_id):
    """Get brief info for a verse — text preview + book title."""
    row = conn.execute(
        """
        SELECT v.text_english, b.title as book_title
        FROM verses v
        JOIN books b ON b.id = v.book_id
        WHERE v.id = ?
    """,
        (verse_id,),
    ).fetchone()
    if row:
        return {"text": row["text_english"][:200], "book": row["book_title"]}
    return None


def compare_verses(conn, verse_a, verse_b, max_path_depth=4):
    """Compare two verses — path, shared entities, connection overlap, side-by-side text.

    Args:
        verse_a: First verse ID (gen.1.1)
        verse_b: Second verse ID (john.1.1)
        max_path_depth: Max path length in hops (default 4)

    Returns: dict with comparison results
    """
    from lib.api.graph import graph_path, graph_shared_entities
    from lib.api.verse import lookup_verse
    from lib.connections.pardes import get_pardes_level

    result = {"verse_a": verse_a, "verse_b": verse_b}

    # 1. Side-by-side text
    parts_a = verse_a.split(".")
    parts_b = verse_b.split(".")
    if len(parts_a) >= 3 and len(parts_b) >= 3:
        va = lookup_verse(conn, parts_a[0], int(parts_a[1]), int(parts_a[2]))
        vb = lookup_verse(conn, parts_b[0], int(parts_b[1]), int(parts_b[2]))
        if "error" not in va and "error" not in vb:
            result["text_a"] = {
                "reference": va.get("reference", verse_a),
                "text_english": va.get("text_english", ""),
                "text_hebrew": va.get("text_hebrew"),
                "text_greek": va.get("text_greek"),
            }
            result["text_b"] = {
                "reference": vb.get("reference", verse_b),
                "text_english": vb.get("text_english", ""),
                "text_hebrew": vb.get("text_hebrew"),
                "text_greek": vb.get("text_greek"),
            }

    # 2. Connection path
    path_result = graph_path(conn, verse_a, verse_b, max_depth=max_path_depth)
    if "error" not in path_result:
        result["connection_path"] = path_result
    else:
        result["connection_path"] = None

    # 3. Shared entities
    shared = graph_shared_entities(conn, verse_a, limit=50)
    result["shared_entities"] = shared.get("entities", [])

    # 4. Connection overlap (connection types both verses have)
    conns_a = conn.execute(
        "SELECT layer, type, COUNT(*) as c FROM connections WHERE source_verse = ? GROUP BY layer, type ORDER BY c DESC",
        (verse_a,),
    ).fetchall()
    conns_b = conn.execute(
        "SELECT layer, type, COUNT(*) as c FROM connections WHERE source_verse = ? GROUP BY layer, type ORDER BY c DESC",
        (verse_b,),
    ).fetchall()

    types_a = {(r["layer"], r["type"]): r["c"] for r in conns_a}
    types_b = {(r["layer"], r["type"]): r["c"] for r in conns_b}
    overlap = set(types_a.keys()) & set(types_b.keys())
    result["connection_overlap"] = [
        {"layer": layer, "type": typ, "count_a": types_a[(layer, typ)], "count_b": types_b[(layer, typ)]}
        for layer, typ in sorted(overlap)
    ]

    # 5. PaRDeS summary
    def get_layer_pardes(layer_name):
        for level_name in ["p'shat", "remez", "drash", "sod"]:
            pl = get_pardes_level(layer_name)
            if pl == level_name:
                return level_name
        return "p'shat"

    pardes_a = defaultdict(int)
    for r in conns_a:
        pardes_a[get_layer_pardes(r["layer"])] += r["c"]
    pardes_b = defaultdict(int)
    for r in conns_b:
        pardes_b[get_layer_pardes(r["layer"])] += r["c"]

    result["pardes_summary"] = {
        verse_a: dict(pardes_a),
        verse_b: dict(pardes_b),
    }

    # 6. Stats
    result["total_connections_a"] = sum(r["c"] for r in conns_a)
    result["total_connections_b"] = sum(r["c"] for r in conns_b)
    result["overlap_count"] = len(result["connection_overlap"])

    return result


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
