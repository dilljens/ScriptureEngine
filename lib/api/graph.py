"""
Shared tool: graph traversal and entity-aware queries.

New graph capabilities powered by the connection graph + verse_entities table:
  - Shortest path between any two verses
  - All reachable verses within N hops
  - Hub verse detection
  - Entity-linked verses
  - Shared entity discovery

Used by MCP (scripture_graph_*),
HTTP API (/api/v1/graph/*),
and CLI.
"""

import json
from collections import defaultdict


# ─── Connection Graph Traversal ───


def graph_path(conn, start, end, max_depth=3, layers=None):
    """Find the shortest connection path between two verses.

    Uses recursive CTE for BFS through the connection graph.

    Args:
        start: Starting verse ID (gen.1.1)
        end: Target verse ID
        max_depth: Maximum path length in hops (default 3)
        layers: Optional list of layers to restrict traversal

    Returns: list of path segments, or message if no path found
    """
    from lib.connections.graph import find_path as bfs_find_path

    # Use BFS from the existing graph module
    path = bfs_find_path(conn, start, end, max_depth=max_depth)
    if not path:
        # Try the recursive CTE approach which may find paths BFS misses
        rows = _cte_find_path(conn, start, end, max_depth, layers)
        if not rows:
            return {"error": f"No path found between {start} and {end} within {max_depth} hops"}

        path = _format_cte_path(start, rows)

    # Enrich with book titles and text
    enriched = []
    for seg in path:
        from_info = _get_verse_info(conn, seg.get("from", ""))
        to_info = _get_verse_info(conn, seg.get("to", ""))
        enriched.append({
            **seg,
            "from_text": from_info["text"] if from_info else "",
            "from_book": from_info["book"] if from_info else "",
            "to_text": to_info["text"] if to_info else "",
            "to_book": to_info["book"] if to_info else "",
        })

    return {
        "start": start,
        "end": end,
        "hops": len(enriched),
        "path": enriched,
    }


def _cte_find_path(conn, start, end, max_depth=3, layers=None):
    """Recursive CTE path finding — finds the shortest path."""
    layer_filter = ""
    if layers:
        placeholders = ",".join(f"'{l}'" for l in layers)
        layer_filter = f"AND c.layer IN ({placeholders})"

    rows = conn.execute(
        f"""
        WITH RECURSIVE
        paths(verse_id, path_json, depth) AS (
            SELECT target_verse,
                   json_array(json_object('from', source_verse, 'to', target_verse, 'layer', layer, 'type', type)),
                   1
            FROM connections c
            WHERE source_verse = ? {layer_filter}
            UNION
            SELECT c.target_verse,
                   json_insert(p.path_json, '$[#]',
                       json_object('from', c.source_verse, 'to', c.target_verse, 'layer', c.layer, 'type', c.type)),
                   p.depth + 1
            FROM paths p
            JOIN connections c ON c.source_verse = p.verse_id
            WHERE p.depth < ? AND p.verse_id != ?
        )
        SELECT path_json, depth FROM paths
        WHERE verse_id = ?
        ORDER BY depth
        LIMIT 1
    """,
        (start, max_depth, end, end),
    ).fetchall()
    return rows


def _format_cte_path(start, rows):
    """Format CTE path result into path segments."""
    if not rows:
        return None
    r = rows[0]
    try:
        return json.loads(r["path_json"])
    except (json.JSONDecodeError, TypeError):
        return None


def _get_verse_info(conn, verse_id):
    """Get brief info (book, text preview) for a verse."""
    if not verse_id:
        return None
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
        return {"text": row["text_english"][:120], "book": row["book_title"]}
    return None


