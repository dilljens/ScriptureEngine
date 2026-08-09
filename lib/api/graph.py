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

from lib.api.passage import derive_granularity, split_embedded_range

# ─── Connection Graph Traversal ───


# ── Passage-level edges (verse↔chapter / verse↔chunk / chapter↔book) ──

def _parse_vid(vid):
    """Parse 'book.ch.verse' → (book, ch, vs) for numeric comparison. Non-verse
    refs (entity ids, commentary ids) return None."""
    parts = str(vid).split(".")
    if len(parts) != 3:
        return None
    try:
        return parts[0], int(parts[1]), int(parts[2])
    except ValueError:
        return None


def _book_of(ref):
    """Book prefix of a ref like 'gen.1.1' → 'gen'. None for unparseable refs."""
    parts = str(ref or "").split(".")
    return parts[0] if parts and parts[0] else None


def _in_range(vid, start, end):
    """True if vid falls within the inclusive range [start, end], compared
    numerically per component (string BETWEEN is wrong for ch.10 < ch.2)."""
    v = _parse_vid(vid)
    s = _parse_vid(start)
    e = _parse_vid(end)
    if not (v and s and e) or v[0] != s[0] or v[0] != e[0]:
        return False
    return (s[1], s[2]) <= (v[1], v[2]) <= (e[1], e[2])


# Module-level cache for the passage table — it changes only when generators
# run (batch jobs), so a short TTL makes repeated traversal calls cheap while
# staying fresh. Guarded implicitly by the GIL (worst case: two threads rebuild).
_passages_cache = {"at": 0.0, "passages": None, "by_book": None}
_PASSAGES_TTL = 30.0  # seconds


def _load_passages(conn):
    """Load all passage_connections, normalized (embedded '--' ranges split),
    and index them by book on BOTH sides (source book and target book).

    ~100k rows; cached for _PASSAGES_TTL seconds. The book index keeps per-verse
    neighbor lookup O(passages-in-that-book) instead of O(all passages).
    Returns (passages, by_book) where by_book[book] is a list of passage indices.
    """
    import time as _time
    now = _time.time()
    if _passages_cache["passages"] is not None and now - _passages_cache["at"] < _PASSAGES_TTL:
        return _passages_cache["passages"], _passages_cache["by_book"]

    rows = conn.execute("""
        SELECT source_start, source_end, target_start, target_end,
               layer, type, subtype, strength, confidence
        FROM passage_connections
    """).fetchall()
    passages = []
    by_book = defaultdict(list)
    for r in rows:
        ss, se = split_embedded_range(r["source_start"], r["source_end"])
        ts, te = split_embedded_range(r["target_start"], r["target_end"])
        idx = len(passages)
        passages.append({
            "source_start": ss, "source_end": se,
            "target_start": ts, "target_end": te,
            "layer": r["layer"], "type": r["type"], "subtype": r["subtype"] or "",
            "strength": r["strength"], "confidence": r["confidence"],
        })
        for book in {_book_of(ss), _book_of(ts)}:
            if book:
                by_book[book].append(idx)
    _passages_cache["at"] = now
    _passages_cache["passages"] = passages
    _passages_cache["by_book"] = by_book
    return passages, by_book


def _passage_neighbors(passages, by_book, verse_id):
    """Passage-level edges touching verse_id: passages whose range contains it.

    Only passages in the verse's own book are candidates (ranges never cross
    into the verse's book from another book without being indexed under it).
    Returns edge dicts whose `to` is the anchor verse of the far side of the
    passage (the far range's start).
    """
    edges = []
    book = _book_of(verse_id)
    if not book or not _parse_vid(verse_id):
        return edges
    for idx in by_book.get(book, ()):
        p = passages[idx]
        if _in_range(verse_id, p["source_start"], p["source_end"]):
            edges.append({
                "to": p["target_start"],
                "to_end": p["target_end"],
                "layer": p["layer"], "type": p["type"], "subtype": p["subtype"],
                "strength": p["strength"], "confidence": p["confidence"],
                "passage": True,
                "granularity": derive_granularity(p["source_start"], p["source_end"]),
            })
        elif _in_range(verse_id, p["target_start"], p["target_end"]):
            edges.append({
                "to": p["source_start"],
                "to_end": p["source_end"],
                "layer": p["layer"], "type": p["type"], "subtype": p["subtype"],
                "strength": p["strength"], "confidence": p["confidence"],
                "passage": True,
                "granularity": derive_granularity(p["target_start"], p["target_end"]),
            })
    return edges


def _passage_segment(from_verse, edge, reverse=False):
    """Build a path segment dict for a passage edge."""
    to = edge["to"] if not reverse else from_verse
    frm = from_verse if not reverse else edge["to"]
    return {
        "from": frm,
        "to": to,
        "layer": edge["layer"],
        "type": edge["type"],
        "subtype": edge.get("subtype", ""),
        "passage": True,
        "passage_to": edge["to_end"],
        "granularity": edge["granularity"],
    }


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
            # Finally: bridge through passage-level (chapter/chunk/book) edges
            path = _passage_bridged_path(conn, start, end, max_depth)
            if not path:
                return {"error": f"No path found between {start} and {end} within {max_depth} hops"}
        else:
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
        placeholders = ",".join(f"'{layer}'" for layer in layers)
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


