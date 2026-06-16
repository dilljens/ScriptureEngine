"""
Connection graph engine — query and analyze the typed connection graph.

Provides high-level queries across all 9 connection layers.
"""

import json
from collections import defaultdict
from ..db import get_db, get_connections, get_connections_by_layer, add_connection
from .types import LAYERS


def get_all_layers_for_verse(conn, verse_id):
    """Get all connections for a verse, organized by layer with summaries."""
    by_layer = get_connections_by_layer(conn, verse_id)

    result = {}
    for layer_name, connections in by_layer.items():
        layer_info = LAYERS.get(layer_name, {})
        types_used = defaultdict(list)

        for c in connections:
            types_used[c["type"]].append(c)

        result[layer_name] = {
            "layer_name": layer_info.get("name", layer_name),
            "layer_description": layer_info.get("description", ""),
            "total_connections": len(connections),
            "by_type": {
                t: {
                    "count": len(c_list),
                    "connections": c_list,
                }
                for t, c_list in types_used.items()
            },
        }

    return result


def get_connection_summary(conn, verse_id):
    """Get a concise summary of all connections for a verse."""
    by_layer = get_connections_by_layer(conn, verse_id)

    summary = {}
    for layer, connections in by_layer.items():
        layer_info = LAYERS.get(layer, {})
        types = defaultdict(int)
        discovered = defaultdict(int)
        for c in connections:
            types[c["type"]] += 1
            discovered[c["discovered_by"]] += 1

        summary[layer] = {
            "name": layer_info.get("name", layer),
            "count": len(connections),
            "types": dict(types),
            "discovered_by": dict(discovered),
        }

    return summary


def find_path(conn, start_verse, end_verse, max_depth=3):
    """Find connection paths between two verses (up to max_depth hops).

    Uses BFS through the connection graph.
    """
    visited = {start_verse}
    queue = [(start_verse, [])]

    while queue:
        current, path = queue.pop(0)
        if len(path) >= max_depth:
            continue

        # Get outgoing connections
        current_connections = get_connections(conn, current)

        for c in current_connections:
            neighbor = c["target_verse"]
            new_path = path + [{
                "from": current,
                "to": neighbor,
                "layer": c["layer"],
                "type": c["type"],
                "subtype": c["subtype"],
            }]

            if neighbor == end_verse:
                return new_path

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, new_path))

    return None


def get_layer_statistics(conn):
    """Get statistics about connections in each layer."""
    rows = conn.execute("""
        SELECT layer, type, COUNT(*) as count,
               AVG(strength) as avg_strength,
               AVG(confidence) as avg_confidence
        FROM connections
        GROUP BY layer, type
        ORDER BY layer, count DESC
    """).fetchall()

    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["layer"]].append({
            "type": r["type"],
            "count": r["count"],
            "avg_strength": round(r["avg_strength"], 2),
            "avg_confidence": round(r["avg_confidence"], 2),
        })

    return dict(by_layer)


def connect_parallel_verses(conn, verse_a, verse_b, layer, type_name,
                            subtype="", strength=0.5, metadata=None):
    """Create a bidirectional connection between two verses."""
    add_connection(conn, verse_a, verse_b, layer, type_name,
                  subtype=subtype, strength=strength, metadata=metadata)
    add_connection(conn, verse_b, verse_a, layer, type_name,
                  subtype=subtype, strength=strength, metadata=metadata)


