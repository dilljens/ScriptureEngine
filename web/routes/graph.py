"""Graph exploration API — interactive knowledge graph for scripture connections.

Endpoints:
  GET /api/v1/graph/explore?verse=X&depth=N&layers=A,B&min_quality=N&limit=N
  GET /api/v1/graph/centrality?book=X&layer=Y&limit=N
  GET /api/v1/graph/search?q=X&limit=N
  GET /api/v1/connections/{verse_a}/{verse_b}/explain
"""
from collections import deque
import contextlib
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"
MEM_DB_PATH = BASE_DIR / "data" / "memorize.db"


def get_conn():
    return sqlite3.connect(str(DB_PATH))


def get_mem_conn():
    if MEM_DB_PATH.exists():
        return sqlite3.connect(str(MEM_DB_PATH))
    return None


# ── Layer display configuration ──

LAYER_CONFIG = {
    "linguistic":    {"color": "#3b82f6", "label": "Linguistic",    "order": 1},
    "intertextual":  {"color": "#10b981", "label": "Intertextual",  "order": 2},
    "numerical":     {"color": "#f59e0b", "label": "Numerical",     "order": 3},
    "structural":    {"color": "#8b5cf6", "label": "Structural",    "order": 4},
    "interpretive":  {"color": "#ec4899", "label": "Interpretive",  "order": 5},
    "symbolic":      {"color": "#06b6d4", "label": "Symbolic",      "order": 6},
    "textual":       {"color": "#84cc16", "label": "Textual",       "order": 7},
    "geographic":    {"color": "#f97316", "label": "Geographic",    "order": 8},
    "chronological": {"color": "#a855f7", "label": "Chronological", "order": 9},
    "frequency":     {"color": "#64748b", "label": "Frequency",     "order": 10},
    "sod":           {"color": "#dc2626", "label": "Hidden (Sod)",  "order": 11},
}

LAYER_NAMES = list(LAYER_CONFIG.keys())
LAYER_COLORS = {k: v["color"] for k, v in LAYER_CONFIG.items()}

CONNECTION_TYPE_LABELS = {
    "topical_guide": "Topical Guide",
    "topical_see_also": "TG See Also",
    "topical_shared_verses": "TG Shared Verses",
    "bible_dictionary": "Bible Dictionary",
    "bible_dictionary_tg": "BD → TG",
    "direct_quotation": "Direct Quotation",
    "same_lemma": "Same Lemma",
    "same_root": "Same Root",
    "allusion": "Allusion",
    "parallel_synonymous": "Synonymous Parallel",
    "parallel_antithetic": "Antithetic Parallel",
    "chiastic": "Chiastic",
    "gematria": "Gematria",
    "type_antitype": "Type/Antitype",
    "prophetic_fulfillment": "Prophecy Fulfilled",
    "hebrew_grammar": "Hebrew Grammar",
}