def _passage_bridged_path(conn, start, end, max_depth):
    """Find a path where start/end hop onto passage-level (chapter/chunk/book)
    edges: start --passage--> anchor ... direct verse link ... anchor' --passage--> end.

    Only called when the verse-level BFS + CTE found nothing. Two shapes:
      • start and end share the same passage anchor (2-hop passage path)
      • the far-side anchors are directly verse-connected (3-hop mixed path)
    Both are single cheap SELECTs — no recursive BFS (that's what made the
    bridge slow). Returns a list of segments, or None.
    """
    passages, by_book = _load_passages(conn)
    start_edges = sorted(_passage_neighbors(passages, by_book, start),
                         key=lambda e: -(e["strength"] or 0))[:5]
    end_edges = sorted(_passage_neighbors(passages, by_book, end),
                       key=lambda e: -(e["strength"] or 0))[:5]
    if not start_edges or not end_edges:
        return None

    for se in start_edges:
        for ee in end_edges:
            if se["to"] == ee["to"]:
                return [_passage_segment(start, se), _passage_segment(end, ee, reverse=True)]
            # Direct verse connection between the two anchors?
            for frm, to in ((se["to"], ee["to"]), (ee["to"], se["to"])):
                row = conn.execute(
                    "SELECT layer, type, subtype FROM connections WHERE source_verse=? AND target_verse=? LIMIT 1",
                    (frm, to),
                ).fetchone()
                if row:
                    mid = {"from": frm, "to": to, "layer": row["layer"],
                           "type": row["type"], "subtype": row["subtype"] or ""}
                    return [_passage_segment(start, se), mid, _passage_segment(end, ee, reverse=True)]
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
        placeholders = ",".join(f"'{layer}'" for layer in layers)
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
    seen = set()
    for r in rows:
        vid = r["verse_id"]
        if vid in seen:
            continue
        seen.add(vid)
        info = _get_verse_info(conn, vid)
        by_depth[r["depth"]].append({
            "verse": vid,
            "text": info["text"] if info else "",
            "book": info["book"] if info else "",
        })

    # Passage expansion: the seed verse AND verses inside a passage range reach
    # the far side's anchor (chapter/chunk/book edges) at depth+1. Keep the
    # strongest few per verse (a verse can sit in hundreds of passages) and
    # insert them at the front of their depth bucket so the limit keeps them.
    if max_depth > 1:
        passages, by_book = _load_passages(conn)

        def _expand(verse_id, target_depth):
            for edge in sorted(_passage_neighbors(passages, by_book, verse_id),
                               key=lambda e: -(e["strength"] or 0))[:5]:
                to = edge["to"]
                if to == verse_id or to in seen:
                    continue
                seen.add(to)
                by_depth[target_depth].insert(0, {
                    "verse": to,
                    "text": "",
                    "book": "",
                    "passage": True,
                    "passage_to": edge["to_end"],
                    "layer": edge["layer"],
                    "type": edge["type"],
                    "granularity": edge["granularity"],
                })

        # Seed's own passage edges land at depth 1 (CTE never includes it).
        _expand(verse, 1)
        for depth in sorted(by_depth):
            if depth >= max_depth:
                break
            for entry in list(by_depth[depth]):
                _expand(entry["verse"], depth + 1)
        # Re-truncate to the limit (passage expansion may have exceeded it)
        flat = [(d, e) for d in sorted(by_depth) for e in by_depth[d]]
        if len(flat) > limit:
            by_depth = defaultdict(list)
            for d, e in flat[:limit]:
                by_depth[d].append(e)

    return {
        "start": verse,
        "total": sum(len(v) for v in by_depth.values()),
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


def graph_context(conn, verse, depth=2, layers=None, limit=20):
    """N-hop neighborhood formatted as structured text for LLM consumption.

    Returns verse text + typed relationships as readable text (not JSON),
    optimized for LLMs to reason over.

    Args:
        verse: Starting verse ID
        depth: How many hops to traverse (default 2)
        layers: Optional list of layer names to restrict
        limit: Max verses to include (default 20)

    Returns: dict with structured context
    """
    verse.split(".")
    context = {
        "verse": verse,
        "depth": depth,
        "layers": layers,
        "focal_verse": {},
        "neighborhood": [],
    }

    # Get verse info
    info = _get_verse_info(conn, verse)
    if info:
        context["focal_verse"] = {
            "verse": verse,
            "text": info.get("text", ""),
            "book": info.get("book", ""),
        }

    # Get 1-hop neighbors
    layer_filter = ""
    params = [verse, depth]
    if layers:
        placeholders = ",".join(f"'{layer}'" for layer in layers)
        layer_filter = f" AND c.layer IN ({placeholders})"

    rows = conn.execute(
        f"""
        SELECT c.target_verse, c.layer, c.type, c.subtype, c.strength, c.confidence,
               c.discovered_by, v.text_english as target_text, b.title as target_book
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ? {layer_filter}
        ORDER BY c.strength DESC
        LIMIT ?
    """,
        params + [limit],
    ).fetchall()

    # Group by layer and format as structured text
    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["layer"]].append({
            "target": r["target_verse"],
            "type": r["type"],
            "subtype": r["subtype"],
            "strength": r["strength"],
            "confidence": r["confidence"],
            "discovered_by": r["discovered_by"],
            "target_text": (r["target_text"] or "")[:150],
            "target_book": r["target_book"],
        })

    context["neighborhood"] = [
        {
            "layer": layer,
            "count": len(conns),
            "connections": conns,
        }
        for layer, conns in by_layer.items()
    ]

    # Build structured text representation
    text_parts = [f"=== Verse {verse} ==="]
    if info:
        text_parts.append(f"{info.get('book', '')}:")
        text_parts.append(f"\"{info.get('text', '')}\"")
    text_parts.append("")

    for layer_group in context["neighborhood"]:
        text_parts.append(f"--- {layer_group['layer']} ({layer_group['count']} connections) ---")
        for c in layer_group["connections"][:8]:
            strength_str = f" [strength={c['strength']:.1f}, conf={c['confidence']:.0%}]" if c.get("strength") else ""
            text_parts.append(f"  {c['type']} → {c['target']}{strength_str}")
            if c.get("target_text"):
                text_parts.append(f"    \"{c['target_text'][:100]}\"")
        if layer_group["count"] > 8:
            text_parts.append(f"  ... and {layer_group['count'] - 8} more")

    context["structured_text"] = "\n".join(text_parts)
    return context