def verses_with_most_connections(conn, limit=20):
    """Find verses with the most connections."""
    rows = conn.execute("""
        SELECT source_verse, COUNT(*) as connection_count,
               MAX(strength) as max_strength,
               GROUP_CONCAT(DISTINCT layer) as layers
        FROM connections
        GROUP BY source_verse
        ORDER BY connection_count DESC
        LIMIT ?
    """, (limit,)).fetchall()

    result = []
    for r in rows:
        v = conn.execute("""
            SELECT v.text_english, b.title as book_title
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (r["source_verse"],)).fetchone()

        result.append({
            "verse_id": r["source_verse"],
            "connection_count": r["connection_count"],
            "max_strength": r["max_strength"],
            "layers": r["layers"].split(",") if r["layers"] else [],
            "text": v["text_english"][:100] if v else "",
            "book": v["book_title"] if v else "",
        })

    return result


def find_all_paths(conn, start_verse, end_verse=None, max_depth=6, layer_filter=None):
    """Find all connection paths up to max_depth hops using recursive CTE.

    This is the SPARQL-style property path equivalent — finds transitive
    connections between verses through any chain of relationships.

    Args:
        start_verse: starting verse ID
        end_verse: optional target verse ID. If None, returns all reachable verses.
        max_depth: maximum path length (default 6 hops)
        layer_filter: optional list of layer names to restrict traversal

    Returns:
        list of path dicts, each path is [{from, to, layer, type}, ...]
        or if end_verse is None: dict of {reachable_verse_id: [path, ...]}
    """
    if not layer_filter:
        # Start with the first verse's connections to find what layers are available
        sample = conn.execute("""
            SELECT DISTINCT layer FROM connections
            WHERE source_verse = ? OR target_verse = ?
            LIMIT 5
        """, (start_verse, start_verse)).fetchall()

    # Use SQLite recursive CTE for path finding
    if end_verse:
        # Specific target — find shortest path
        rows = conn.execute("""
            WITH RECURSIVE
            paths(verse_id, path_json, depth) AS (
                SELECT target_verse,
                       json_array(json_object('from', source_verse, 'to', target_verse, 'layer', layer, 'type', type)),
                       1
                FROM connections
                WHERE source_verse = ?
                UNION
                SELECT c.target_verse,
                       json_insert(p.path_json, '$[#]', json_object('from', c.source_verse, 'to', c.target_verse, 'layer', c.layer, 'type', c.type)),
                       p.depth + 1
                FROM paths p
                JOIN connections c ON c.source_verse = p.verse_id
                WHERE p.depth < ?
                  AND p.verse_id != ?
            )
            SELECT path_json, depth FROM paths
            WHERE verse_id = ?
            ORDER BY depth
            LIMIT 20
        """, (start_verse, max_depth, end_verse, end_verse)).fetchall()
    else:
        # No target — find all reachable verses
        rows = conn.execute("""
            WITH RECURSIVE
            paths(verse_id, path_json, depth) AS (
                SELECT target_verse,
                       json_array(json_object('from', source_verse, 'to', target_verse, 'layer', layer, 'type', type)),
                       1
                FROM connections
                WHERE source_verse = ?
                UNION
                SELECT c.target_verse,
                       json_insert(p.path_json, '$[#]', json_object('from', c.source_verse, 'to', c.target_verse, 'layer', c.layer, 'type', c.type)),
                       p.depth + 1
                FROM paths p
                JOIN connections c ON c.source_verse = p.verse_id
                WHERE p.depth < ?
            )
            SELECT verse_id, path_json, depth FROM paths
            ORDER BY depth
            LIMIT 200
        """, (start_verse, max_depth)).fetchall()

    results = []
    for r in rows:
        try:
            path = json.loads(r["path_json"])
            results.append({
                "path": path,
                "depth": r["depth"],
                "start": start_verse,
                "end": r["verse_id"],
            })
        except (json.JSONDecodeError, TypeError):
            continue

    return results


def find_hub_verses(conn, min_connections=2, layer=None, limit=30):
    """Find 'hub' verses — those that connect to the most diverse other verses.

    These are the key nodes in the connection graph that bridge
    different books, layers, or themes.
    """
    sql = """
        SELECT source_verse,
               COUNT(DISTINCT target_verse) as unique_targets,
               COUNT(DISTINCT layer) as unique_layers,
               GROUP_CONCAT(DISTINCT layer) as layers_used,
               ROUND(AVG(strength), 2) as avg_strength
        FROM connections
    """
    params = []
    wheres = []
    if layer:
        wheres.append("layer = ?")
        params.append(layer)

    sql += " WHERE " + " AND ".join(wheres) if wheres else ""
    sql += " GROUP BY source_verse HAVING unique_targets >= ?"
    params.append(min_connections)
    sql += " ORDER BY unique_targets DESC, avg_strength DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        v = conn.execute("""
            SELECT v.text_english, b.title as book_title
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (r["source_verse"],)).fetchone()
        result.append({
            "verse_id": r["source_verse"],
            "unique_targets": r["unique_targets"],
            "unique_layers": r["unique_layers"],
            "layers_used": r["layers_used"].split(",") if r["layers_used"] else [],
            "avg_strength": r["avg_strength"],
            "text": v["text_english"][:120] if v else "",
            "book": v["book_title"] if v else "",
        })

    return result


def network_stats(conn):
    """Get overall connection graph statistics."""
    rows = conn.execute("""
        SELECT
            COUNT(*) as total_connections,
            COUNT(DISTINCT source_verse) as unique_source_verses,
            COUNT(DISTINCT target_verse) as unique_target_verses,
            COUNT(DISTINCT layer) as unique_layers,
            AVG(strength) as avg_strength,
            AVG(confidence) as avg_confidence
        FROM connections
    """).fetchone()

    stats = dict(rows) if rows else {}

    # Also get some graph-level metrics
    hub_count = conn.execute("""
        SELECT COUNT(*) as c FROM (
            SELECT source_verse FROM connections
            GROUP BY source_verse HAVING COUNT(DISTINCT target_verse) >= 2
        )
    """).fetchone()["c"]

    stats["hub_verses_min_2"] = hub_count

    return stats