@router.get("/api/v1/graph/explore")
def graph_explore(
    verse: str = Query("", description="Center verse ID (gen.1.1)"),
    depth: int = Query(1, description="Connection depth (1-3)", ge=1, le=3),
    layers: str = Query("", description="Comma-separated layer filter"),
    min_quality: int = Query(0, description="Minimum star quality (0-5)", ge=0, le=5),
    limit: int = Query(100, description="Max nodes to return", ge=1, le=500),
):
    """Explore the connection graph from a starting verse or TG topic.

    Returns nodes and edges for force-directed graph rendering.
    Supports `tg:topic_slug` and `bd:entry_slug` as verse parameter.
    """
    if not verse:
        raise HTTPException(400, "verse parameter required")

    verse.startswith("tg:")
    verse.startswith("bd:")

    conn = get_conn()
    cursor = conn.cursor()

    # Parse layer filter
    layer_filter = [layer.strip() for layer in layers.split(",") if layer.strip()] if layers else None

    # ── BFS through connections ──
    visited_nodes = set()
    all_nodes = []
    all_edges = []
    queue = deque([(verse, 0)])  # (node_id, current_depth)

    # Track node metadata (type-specific enrichment)
    node_meta = {}

    while queue and len(all_nodes) < limit:
        current, current_depth = queue.popleft()

        if current in visited_nodes:
            continue
        if current_depth > depth:
            continue

        visited_nodes.add(current)

        # Determine node type and fetch metadata
        is_tg = current.startswith("tg:")
        is_bd_entry = current.startswith("bd:")

        if is_tg:
            # TG topic node
            slug = current[3:]
            row = cursor.execute(
                "SELECT name, description, verse_count, importance, slug FROM topical_guide WHERE slug=?",
                (slug,)
            ).fetchone()
            if row:
                node = {
                    "id": current,
                    "title": row[0],
                    "type": "topic",
                    "subtype": "tg",
                    "description": (row[1] or "")[:200],
                    "verse_count": row[2],
                    "importance": row[3],
                    "size": max(8, min(30, row[2] * 0.5 + 10)),
                    "depth": current_depth,
                }
                all_nodes.append(node)
                node_meta[current] = node

            if current_depth < depth:
                # Get all verses connected to this topic
                edges = cursor.execute("""
                    SELECT source_verse, target_verse, type, layer, strength, confidence, quality_level
                    FROM connections
                    WHERE (source_verse=? OR target_verse=?) AND deprecated=0
                    LIMIT ?
                """, (current, current, limit)).fetchall()
                for src, tgt, etype, layer, strength, confidence, quality in edges:
                    other = src if src != current else tgt
                    if other not in visited_nodes and other not in [n["id"] for n in all_nodes]:
                        queue.append((other, current_depth + 1))
                    if layer_filter and layer not in layer_filter:
                        continue
                    qual = {"low": 1, "suggested": 2, "probable": 3, "strong": 4, "certain": 5}.get(quality or "", 0)
                    if qual < min_quality:
                        continue
                    all_edges.append({
                        "source": src, "target": tgt, "type": etype,
                        "layer": layer, "strength": strength,
                        "confidence": confidence, "quality": quality,
                    })

                # Get TG cross-references
                edges2 = cursor.execute("""
                    SELECT source_verse, target_verse, type, layer, strength, confidence
                    FROM connections
                    WHERE (source_verse=? OR target_verse=?)
                    AND type IN ('topical_see_also', 'topical_shared_verses')
                    AND deprecated=0
                    LIMIT 30
                """, (current, current)).fetchall()
                for src, tgt, etype, layer, strength, confidence in edges2:
                    other = src if src != current else tgt
                    if other not in visited_nodes and other not in [n["id"] for n in all_nodes]:
                        queue.append((other, current_depth + 1))
                    all_edges.append({
                        "source": src, "target": tgt, "type": etype,
                        "layer": layer, "strength": strength,
                        "confidence": confidence, "quality": "strong",
                    })

        elif is_bd_entry:
            # Bible Dictionary entry node
            slug = current[3:]
            row = cursor.execute(
                "SELECT name, entry_text, slug FROM bible_dictionary WHERE slug=?",
                (slug,)
            ).fetchone()
            if row:
                node = {
                    "id": current,
                    "title": row[0],
                    "type": "bd_entry",
                    "subtype": "bd",
                    "description": (row[1] or "")[:200],
                    "size": 18,
                    "depth": current_depth,
                }
                all_nodes.append(node)
                node_meta[current] = node

            if current_depth < depth:
                edges = cursor.execute("""
                    SELECT source_verse, target_verse, type, layer, strength, confidence
                    FROM connections
                    WHERE (source_verse=? OR target_verse=?) AND deprecated=0
                    LIMIT ?
                """, (current, current, limit)).fetchall()
                for src, tgt, etype, layer, strength, confidence in edges:
                    other = src if src != current else tgt
                    if other not in visited_nodes and other not in [n["id"] for n in all_nodes]:
                        queue.append((other, current_depth + 1))
                    if layer_filter and layer not in layer_filter:
                        continue
                    all_edges.append({
                        "source": src, "target": tgt, "type": etype,
                        "layer": layer, "strength": strength,
                        "confidence": confidence, "quality": "strong",
                    })

        else:
            # Regular verse node
            row = cursor.execute(
                "SELECT id, book_id, chapter, verse FROM verses WHERE id=?",
                (current,)
            ).fetchone()
            if row:
                title = f"{row[1].upper()}.{row[2]}.{row[3]}" if row[1] else current
                # Get connection count for sizing
                conn_count = cursor.execute(
                    "SELECT COUNT(*) FROM connections WHERE (source_verse=? OR target_verse=?) AND deprecated=0",
                    (current, current)
                ).fetchone()[0]

                node = {
                    "id": current,
                    "title": title,
                    "type": "verse",
                    "subtype": "",
                    "book": row[1],
                    "chapter": row[2],
                    "verse": row[3],
                    "connection_count": conn_count,
                    "size": max(5, min(25, conn_count * 0.3 + 5)),
                    "depth": current_depth,
                }
                all_nodes.append(node)
                node_meta[current] = node
            else:
                # Unknown node — still add as placeholder
                all_nodes.append({
                    "id": current, "title": current, "type": "unknown",
                    "size": 5, "depth": current_depth,
                })

            if current_depth < depth:
                edges = cursor.execute("""
                    SELECT source_verse, target_verse, type, layer, strength, confidence, quality_level, metadata, tradition, hermeneutic
                    FROM connections
                    WHERE (source_verse=? OR target_verse=?) AND deprecated=0
                    ORDER BY strength DESC, confidence DESC
                    LIMIT ?
                """, (current, current, limit * 2)).fetchall()

                for src, tgt, etype, layer, strength, confidence, quality, _meta_json, tradition, hermeneutic in edges:
                    other = src if src != current else tgt
                    if layer_filter and layer not in layer_filter:
                        continue
                    qual = {"low": 1, "suggested": 2, "probable": 3, "strong": 4, "certain": 5}.get(quality or "", 0)
                    if qual < min_quality:
                        continue

                    # If the other node is a TG topic or BD entry, handle it
                    if other.startswith("tg:") or other.startswith("bd:"):
                        if other not in visited_nodes and other not in [n["id"] for n in all_nodes]:
                            queue.append((other, current_depth + 1))
                    elif other not in visited_nodes and other not in [n["id"] for n in all_nodes]:
                        queue.append((other, current_depth + 1))

                    all_edges.append({
                        "source": src, "target": tgt, "type": etype,
                        "layer": layer, "strength": strength,
                        "confidence": confidence, "quality": quality or "suggested",
                        "tradition": tradition or "none",
                        "hermeneutic": hermeneutic or "linguistic",
                    })

    conn.close()

    # Deduplicate nodes
    seen_ids = set()
    unique_nodes = []
    for n in all_nodes:
        if n["id"] not in seen_ids:
            seen_ids.add(n["id"])
            unique_nodes.append(n)

    # Deduplicate edges
    edge_set = set()
    unique_edges = []
    for e in all_edges:
        key = (e["source"], e["target"], e["type"])
        if key not in edge_set:
            edge_set.add(key)
            unique_edges.append(e)

    # Get layer distribution
    layer_counts = Counter(e["layer"] for e in unique_edges)

    return {"ok": True, "data": {
        "root": verse,
        "nodes": unique_nodes[:limit],
        "edges": unique_edges[:limit * 3],
        "node_count": len(unique_nodes),
        "edge_count": len(unique_edges),
        "layers": dict(layer_counts),
        "layers_config": LAYER_CONFIG,
        "node_types": {
            "verse": {"label": "Verse", "color": "#6366f1"},
            "topic": {"label": "TG Topic", "color": "#ef4444"},
            "bd_entry": {"label": "Bible Dictionary", "color": "#3b82f6"},
        },
    }}