def entity_deep(conn, entity, min_confidence=0.3, limit=100):
    """Deep dive on a biblical entity — all verses, connections, and related entities.

    Args:
        entity: Entity ID (e.g., 'person.abraham', 'place.zion')
        min_confidence: Minimum entity link confidence
        limit: Max verses to return

    Returns: dict with entity info, all verses, connections involving entity, related entities
    """
    # Get entity info
    entity_row = conn.execute(
        "SELECT * FROM entity_links WHERE entity_id = ?", (entity,)
    ).fetchone()
    if not entity_row:
        return {"error": f"Entity not found: {entity}"}

    entity_info = {
        "id": entity_row["entity_id"],
        "type": entity_row["entity_type"],
        "english_name": entity_row["english_name"],
        "hebrew_name": entity_row["hebrew_name"],
        "greek_name": entity_row["greek_name"],
        "strongs": entity_row.get("strongs", ""),
        "notes": entity_row.get("notes", ""),
    }

    # Get all verses linked to this entity
    verse_rows = conn.execute(
        """
        SELECT ve.verse_id, ve.relationship_type, ve.confidence,
               v.text_english, b.title as book_title, b.id as book_id,
               v.chapter, v.verse
        FROM verse_entities ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE ve.entity_id = ? AND ve.confidence >= ?
        ORDER BY b.position, v.chapter, v.verse
        LIMIT ?
    """,
        (entity, min_confidence, limit),
    ).fetchall()

    verses = []
    verse_ids = []
    for r in verse_rows:
        verses.append({
            "verse": r["verse_id"],
            "text": (r["text_english"] or "")[:200],
            "book": r["book_title"],
            "chapter": r["chapter"],
            "verse_num": r["verse"],
            "relationship": r["relationship_type"],
            "confidence": r["confidence"],
        })
        verse_ids.append(r["verse_id"])

    # Get connections involving this entity (connections where either end is in the verse list)
    # This finds connections BETWEEN verses that mention the entity
    entity_connections = []
    if verse_ids:
        placeholders = ",".join("?" for _ in verse_ids[:50])  # cap at 50
        conn_rows = conn.execute(
            f"""
            SELECT c.source_verse, c.target_verse, c.layer, c.type, c.strength
            FROM connections c
            WHERE c.source_verse IN ({placeholders})
            AND c.target_verse IN ({placeholders})
            AND c.source_verse != c.target_verse
            LIMIT 100
        """,
            verse_ids[:50] + verse_ids[:50],
        ).fetchall()
        entity_connections = [dict(r) for r in conn_rows]

    # Find related entities (other entities that appear in the same verses)
    related = []
    if verse_ids:
        related_rows = conn.execute(
            f"""
            SELECT el.entity_id, el.english_name, el.entity_type, COUNT(*) as co_occurrences
            FROM verse_entities ve
            JOIN entity_links el ON el.entity_id = ve.entity_id
            WHERE ve.verse_id IN ({",".join("?" for _ in verse_ids[:50])})
            AND ve.entity_id != ?
            AND ve.confidence >= ?
            GROUP BY el.entity_id
            ORDER BY co_occurrences DESC
            LIMIT 20
        """,
            verse_ids[:50] + [entity, min_confidence],
        ).fetchall()
        related = [dict(r) for r in related_rows]

    return {
        "entity": entity_info,
        "total_verses": len(verses),
        "verses": verses,
        "entity_connections": {
            "total": len(entity_connections),
            "connections": entity_connections[:50],
        },
        "related_entities": {
            "total": len(related),
            "entities": related,
        },
    }
