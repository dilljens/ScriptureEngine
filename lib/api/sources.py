"""Source provenance tool — track where connections come from."""

import json


def _safe_json_extract(metadata, key):
    """Safely extract a key from a JSON metadata string."""
    if not metadata or not metadata.startswith('{'):
        return None
    try:
        obj = json.loads(metadata)
        return obj.get(key)
    except (json.JSONDecodeError, TypeError):
        return None


def get_sources_for_verse(conn, verse):
    """Get all source breakdown for a verse's connections.
    
    Args:
        verse: Verse ID (gen.1.1)
    
    Returns: dict with verse and sources breakdown
    """
    rows = conn.execute("""
        SELECT discovered_by, COUNT(*) as c
        FROM connections WHERE source_verse = ?
        GROUP BY discovered_by
        ORDER BY c DESC
    """, (verse,)).fetchall()
    
    methods = [dict(r) for r in rows] if rows else []
    
    meta_rows = conn.execute("""
        SELECT discovered_by, metadata FROM connections 
        WHERE source_verse = ? AND metadata IS NOT NULL AND metadata != '{}'
        LIMIT 100
    """, (verse,)).fetchall()
    
    scholars = {}
    for r in meta_rows:
        scholar_name = _safe_json_extract(r['metadata'], 'scholar')
        tag = _safe_json_extract(r['metadata'], 'tag') or scholar_name or r['discovered_by']
        source = _safe_json_extract(r['metadata'], 'source') or ''
        if tag not in scholars:
            scholars[tag] = {"tag": tag, "count": 0, "name": scholar_name or tag, "works": []}
        scholars[tag]["count"] += 1
        if source and source not in scholars[tag]["works"]:
            scholars[tag]["works"].append(source)
    
    return {
        "verse": verse,
        "total_connections": sum(r["c"] for r in rows) if rows else 0,
        "discovery_methods": methods,
        "scholars": list(scholars.values()),
    }


def get_sources_by_scholar(conn, scholar_tag=None, scholar_name=None):
    """Get all connections from a specific scholar.
    
    Args:
        scholar_tag: Tag to filter by (e.g., 'morales_ascent')
        scholar_name: Scholar name to filter by
    
    Returns: dict with scholar info and connections
    """
    # Fetch all rows with valid JSON metadata and extract in Python
    key = 'scholar' if scholar_name else 'tag'
    value = scholar_name or scholar_tag
    
    all_rows = conn.execute("""
        SELECT source_verse, target_verse, type, layer, discovered_by, metadata
        FROM connections
        WHERE metadata LIKE '{%'
        LIMIT 10000
    """).fetchall()
    
    matched = []
    seen_meta = None
    for r in all_rows:
        val = _safe_json_extract(r['metadata'], key)
        if val and val == value:
            matched.append(r)
            if seen_meta is None:
                seen_meta = r['metadata']
    
    if not matched:
        return {"total": 0, "error": f"No connections found for {key}={value}"}
    
    meta_info = _safe_json_extract(seen_meta, 'scholar') or ''
    source_info = _safe_json_extract(seen_meta, 'source') or ''
    
    types = {}
    for r in matched:
        t = r["type"]
        types[t] = types.get(t, 0) + 1
    
    connections = [
        {
            "source": r["source_verse"],
            "target": r["target_verse"],
            "type": r["type"],
            "layer": r["layer"],
            "note": (_safe_json_extract(r['metadata'], 'note') or '')[:100],
        }
        for r in matched[:50]
    ]
    
    result = {"total": len(matched), "type_breakdown": types, "connections": connections}
    if meta_info:
        result["scholar"] = meta_info
    if source_info:
        result["source"] = source_info
    return result


def list_scholars(conn):
    """List all distinct scholars found in connection metadata."""
    rows = conn.execute("""
        SELECT metadata FROM connections 
        WHERE metadata LIKE '{%'
    """).fetchall()
    
    scholars_map = {}
    tags_map = {}
    
    for r in rows:
        try:
            obj = json.loads(r['metadata'])
        except (json.JSONDecodeError, TypeError):
            continue
        
        scholar = obj.get('scholar', '')
        tag = obj.get('tag', '')
        
        if scholar:
            scholars_map[scholar] = scholars_map.get(scholar, 0) + 1
        if tag:
            tags_map[tag] = tags_map.get(tag, 0) + 1
    
    return {
        "scholars": [{"name": k, "connections": v} for k, v in sorted(scholars_map.items())],
        "tags": [{"tag": k, "connections": v} for k, v in sorted(tags_map.items())],
    }