@router.get("/api/v1/graph/search")
def graph_search(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search verses, TG topics, and BD entries. Returns autocomplete suggestions."""
    if not q:
        return {"ok": True, "data": {"results": []}}

    conn = get_conn()
    cursor = conn.cursor()
    results = []

    # Search TG topics
    tg_rows = cursor.execute(
        "SELECT slug, name, verse_count FROM topical_guide WHERE name LIKE ? ORDER BY verse_count DESC LIMIT ?",
        (f"%{q}%", limit)
    ).fetchall()
    for r in tg_rows:
        results.append({
            "id": f"tg:{r[0]}", "title": r[1], "type": "topic",
            "subtitle": f"Topical Guide · {r[2]} verses",
        })

    # Search BD entries
    bd_rows = cursor.execute(
        "SELECT slug, name FROM bible_dictionary WHERE name LIKE ? OR slug LIKE ? LIMIT ?",
        (f"%{q}%", f"%{q}%", limit // 2)
    ).fetchall()
    for r in bd_rows:
        results.append({
            "id": f"bd:{r[0]}", "title": r[1], "type": "bd_entry",
            "subtitle": "Bible Dictionary",
        })

    # Search verses
    if len(results) < limit:
        verse_rows = cursor.execute(
            "SELECT id, book_id, chapter, verse FROM verses WHERE id LIKE ? LIMIT ?",
            (f"%{q}%", limit // 2)
        ).fetchall()
        for r in verse_rows:
            title = f"{r[1].upper()}.{r[2]}.{r[3]}" if r[1] else r[0]
            results.append({
                "id": r[0], "title": title, "type": "verse",
                "subtitle": f"{r[1].upper()} {r[2]}:{r[3]}" if r[1] else "",
            })

    conn.close()
    return {"ok": True, "data": {"results": results[:limit]}}


@router.get("/api/v1/graph/centrality")
def graph_centrality(
    book: str = Query("", description="Book filter"),
    layer: str = Query("", description="Layer filter"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get the most connected verses (hub verses) ranked by degree centrality."""
    conn = get_conn()
    cursor = conn.cursor()

    filter_clauses = ["1=1"]
    filter_params = []

    if book:
        filter_clauses.append("(source_verse LIKE ? OR target_verse LIKE ?)")
        filter_params.extend([f"{book}.%", f"{book}.%"])
    if layer:
        filter_clauses.append("layer=?")
        filter_params.append(layer)

    filter_sql = " AND ".join(filter_clauses)

    # Count connections per verse using single-pass aggregation (not correlated subqueries)
    # filter_sql appears in both src and tgt subqueries, so params need to be duplicated
    params_for_query = filter_params * 2 + [limit]
    rows = cursor.execute(f"""
        SELECT * FROM (
            SELECT v.id as verse_id, v.book_id, v.chapter, v.verse,
                   COALESCE(src.cnt, 0) + COALESCE(tgt.cnt, 0) as total_connections
            FROM verses v
            LEFT JOIN (
                SELECT source_verse, COUNT(*) as cnt
                FROM connections
                WHERE deprecated=0 AND ({filter_sql})
                GROUP BY source_verse
            ) src ON src.source_verse = v.id
            LEFT JOIN (
                SELECT target_verse, COUNT(*) as cnt
                FROM connections
                WHERE deprecated=0 AND ({filter_sql})
                GROUP BY target_verse
            ) tgt ON tgt.target_verse = v.id
        )
        WHERE total_connections > 0
        ORDER BY total_connections DESC
        LIMIT ?
    """, params_for_query).fetchall()

    conn.close()

    results = []
    for r in rows:
        title = f"{r[1].upper()}.{r[2]}.{r[3]}" if r[1] else r[0]
        results.append({
            "verse_id": r[0],
            "title": title,
            "centrality": r[4],
            "book": r[1],
            "chapter": r[2],
            "verse": r[3],
        })

    return {"ok": True, "data": {
        "results": results,
        "total": len(results),
        "filter": {"book": book, "layer": layer},
    }}


@router.get("/api/v1/connections/{verse_a}/{verse_b}/explain")
def explain_connection(
    verse_a: str,
    verse_b: str,
):
    """Get a human-readable explanation of why two verses or topics are connected."""
    # Order the verse IDs deterministically
    a, b = sorted([verse_a, verse_b])

    conn = get_conn()
    cursor = conn.cursor()

    # Find the connection(s) between these two nodes
    rows = cursor.execute("""
        SELECT type, layer, strength, confidence, subtype, metadata, quality_level
        FROM connections
        WHERE ((source_verse=? AND target_verse=?) OR (source_verse=? AND target_verse=?))
        AND deprecated=0
        ORDER BY strength DESC, confidence DESC
        LIMIT 10
    """, (a, b, b, a)).fetchall()

    conn.close()

    if not rows:
        return {"ok": True, "data": {
            "explanation": None,
            "note": "No direct connection found between these items.",
        }}

    explanations = []
    for r in rows:
        etype, layer, strength, confidence, subtype, meta_json, quality = r
        meta = {}
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            meta = json.loads(meta_json) if meta_json else {}

        # Generate explanation from templates
        exp = _generate_explanation(a, b, etype, layer, strength, meta)
        explanations.append({
            "type": etype,
            "layer": layer,
            "strength": strength,
            "confidence": confidence,
            "explanation": exp,
        })

    return {"ok": True, "data": {
        "connections": explanations,
        "count": len(explanations),
    }}


def _generate_explanation(a, b, etype, layer, strength, meta):
    """Generate a human-readable explanation for a connection."""
    # Clean verse IDs for display
    def fmt_id(vid):
        if vid.startswith("tg:"):
            name = vid[3:].replace("-", " ").title()
            return f"**{name}** (TG)"
        if vid.startswith("bd:"):
            name = vid[3:].replace("-", " ").title()
            return f"**{name}** (BD)"
        return f"**{vid}**"

    a_fmt = fmt_id(a)
    b_fmt = fmt_id(b)

    # TG connections
    if etype == "topical_guide":
        topic_name = meta.get("topic_name", b[3:].replace("-", " ").title() if b.startswith("tg:") else "")
        return f"{a_fmt} is categorized under **{topic_name}** in the LDS Topical Guide."

    if etype == "topical_see_also":
        return f"In the Topical Guide, {a_fmt} lists {b_fmt} as a related topic."

    if etype == "topical_shared_verses":
        shared = meta.get("shared_verses", 0)
        return f"{a_fmt} and {b_fmt} are thematically linked — they appear together in {shared} verses."

    if etype == "bible_dictionary":
        entry_name = meta.get("entry_name", "")
        return f"The Bible Dictionary entry for **{entry_name}** references {b_fmt}."

    if etype == "bible_dictionary_tg":
        entry_name = meta.get("entry_name", "")
        return f"The Bible Dictionary entry for **{entry_name}** relates to {b_fmt}."

    # Standard connection types
    if etype == "direct_quotation":
        return f"{a_fmt} directly quotes {b_fmt} — the wording is nearly identical."
    if etype == "same_lemma":
        lemma = meta.get("lemma", "")
        gloss = meta.get("gloss", "")
        word_info = f" '{lemma}' ({gloss})" if lemma else ""
        return f"{a_fmt} and {b_fmt} share the Hebrew word{word_info}, linking the passages thematically."
    if etype == "same_root":
        root = meta.get("root", "")
        return f"{a_fmt} and {b_fmt} share the Hebrew root **{root}**, connecting their core meaning."
    if etype == "allusion":
        theme = meta.get("theme", "")
        return f"{a_fmt} alludes to {b_fmt} through shared imagery{f' of **{theme}**' if theme else ''}."
    if etype == "parallel_synonymous":
        return f"{a_fmt} and {b_fmt} express the same idea in parallel form."
    if etype == "chiastic":
        return f"{a_fmt} and {b_fmt} form a chiastic mirror structure."
    if etype == "gematria":
        val_a = meta.get("value_a", "")
        val_b = meta.get("value_b", "")
        return f"The gematria values of key words in {a_fmt} ({val_a}) and {b_fmt} ({val_b}) create a numerical link."
    if etype == "type_antitype":
        return f"{a_fmt} prefigures {b_fmt} as a type pointing forward to its fulfillment."
    if etype == "prophetic_fulfillment":
        return f"{a_fmt} prophesied of {b_fmt}, which records its fulfillment."
    if etype == "hebrew_grammar":
        concept = meta.get("concept", "")
        return f"**{concept}**: {a_fmt} uses this Hebrew grammar concept, which you studied in your lessons."

    # Fallback
    type_label = CONNECTION_TYPE_LABELS.get(etype, etype.replace("_", " ").title())
    return f"{a_fmt} and {b_fmt} are connected via **{type_label}** ({layer} layer, strength {strength})."


@router.get("/api/v1/topical-guide")
def list_topical_guide(
    search: str = Query("", description="Search topics"),
    category: str = Query("", description="Category filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List Topical Guide topics with metadata."""
    conn = get_conn()
    cursor = conn.cursor()

    where = "1=1"
    params = []
    if search:
        where += " AND name LIKE ?"
        params.append(f"%{search}%")

    total = cursor.execute(f"SELECT COUNT(*) FROM topical_guide WHERE {where}", params).fetchone()[0]

    rows = cursor.execute(f"""
        SELECT slug, name, description, verse_count, importance, related_topic_ids
        FROM topical_guide WHERE {where}
        ORDER BY verse_count DESC
        LIMIT ? OFFSET ?
    """, params + [limit, offset]).fetchall()

    conn.close()

    results = []
    for r in rows:
        try:
            related = json.loads(r[5]) if r[5] else []
        except (json.JSONDecodeError, ValueError):
            related = []
        results.append({
            "id": f"tg:{r[0]}",
            "slug": r[0],
            "name": r[1],
            "description": (r[2] or "")[:300],
            "verse_count": r[3],
            "importance": r[4],
            "related_topics": related[:10],
        })

    return {"ok": True, "data": {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset,
    }}


@router.get("/api/v1/topical-guide/{slug}")
def get_topical_topic(slug: str):
    """Get a single Topical Guide topic with its full details and connected verses."""
    conn = get_conn()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT slug, name, description, summary, verse_count, importance, related_topic_ids, related_bd_entries FROM topical_guide WHERE slug=?",
        (slug,)
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(404, f"Topic not found: {slug}")

    # Parse related topics
    try:
        related_topics = json.loads(row[6]) if row[6] else []
    except (json.JSONDecodeError, ValueError):
        related_topics = []

    try:
        related_bd = json.loads(row[7]) if row[7] else []
    except (json.JSONDecodeError, ValueError):
        related_bd = []

    # Get connected verses (first 20)
    verses = cursor.execute("""
        SELECT verse_id, snippet FROM tg_verse_references
        WHERE topic_id=?
        ORDER BY rowid
        LIMIT 20
    """, (slug,)).fetchall()

    # Also get from connections table for count
    conn_count = cursor.execute(
        "SELECT COUNT(*) FROM connections WHERE (source_verse=? OR target_verse=?) AND type='topical_guide'",
        (f"tg:{slug}", f"tg:{slug}")
    ).fetchone()[0]

    conn.close()

    return {"ok": True, "data": {
        "id": f"tg:{slug}",
        "slug": row[0],
        "name": row[1],
        "description": row[2] or "",
        "summary": row[3] or "",
        "verse_count": row[4],
        "connections_in_graph": conn_count,
        "importance": row[5],
        "related_topics": related_topics,
        "related_bd_entries": related_bd,
        "sample_verses": [{"verse": v[0], "snippet": v[1]} for v in verses],
    }}


@router.get("/api/v1/bible-dictionary/{slug}")
def get_bd_entry(slug: str):
    """Get a Bible Dictionary entry."""
    conn = get_conn()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT slug, name, entry_text, summary, related_verses, related_topics FROM bible_dictionary WHERE slug=?",
        (slug,)
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(404, f"BD entry not found: {slug}")

    try:
        verses = json.loads(row[4]) if row[4] else []
    except (json.JSONDecodeError, ValueError):
        verses = []
    try:
        topics = json.loads(row[5]) if row[5] else []
    except (json.JSONDecodeError, ValueError):
        topics = []

    conn.close()

    return {"ok": True, "data": {
        "id": f"bd:{slug}",
        "slug": row[0],
        "name": row[1],
        "entry_text": row[2],
        "summary": row[3],
        "related_verses": verses[:30],
        "related_topics": topics[:10],
    }}


# ── Hub Notes API ──

@router.get("/api/v1/hub-notes")
def list_hub_notes(user_id: str = "default"):
    """List all hub notes with user progress summary."""
    conn = get_conn()
    cursor = conn.cursor()

    notes = cursor.execute("""
        SELECT n.id, n.title, n.description, n.theme, n.icon, n.seed_verse,
               n.tg_topic_ids,
               (SELECT COUNT(*) FROM hub_note_steps WHERE hub_id=n.id) as total_steps
        FROM hub_notes n
        ORDER BY n.id
    """).fetchall()

    results = []
    for r in notes:
        completed = cursor.execute(
            "SELECT COUNT(*) FROM hub_note_progress WHERE user_id=? AND hub_id=?",
            (user_id, r[0])
        ).fetchone()[0]

        tg_topics = cursor.execute("""
            SELECT t.slug, t.name, h.relevance_weight
            FROM hub_topic_links h
            JOIN topical_guide t ON t.slug=h.topic_id
            WHERE h.hub_id=?
            ORDER BY h.relevance_weight DESC
        """, (r[0],)).fetchall()

        try:
            tg_ids = json.loads(r[6]) if r[6] else []
        except (json.JSONDecodeError, ValueError):
            tg_ids = []

        results.append({
            "id": r[0], "title": r[1], "description": r[2],
            "theme": r[3], "icon": r[4], "seed_verse": r[5],
            "total_steps": r[7], "completed_steps": completed,
            "progress_pct": round(completed / max(r[7], 1) * 100, 1) if r[7] > 0 else 0,
            "tg_topic_ids": tg_ids,
            "tg_topics": [{"slug": t[0], "name": t[1], "weight": t[2]} for t in tg_topics],
        })

    conn.close()
    return {"ok": True, "data": {"notes": results, "total": len(results)}}


@router.get("/api/v1/hub-notes/{hub_id}")
def get_hub_note(hub_id: str, user_id: str = "default"):
    """Get a full hub note with all steps, verse text, and TG topics."""
    conn = get_conn()
    cursor = conn.cursor()

    note = cursor.execute(
        "SELECT id, title, description, theme, icon, seed_verse, tg_topic_ids, version FROM hub_notes WHERE id=?",
        (hub_id,)
    ).fetchone()

    if not note:
        conn.close()
        raise HTTPException(404, f"Hub note not found: {hub_id}")

    steps = cursor.execute("""
        SELECT id, step_number, verse_id, title, explanation, connection_type, pa_r_de_s_level, tg_topic_ids
        FROM hub_note_steps WHERE hub_id=? ORDER BY step_number
    """, (hub_id,)).fetchall()

    step_data = []
    for s in steps:
        vt = cursor.execute(
            "SELECT text_english FROM verses WHERE id=?", (s[2],)
        ).fetchone()
        verse_text = vt[0] if vt else ""

        prog = cursor.execute(
            "SELECT completed_at FROM hub_note_progress WHERE user_id=? AND hub_id=? AND step_number=?",
            (user_id, hub_id, s[1])
        ).fetchone()

        try:
            step_tg = json.loads(s[7]) if s[7] else []
        except (json.JSONDecodeError, ValueError):
            step_tg = []

        step_data.append({
            "step_number": s[1], "verse_id": s[2], "title": s[3],
            "explanation": s[4], "verse_text": verse_text[:500] if verse_text else "",
            "connection_type": s[5] or "", "pa_r_de_s_level": s[6] or "pshat",
            "tg_topic_ids": step_tg, "completed": prog is not None,
            "completed_at": prog[0] if prog else None,
        })

    tg_topics = cursor.execute("""
        SELECT t.slug, t.name, t.verse_count, h.relevance_weight
        FROM hub_topic_links h JOIN topical_guide t ON t.slug=h.topic_id
        WHERE h.hub_id=? ORDER BY h.relevance_weight DESC
    """, (hub_id,)).fetchall()

    try:
        tg_ids = json.loads(note[6]) if note[6] else []
    except (json.JSONDecodeError, ValueError):
        tg_ids = []

    conn.close()

    return {"ok": True, "data": {
        "id": note[0], "title": note[1], "description": note[2],
        "theme": note[3], "icon": note[4], "seed_verse": note[5],
        "tg_topic_ids": tg_ids,
        "tg_topics": [{"slug": t[0], "name": t[1], "verse_count": t[2], "weight": t[3]} for t in tg_topics],
        "total_steps": len(step_data),
        "completed_steps": sum(1 for s in step_data if s["completed"]),
        "progress_pct": round(sum(1 for s in step_data if s["completed"]) / max(len(step_data), 1) * 100, 1),
        "steps": step_data,
    }}


@router.post("/api/v1/hub-notes/{hub_id}/step/{step_number}/complete")
def complete_hub_step(hub_id: str, step_number: int, user_id: str = "default"):
    """Mark a hub note step as complete."""
    conn = get_conn()
    cursor = conn.cursor()

    step = cursor.execute(
        "SELECT verse_id, title FROM hub_note_steps WHERE hub_id=? AND step_number=?",
        (hub_id, step_number)
    ).fetchone()

    if not step:
        conn.close()
        raise HTTPException(404, f"Step {step_number} not found in hub note {hub_id}")

    existing = cursor.execute(
        "SELECT completed_at FROM hub_note_progress WHERE user_id=? AND hub_id=? AND step_number=?",
        (user_id, hub_id, step_number)
    ).fetchone()

    if existing:
        conn.close()
        return {"ok": True, "data": {"message": "Already completed", "step_number": step_number, "verse_id": step[0]}}

    cursor.execute("""
        INSERT OR IGNORE INTO hub_note_progress (user_id, hub_id, step_number, completed_at)
        VALUES (?, ?, ?, datetime('now'))
    """, (user_id, hub_id, step_number))

    conn.commit()
    conn.close()

    return {"ok": True, "data": {
        "message": f"Completed step {step_number}: {step[1]}",
        "step_number": step_number, "verse_id": step[0], "xp_awarded": 25, "hub_id": hub_id,
    }}


@router.get("/api/v1/hub-notes/{hub_id}/path")
def get_hub_path(hub_id: str):
    """Return the ordered graph path traversal for a hub note."""
    conn = get_conn()
    cursor = conn.cursor()

    steps = cursor.execute("""
        SELECT step_number, verse_id, connection_type
        FROM hub_note_steps WHERE hub_id=? ORDER BY step_number
    """, (hub_id,)).fetchall()

    conn.close()

    path = [{"step": s[0], "verse": s[1], "connection_type": s[2] if s[2] else ""} for s in steps]

    return {"ok": True, "data": {"hub_id": hub_id, "path_steps": path, "total": len(path)}}


# ── LLM Grading Endpoint ──


from pydantic import BaseModel


class GradingRequest(BaseModel):
    question: str
    user_answer: str
    rubric: str | None = None
    tier: str | None = "text"
    passage_context: str | None = None
    user_id: str | None = None  # If provided, inject user's progress context


@router.post("/api/v1/assess/grade")
def grade_answer(body: GradingRequest):
    """Grade an open-ended answer using the LLM with a transparent rubric.

    Evaluates the QUALITY OF REASONING, not whether the answer is "right" or "wrong."
    Returns scores for: engagement with text, internal consistency,
    awareness of alternatives, context.
    If user_id is provided, injects their learning progress for personalized feedback.
    """
    # Build a grading prompt
    tier = body.tier or "text"
    rubric = body.rubric or ""

    if not rubric:
        if tier == "text":
            rubric = "Does the answer accurately reference specific words or phrases from the passage?"
        elif tier == "analysis":
            rubric = "Does the answer identify patterns or relationships? Is the reasoning internally consistent?"
        elif tier == "consistency":
            rubric = "Does the answer recognize how multiple passages contribute to a theme? Does it show how the witnesses reinforce each other?"
        elif tier == "interpretation":
            rubric = "Does the answer engage with the text? Does it acknowledge that other interpretations exist?"
        else:
            rubric = "Does the answer engage with the text and show reasoned thinking?"

    # Fetch user progress context if user_id provided
    user_context = ""
    _api_base = os.environ.get("SCRIPTURE_API_URL", "http://localhost:8002")
    if body.user_id:
        try:
            import requests as _req
            prog = _req.get(
                f"{_api_base}/api/v1/user/progress/{body.user_id}",
                timeout=5
            ).json()
            if prog.get("ok"):
                data = prog["data"]
                parts = []

                q = data.get("quiz", {})
                if q.get("total_answered", 0) > 0:
                    parts.append(f"- Answered {q['total_answered']} quiz questions")
                    for tier_info in q.get("by_tier", []):
                        pct = round(tier_info["mastered"] / max(tier_info["total"], 1) * 100)
                        parts.append(f"- {tier_info['tier']} tier: {pct}% mastered")
                    if q.get("weakest_areas"):
                        parts.append(f"- Struggling with: {q['weakest_areas'][0]['question_text'][:80]}...")

                m = data.get("memorize", {})
                if m.get("total", 0) > 0:
                    parts.append(f"- Memorizing {m['total']} verses ({m.get('mastered', 0)} mastered)")

                h = data.get("hebrew", {})
                if h.get("progress"):
                    p = h["progress"]
                    pc = round(p.get("mastered", 0) / max(h.get("total_nodes", 1), 1) * 100)
                    parts.append(f"- Hebrew: {pc}% complete ({p.get('mastered', 0)}/{h.get('total_nodes', 0)} nodes)")
                    if h.get("struggling"):
                        parts.append(f"- Struggling with Hebrew: {h['struggling'][0]['title']}")

                if parts:
                    user_context = "\nUser's learning context:\n" + "\n".join(parts) + "\n"
        except Exception:
            log.warning("silent_exception", exc_info=True)
            pass

    # Format the grading request for the LLM
    prompt = (
        f"You are grading a student's answer to a scripture question.\n\n"
        f"QUESTION: {body.question}\n\n"
        f"STUDENT ANSWER: {body.user_answer}\n\n"
        f"GRADING RUBRIC: {rubric}\n\n"
        f"{user_context}"
        f"Please evaluate the answer on the following 4 criteria (1-10 each):\n"
        f"1. TEXT ENGAGEMENT: Does the answer reference specific words, phrases, or details from the passage?\n"
        f"2. REASONING QUALITY: Is the argument internally consistent and logical?\n"
        f"3. DEPTH: Does the answer go beyond surface observation to insight?\n"
        f"4. CONTEXT: Does the answer show awareness of the passage's context or the bigger picture?\n\n"
        f"Respond in JSON format:\n"
        '{"scores": {"text_engagement": N, "reasoning": N, "depth": N, "context": N}, "total": N, "feedback": "...", "strengths": ["..."], "areas_for_growth": ["..."]}\n\n'
        f"Keep feedback constructive and specific. Do NOT say 'right' or 'wrong' — evaluate reasoning quality only."
    )

    # Call the existing chat endpoint
    result = {}
    try:
        import requests
        resp = requests.post(f"{_api_base}/api/v1/chat", json={
            "message": prompt,
            "model": "default",
        }, timeout=30)
        llm_response = resp.json()

        if llm_response.get("ok"):
            raw = llm_response.get("data", {}).get("response", "{}")
            # Try to parse JSON from the LLM response
            import re as _re
            json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                except (json.JSONDecodeError, ValueError):
                    result = {"raw": raw}
            else:
                result = {"raw": raw}
        else:
            result = {"error": "LLM unavailable"}
    except Exception as e:
        result = {"error": str(e)}

    # If LLM grading failed, provide useful default feedback
    if not result or result.get("error"):
        len(body.user_answer.split())
        result = {
            "scores": {"text_engagement": 5, "reasoning": 5, "depth": 3, "context": 3},
            "total": 16,
            "feedback": (
                "Your answer was received. To get the most out of open-ended questions, "
                "try to reference specific words or phrases from the passage, "
                "show how different parts connect, and explain your reasoning step by step."
            ),
            "strengths": ["You attempted to engage with the material"],
            "areas_for_growth": ["Reference specific words from the text", "Connect your observations to the broader context"],
        }

    return {"ok": True, "data": {
        "tier": tier,
        "rubric": rubric,
        "grading": result,
    }}


# ── Provenance Endpoint ──

@router.get("/api/v1/provenance/{verse_id}")
def get_verse_provenance(verse_id: str, limit: int = 50):
    """Get provenance info for connections from a verse — shows tradition, hermeneutic, and consensus.

    This lets users see WHICH traditions recognize each connection and whether
    it's a linguistic fact or an interpretive claim.
    """
    conn = get_conn()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT type, layer, tradition, hermeneutic, consensus_score, strength, quality_level,
               target_verse, tradition_note
        FROM connections
        WHERE (source_verse=? OR target_verse=?) AND deprecated=0
        ORDER BY tradition, layer, strength DESC
        LIMIT ?
    """, (verse_id, verse_id, limit)).fetchall()

    # Group by tradition
    by_tradition = {}
    for r in rows:
        trad = r[2] or "none"
        if trad not in by_tradition:
            by_tradition[trad] = {
                "tradition": trad,
                "count": 0,
                "connections": [],
            }
        by_tradition[trad]["connections"].append({
            "type": r[0], "layer": r[1], "hermeneutic": r[3] or "linguistic",
            "consensus_score": r[4] or 0.0, "strength": r[5] or 0.5,
            "quality": r[6] or "suggested", "target": r[7],
            "note": r[8] or "",
        })
        by_tradition[trad]["count"] += 1

    # Get tradition label info
    labels = cursor.execute("SELECT id, name, short_name, icon, color FROM tradition_labels").fetchall()
    tradition_labels = {r[0]: {"name": r[1], "short": r[2], "icon": r[3], "color": r[4]} for r in labels}

    conn.close()

    return {"ok": True, "data": {
        "verse_id": verse_id,
        "total_connections": sum(t["count"] for t in by_tradition.values()),
        "by_tradition": list(by_tradition.values()),
        "tradition_labels": tradition_labels,
    }}


@router.get("/api/v1/provenance/tradition-labels")
def get_tradition_labels():
    """Get all tradition labels with their icons and descriptions."""
    conn = get_conn()
    rows = conn.execute("SELECT id, name, short_name, description, icon, color FROM tradition_labels").fetchall()
    conn.close()
    return {"ok": True, "data": {
        "labels": [{"id": r[0], "name": r[1], "short": r[2], "description": r[3], "icon": r[4], "color": r[5]} for r in rows]
    }}


@router.post("/api/v1/assess/submit-open")
def submit_open_question(body: dict):
    """Submit an open-ended answer for LLM grading.

    Body: {
        "question": "What connections do you see between these passages?",
        "passages": ["gen.1.1", "john.1.1"],
        "user_answer": "Both passages begin with 'In the beginning'...",
        "tier": "analysis"
    }
    Returns scores + feedback, NOT a right/wrong judgment.
    """

    question = body.get("question", "")
    passages = body.get("passages", [])
    user_answer = body.get("user_answer", "")
    tier = body.get("tier", "text")

    # Format passage text for the grading context
    passage_texts = []
    for pid in passages:
        conn2 = get_conn()
        txt = conn2.execute("SELECT text_english FROM verses WHERE id=?", (pid,)).fetchone()
        conn2.close()
        if txt:
            passage_texts.append(f"{pid}: {txt[0][:200]}")

    passage_context = "\n".join(passage_texts) if passage_texts else ""

    grading_req = GradingRequest(
        question=question,
        user_answer=user_answer,
        tier=tier,
        passage_context=passage_context,
    )
    return grade_answer(grading_req)