def graph_reachable(conn, verse, max_depth=3, layers=None, limit=100):
    """Find all verses reachable within N hops from a starting verse.

    Args:
        verse: Starting verse ID
        max_depth: Maximum hop depth (default 3)
        layers: Optional list of layers to restrict traversal
        limit: Max results (default 100)

    Returns: dict with depth list of reachable verses
    """
    layer_filter = ""
    if layers:
        placeholders = ",".join(f"'{l}'" for l in layers)
        layer_filter = f"AND c.layer IN ({placeholders})"

    rows = conn.execute(
        f"""
        WITH RECURSIVE
        reachable(verse_id, depth) AS (
            SELECT DISTINCT c.target_verse, 1
            FROM connections c
            WHERE c.source_verse = ? {layer_filter}
            UNION
            SELECT DISTINCT c.target_verse, r.depth + 1
            FROM reachable r
            JOIN connections c ON c.source_verse = r.verse_id
            WHERE r.depth < ?
        )
        SELECT verse_id, MIN(depth) as depth
        FROM reachable
        GROUP BY verse_id
        ORDER BY depth
        LIMIT ?
    """,
        (verse, max_depth, limit),
    ).fetchall()

    by_depth = defaultdict(list)
    for r in rows:
        info = _get_verse_info(conn, r["verse_id"])
        by_depth[r["depth"]].append({
            "verse": r["verse_id"],
            "text": info["text"] if info else "",
            "book": info["book"] if info else "",
        })

    return {
        "start": verse,
        "total": len(rows),
        "by_depth": dict(by_depth),
    }


def graph_hubs(conn, min_connections=3, layer=None, limit=30):
    """Find 'hub' verses — those connecting to the most diverse other verses.

    Args:
        min_connections: Minimum distinct targets to qualify (default 3)
        layer: Optional layer to scope the search
        limit: Max results (default 30)

    Returns: list of hub verses with metrics
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
        info = _get_verse_info(conn, r["source_verse"])
        result.append({
            "verse_id": r["source_verse"],
            "unique_targets": r["unique_targets"],
            "unique_layers": r["unique_layers"],
            "layers_used": (
                r["layers_used"].split(",") if r["layers_used"] else []
            ),
            "avg_strength": r["avg_strength"],
            "text": info["text"] if info else "",
            "book": info["book"] if info else "",
        })

    return {"hubs": result, "total": len(result)}


# ─── Entity-Aware Traversal (powered by verse_entities table) ───


def graph_entities(conn, verse, min_confidence=0.3):
    """Get entities linked to a specific verse.

    Args:
        verse: Verse ID
        min_confidence: Minimum confidence threshold (default 0.3)

    Returns: list of entities with type, name, relationship
    """
    rows = conn.execute(
        """
        SELECT ve.*, el.entity_type, el.english_name, el.hebrew_name,
               el.greek_name, el.notes
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        WHERE ve.verse_id = ? AND ve.confidence >= ?
        ORDER BY ve.confidence DESC
    """,
        (verse, min_confidence),
    ).fetchall()

    return {
        "verse": verse,
        "total": len(rows),
        "entities": [
            {
                "entity_id": r["entity_id"],
                "type": r["entity_type"],
                "english_name": r["english_name"],
                "hebrew_name": r["hebrew_name"],
                "greek_name": r["greek_name"],
                "relationship": r["relationship_type"],
                "confidence": r["confidence"],
            }
            for r in rows
        ],
    }


def graph_shared_entities(conn, verse, min_confidence=0.3, limit=50):
    """Find other verses that share entities with this verse.

    Args:
        verse: Verse ID to start from
        min_confidence: Minimum entity link confidence
        limit: Max results

    Returns: dict with shared entities and verses sharing them
    """
    # Get entities for this verse
    entity_rows = conn.execute(
        """
        SELECT ve.entity_id, el.english_name, el.entity_type
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        WHERE ve.verse_id = ? AND ve.confidence >= ?
    """,
        (verse, min_confidence),
    ).fetchall()

    if not entity_rows:
        return {"verse": verse, "total_entities": 0, "shared_verses": []}

    entity_ids = [r["entity_id"] for r in entity_rows]

    # Build entity info lookup
    entity_info = {r["entity_id"]: {"name": r["english_name"], "type": r["entity_type"]}
                   for r in entity_rows}

    # Find all verses sharing these entities (excluding this verse)
    placeholders = ",".join("?" for _ in entity_ids)
    rows = conn.execute(
        f"""
        SELECT ve.verse_id, ve.entity_id, ve.relationship_type, ve.confidence,
               v.text_english, b.title as book_title
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE ve.entity_id IN ({placeholders})
          AND ve.verse_id != ?
          AND ve.confidence >= ?
        ORDER BY ve.verse_id, ve.confidence DESC
        LIMIT ?
    """,
        (*entity_ids, verse, min_confidence, limit),
    ).fetchall()

    # Group by verse
    by_verse = defaultdict(list)
    for r in rows:
        by_verse[r["verse_id"]].append({
            "entity_id": r["entity_id"],
            "entity_name": entity_info.get(r["entity_id"], {}).get("name", ""),
            "entity_type": entity_info.get(r["entity_id"], {}).get("type", ""),
            "relationship": r["relationship_type"],
            "confidence": r["confidence"],
        })

    return {
        "verse": verse,
        "total_entities": len(entity_ids),
        "entities": [{"id": eid, **info} for eid, info in entity_info.items()],
        "total_shared_verses": len(by_verse),
        "shared_verses": [
            {
                "verse": vid,
                "text": rows_by_v[0].get("text_english", "")[:120],
                "book": rows_by_v[0].get("book_title", ""),
                "shared_entities": entities,
                "entity_count": len(entities),
            }
            for vid, entities in by_verse.items()
            for rows_by_v in (
                [
                    r
                    for r in rows
                    if r["verse_id"] == vid
                ],
            )
            for _ in [None]  # hack to bind rows_by_v
        ],
    }


def graph_entity_network(conn, entity, min_confidence=0.3, limit=100):
    """Get all verses connected to a specific entity.

    Args:
        entity: Entity ID (e.g., 'person.abraham')
        min_confidence: Minimum confidence threshold
        limit: Max results

    Returns: dict with entity info and associated verses
    """
    # Get entity info
    entity_row = conn.execute(
        "SELECT * FROM entity_links WHERE entity_id = ?", (entity,)
    ).fetchone()
    if not entity_row:
        return {"error": f"Entity not found: {entity}"}

    # Get verses linked to this entity
    rows = conn.execute(
        """
        SELECT ve.verse_id, ve.relationship_type, ve.confidence,
               v.text_english, b.title as book_title, b.id as book_id
        FROM verse_entities ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE ve.entity_id = ? AND ve.confidence >= ?
        ORDER BY b.position, v.chapter, v.verse
        LIMIT ?
    """,
        (entity, min_confidence, limit),
    ).fetchall()

    return {
        "entity": {
            "id": entity_row["entity_id"],
            "type": entity_row["entity_type"],
            "english_name": entity_row["english_name"],
            "hebrew_name": entity_row["hebrew_name"],
            "greek_name": entity_row["greek_name"],
        },
        "total_verses": len(rows),
        "by_book": defaultdict(
            list,
            {
                bid: [
                    {
                        "verse": r["verse_id"],
                        "text": r["text_english"][:120],
                        "relationship": r["relationship_type"],
                        "confidence": r["confidence"],
                    }
                    for r in rows
                ]
                for bid in set(r["book_id"] for r in rows)
            },
        ),
    }


def graph_centrality(conn, book=None, layer=None, limit=20):
    """Find the most central (best-connected) verses in the graph.

    Measures degree centrality based on connection count.

    Args:
        book: Optional book ID to scope the analysis
        layer: Optional layer to scope the analysis
        limit: Max results (default 20)

    Returns: list of verses ranked by centrality
    """
    sql = """
        SELECT source_verse,
               COUNT(*) as connection_count,
               COUNT(DISTINCT target_verse) as unique_targets,
               COUNT(DISTINCT layer) as unique_layers,
               ROUND(AVG(strength), 2) as avg_strength,
               ROUND(SUM(strength), 2) as total_strength
        FROM connections
    """
    params = []
    wheres = []

    if book:
        wheres.append("source_verse LIKE ?")
        params.append(f"{book}.%")
    if layer:
        wheres.append("layer = ?")
        params.append(layer)

    if wheres:
        sql += " WHERE " + " AND ".join(wheres)
    sql += " GROUP BY source_verse ORDER BY connection_count DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        info = _get_verse_info(conn, r["source_verse"])
        result.append({
            "verse_id": r["source_verse"],
            "connection_count": r["connection_count"],
            "unique_targets": r["unique_targets"],
            "unique_layers": r["unique_layers"],
            "avg_strength": r["avg_strength"],
            "total_strength": r["total_strength"],
            "text": info["text"] if info else "",
            "book": info["book"] if info else "",
        })

    return {
        "centrality": result,
        "total": len(result),
        "scope": {"book": book, "layer": layer},
    }


def graph_stats(conn):
    """Get overall connection graph statistics.

    Returns: dict with total connections, unique verses, hubs, etc.
    """
    from lib.connections.graph import network_stats

    return network_stats(conn)
