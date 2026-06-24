"""
Shared tool: guided study paths (AI-led exploration) + Export/Publish.

Supports:
  - Creating/editing studies (mutable, stored in study_guides)
  - Full graph path data in a canonical JSON format
  - Export as JSON, HTML, Markdown
  - Publish as immutable snapshot with shareable slug
  - Fork from an existing published study

The canonical JSON format for a study:
{
  "format": "scripture-study-v1",
  "title": "...",
  "description": "...",
  "author": { "name": "...", "id": "..." },
  "forked_from": "slug-or-null",
  "seed_verse": "gen.1.1",
  "theme": "...",
  "steps": [
    {
      "step": 1,
      "verse": "lev.17.11",
      "verse_text": "For the life of the flesh...",
      "book_title": "Leviticus",
      "title": "The Blood Principle",
      "explanation": "The foundational principle...",
      "connections": [
        {
          "from": "lev.17.11",
          "to": "heb.9.22",
          "layer": "intertextual",
          "type": "direct_quotation",
          "subtype": "",
          "strength": 0.85,
          "confidence": 0.9,
          "to_text": "And almost all things are by the law purged with blood...",
          "to_book": "Hebrews"
        }
      ]
    }
  ],
  "graph_summary": {
    "total_connections": 7,
    "unique_layers": ["intertextual", "linguistic", "structural"],
    "hub_verses": ["lev.17.11", "heb.9.22"]
  }
}
"""

import json, uuid, re, textwrap
from datetime import datetime


def _get_verse_text(conn, verse_id):
    """Get verse text + book title for a verse ID."""
    row = conn.execute(
        "SELECT v.text_english, b.title as book_title "
        "FROM verses v JOIN books b ON b.id = v.book_id "
        "WHERE v.id = ?", (verse_id,)
    ).fetchone()
    return (row["text_english"], row["book_title"]) if row else ("", "")


def _get_graph_path(conn, source, target):
    """Get the connection edge(s) between two verses, with full metadata."""
    rows = conn.execute("""
        SELECT c.*, v.text_english as to_text, b.title as to_book
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ? AND c.target_verse = ?
        ORDER BY c.strength DESC
    """, (source, target)).fetchall()
    return [dict(r) for r in rows]


def _get_connections_from(conn, verse_id, limit=5):
    """Get top connections FROM a verse (for xref fallback)."""
    rows = conn.execute("""
        SELECT c.type, c.subtype, c.strength, c.layer, c.confidence,
               c.target_verse, v.text_english as to_text, b.title as to_book
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
        ORDER BY c.strength DESC
        LIMIT ?
    """, (verse_id, limit)).fetchall()
    return [dict(r) for r in rows]


def _enrich_step(conn, step):
    """Add verse text, book title, and full graph path data to a step.
    
    Args:
        conn: DB connection
        step: dict with at least {verse, [connection_from, connection_type, ...]}
    
    Returns: enriched step dict
    """
    verse_text, book_title = _get_verse_text(conn, step["verse"])
    step["verse_text"] = verse_text
    step["book_title"] = book_title

    # Resolve connections: if connection_from is set, fetch the graph path
    connections = []
    cf = step.get("connection_from", "")
    if cf and cf != step["verse"]:
        edges = _get_graph_path(conn, cf, step["verse"])
        for e in edges:
            connections.append({
                "from": cf,
                "to": step["verse"],
                "layer": e["layer"],
                "type": e["type"],
                "subtype": e.get("subtype", ""),
                "strength": e["strength"],
                "confidence": e.get("confidence", 0.5),
                "to_text": e.get("to_text", "")[:200],
                "to_book": e.get("to_book", ""),
            })
    # If no connection_from, check for cross-references
    if not connections:
        xrefs = _get_connections_from(conn, step["verse"], limit=4)
        for x in xrefs:
            connections.append({
                "from": step["verse"],
                "to": x["target_verse"],
                "layer": x["layer"],
                "type": x["type"],
                "subtype": x.get("subtype", ""),
                "strength": x["strength"],
                "confidence": x.get("confidence", 0.5),
                "to_text": x.get("to_text", "")[:200],
                "to_book": x.get("to_book", ""),
            })

    step["connections"] = connections
    return step


def _steps_from_db(conn, guide_id):
    """Load steps from the legacy study_guide_steps table and enrich them."""
    raw = conn.execute("""
        SELECT s.*, v.text_english, b.title as book_title
        FROM study_guide_steps s
        JOIN verses v ON v.id = s.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE s.study_guide_id = ?
        ORDER BY s.step_number
    """, (guide_id,)).fetchall()

    steps = []
    for r in raw:
        rd = dict(r)
        s = {
            "step": rd["step_number"],
            "verse": rd["verse_id"],
            "verse_text": rd.get("text_english") or "",
            "book_title": rd.get("book_title") or "",
            "title": rd.get("title") or "",
            "explanation": rd.get("explanation") or "",
            "connection_from": rd.get("connection_from") or "",
            "connection_type": rd.get("connection_type") or "",
            "connection_layer": rd.get("connection_layer") or "",
            "choices": json.loads(rd["choices_json"]) if rd.get("choices_json") else [],
        }
        steps.append(_enrich_step(conn, s))
    return steps


# ─── JSON Schema ───


def _build_study_json(conn, guide_id, from_db=False):
    """Build the canonical JSON blob for a study guide.
    
    Args:
        guide_id: Study guide ID
        from_db: If True, always read from the steps table (ignore content_json cache).
                 Use this when the steps have been modified and content_json is stale.
    
    Normally pulls from the content_json column (preferred),
    otherwise builds from the legacy study_guide_steps table.
    """
    guide = conn.execute("SELECT * FROM study_guides WHERE id = ?", (guide_id,)).fetchone()
    if not guide:
        return None

    if not from_db:
        content = guide["content_json"]
        if content and content != "{}":
            try:
                parsed = json.loads(content)
                if parsed.get("steps"):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass

    # Build from legacy tables
    steps = _steps_from_db(conn, guide_id)
    data = {
        "format": "scripture-study-v1",
        "title": guide["title"],
        "description": guide["description"] or "",
        "theme": guide["theme"] or "",
        "seed_verse": guide["seed_verse"] or "",
        "author": {"name": guide["created_by"] or "anonymous", "id": ""},
        "forked_from": None,
        "created_at": guide["created_at"],
        "steps": steps,
        "graph_summary": _summarize_graph(steps),
    }
    return data


def _summarize_graph(steps):
    """Compute graph summary from steps."""
    all_layers = set()
    total = 0
    hubs = set()
    for s in steps:
        for c in s.get("connections", []):
            all_layers.add(c.get("layer", ""))
            total += 1
            hubs.add(c.get("from", ""))
            hubs.add(c.get("to", ""))
    return {
        "total_connections": total,
        "unique_layers": sorted(l for l in all_layers if l),
        "hub_verses": sorted(h for h in hubs if h)[:20],
    }


# ─── CRUD ───


def update_guide(conn, guide_id, title=None, description=None, theme=None, seed_verse=None):
    """Update study guide metadata.
    
    Args:
        guide_id: Study guide ID
        title: New title (or None to keep)
        description: New description
        theme: New theme
        seed_verse: New seed verse
    
    Returns: dict with guide_id
    """
    fields = {}
    if title is not None: fields["title"] = title
    if description is not None: fields["description"] = description
    if theme is not None: fields["theme"] = theme
    if seed_verse is not None: fields["seed_verse"] = seed_verse
    
    if fields:
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values())
        vals.append(guide_id)
        conn.execute(f"UPDATE study_guides SET {sets}, updated_at = datetime('now') WHERE id = ?", vals)
        conn.commit()
    
    return {"guide_id": guide_id}


def remove_step(conn, guide_id, step_number):
    """Remove a step from a study guide.
    
    Args:
        guide_id: Study guide ID
        step_number: Step number to remove
    
    Returns: dict confirming removal
    """
    conn.execute(
        "DELETE FROM study_guide_steps WHERE study_guide_id = ? AND step_number = ?",
        (guide_id, step_number),
    )
    # Re-number remaining steps
    remaining = conn.execute(
        "SELECT id, step_number FROM study_guide_steps WHERE study_guide_id = ? ORDER BY step_number",
        (guide_id,),
    ).fetchall()
    for i, r in enumerate(remaining):
        new_num = i + 1
        if r["step_number"] != new_num:
            conn.execute(
                "UPDATE study_guide_steps SET step_number = ? WHERE id = ?",
                (new_num, r["id"]),
            )
    _sync_content_json(conn, guide_id)
    conn.commit()
    return {"guide_id": guide_id, "removed_step": step_number}


def reorder_steps(conn, guide_id, step_order):
    """Reorder steps in a study guide.
    
    Args:
        guide_id: Study guide ID
        step_order: List of step IDs in the new order
    
    Returns: dict with guide_id
    """
    for i, step_id in enumerate(step_order):
        conn.execute(
            "UPDATE study_guide_steps SET step_number = ? WHERE id = ? AND study_guide_id = ?",
            (i + 1, step_id, guide_id),
        )
    _sync_content_json(conn, guide_id)
    conn.commit()
    return {"guide_id": guide_id}


def bulk_update_steps(conn, guide_id, steps):
    """Replace all steps of a study guide.
    
    Deletes existing steps and inserts the new ones.
    Handles re-numbering automatically.
    
    Args:
        guide_id: Study guide ID
        steps: List of step dicts
    
    Returns: dict with guide_id, step_count
    """
    conn.execute("DELETE FROM study_guide_steps WHERE study_guide_id = ?", (guide_id,))
    for i, s in enumerate(steps):
        add_step(conn, guide_id, i + 1,
                 verse_id=s.get("verse", ""),
                 title=s.get("title", ""),
                 explanation=s.get("explanation", ""),
                 connection_from=s.get("connection_from", ""),
                 connection_type=s.get("connection_type", ""),
                 connection_layer=s.get("connection_layer", ""),
                 choices=s.get("choices", []))
    conn.commit()
    return {"guide_id": guide_id, "step_count": len(steps)}


def create_guide(conn, title, description="", theme="", seed_verse="", created_by="ai", is_public=0, steps=None):
    """Create a new study guide.

    Args:
        title: Display title
        description: Optional description
        theme: Theme tag
        seed_verse: Starting verse ID
        created_by: 'ai', 'user', or 'shared'
        is_public: 0 or 1
        steps: Optional list of step dicts to pre-populate

    Returns: dict with guide_id, title
    """
    conn.execute(
        "INSERT INTO study_guides (title, description, theme, seed_verse, created_by, is_public) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (title, description, theme, seed_verse, created_by, is_public),
    )
    conn.commit()

    guide = conn.execute(
        "SELECT id FROM study_guides WHERE title = ? ORDER BY created_at DESC LIMIT 1",
        (title,),
    ).fetchone()
    gid = guide["id"] if guide else None

    if steps and gid:
        for i, s in enumerate(steps):
            add_step(conn, gid, i + 1, s.get("verse", ""),
                     title=s.get("title", ""),
                     explanation=s.get("explanation", ""),
                     connection_from=s.get("connection_from", ""),
                     connection_type=s.get("connection_type", ""),
                     connection_layer=s.get("connection_layer", ""),
                     choices=s.get("choices", []))

    return {"guide_id": gid, "title": title}


def add_step(conn, guide_id, step_number, verse_id, title="", explanation="",
             connection_from="", connection_type="", connection_layer="", choices=None):
    """Add a step to a study guide.

    Args:
        guide_id: Study guide ID
        step_number: Sequential step number
        verse_id: Verse ID for this step
        title: Short title
        explanation: AI-generated explanation
        connection_from: Previous verse this step connects from
        connection_type: Type of connection
        connection_layer: Layer of connection
        choices: List of branching choices [{verse, label}, ...]

    Returns: dict confirming the step
    """
    choices_json = json.dumps(choices or [])
    conn.execute("""
        INSERT INTO study_guide_steps
            (study_guide_id, step_number, verse_id, title, explanation,
             connection_from, connection_type, connection_layer, choices_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(study_guide_id, step_number) DO UPDATE SET
            verse_id = excluded.verse_id,
            title = excluded.title,
            explanation = excluded.explanation,
            connection_from = excluded.connection_from,
            connection_type = excluded.connection_type,
            connection_layer = excluded.connection_layer,
            choices_json = excluded.choices_json
    """, (guide_id, step_number, verse_id, title, explanation,
          connection_from, connection_type, connection_layer, choices_json))
    
    # Sync content_json
    _sync_content_json(conn, guide_id)
    conn.commit()

    return {"guide_id": guide_id, "step_number": step_number, "verse": verse_id}


def _sync_content_json(conn, guide_id):
    """Rebuild the content_json column from the current state."""
    data = _build_study_json(conn, guide_id, from_db=True)
    if data:
        conn.execute(
            "UPDATE study_guides SET content_json = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(data, ensure_ascii=False), guide_id),
        )


def get_guide(conn, guide_id):
    """Get a study guide with all its steps (enriched)."""
    guide = conn.execute("SELECT * FROM study_guides WHERE id = ?", (guide_id,)).fetchone()
    if not guide:
        return None

    data = _build_study_json(conn, guide_id)
    if not data:
        return None

    return {
        "guide": dict(guide),
        "steps": data["steps"],
        "graph_summary": data.get("graph_summary", {}),
    }


def list_guides(conn, theme=None, limit=20):
    """List all study guides, optionally filtered by theme."""
    sql = """
        SELECT sg.*, COUNT(ss.id) as step_count
        FROM study_guides sg
        LEFT JOIN study_guide_steps ss ON ss.study_guide_id = sg.id
    """
    params = []
    if theme:
        sql += " WHERE sg.theme = ?"
        params.append(theme)
    sql += " GROUP BY sg.id ORDER BY sg.updated_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def suggest_path(conn, seed_verse, theme=""):
    """Suggest an exploration path from a seed verse through the connection graph.

    Analyzes connections and suggests the next most interesting verses to visit.

    Args:
        seed_verse: Starting verse ID
        theme: Optional theme to guide suggestions

    Returns: dict with direct connections and deeper paths
    """
    # Direct connections from the seed verse
    direct = conn.execute("""
        SELECT c.target_verse, c.layer, c.type, c.strength, c.confidence,
               v.text_english as target_text,
               b.title as book_title
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
        ORDER BY c.strength DESC
        LIMIT 20
    """, (seed_verse,)).fetchall()

    # Theme filter for direct connections
    if theme:
        weighted = []
        for c in direct:
            score = c["strength"]
            if theme == "angel_of_the_lord" and "malach" in (c.get("type", "") or "").lower():
                score *= 1.5
            elif theme == "covenant" and "covenant" in (c.get("type", "") or "").lower():
                score *= 1.5
            weighted.append((score, dict(c)))
        weighted.sort(key=lambda x: -x[0])
        direct_results = [w[1] for w in weighted[:20]]
    else:
        direct_results = [dict(r) for r in direct]

    # Get 2-hop paths (deeper connections)
    deeper = conn.execute("""
        SELECT c2.target_verse, c2.layer as hop2_layer, c2.type as hop2_type,
               c1.target_verse as hop1_target, c1.layer as hop1_layer,
               v.text_english as target_text,
               b.title as book_title
        FROM connections c1
        JOIN connections c2 ON c2.source_verse = c1.target_verse
        JOIN verses v ON v.id = c2.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c1.source_verse = ?
          AND c2.target_verse != ?
          AND c2.target_verse != c1.source_verse
        ORDER BY c2.strength DESC
        LIMIT 30
    """, (seed_verse, seed_verse)).fetchall()

    # De-duplicate deeper paths
    seen_targets = set()
    deduped_deeper = []
    for r in deeper:
        if r["target_verse"] not in seen_targets:
            seen_targets.add(r["target_verse"])
            deduped_deeper.append(dict(r))

    return {
        "seed": seed_verse,
        "direct_connections": direct_results,
        "deeper_paths": deduped_deeper[:20],
    }


# ─── Export ───


def export_json(conn, guide_id, from_db=False):
    """Export a study guide as a self-contained JSON string.

    The JSON includes all steps, full graph paths, verse texts, and metadata.
    It can be re-imported into any instance of the app.

    Args:
        guide_id: Study guide ID
        from_db: If True, read fresh from the steps table (ignore cache)

    Returns: JSON string
    """
    data = _build_study_json(conn, guide_id, from_db=from_db)
    if not data:
        return None
    return json.dumps(data, indent=2, ensure_ascii=False)


def import_json(conn, json_str, created_by="user"):
    """Import a study from a JSON string.
    
    Creates a new study guide with all steps populated from the JSON.
    Supports the scripture-study-v1 format.

    Args:
        json_str: JSON string (scripture-study-v1 format)
        created_by: Creator tag for the new study

    Returns: dict with guide_id, title
    """
    data = json.loads(json_str)
    if data.get("format") != "scripture-study-v1":
        raise ValueError(f"Unknown format: {data.get('format')}. Expected 'scripture-study-v1'.")

    result = create_guide(
        conn,
        title=data.get("title", "Imported Study"),
        description=data.get("description", ""),
        theme=data.get("theme", ""),
        seed_verse=data.get("seed_verse", ""),
        created_by=created_by,
        is_public=0,
    )
    gid = result["guide_id"]

    for s in data.get("steps", []):
        add_step(
            conn, gid, s["step"],
            verse_id=s["verse"],
            title=s.get("title", ""),
            explanation=s.get("explanation", ""),
            connection_from=s.get("connection_from", ""),
            connection_type=s.get("connection_type", ""),
            connection_layer=s.get("connection_layer", ""),
            choices=s.get("choices", []),
        )

    # Store the full content_json
    conn.execute(
        "UPDATE study_guides SET content_json = ? WHERE id = ?",
        (json.dumps(data, ensure_ascii=False), gid),
    )
    conn.commit()

    return {"guide_id": gid, "title": data.get("title", "Imported Study")}


def _slugify(title):
    """Generate a URL-safe slug from a title."""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        slug = str(uuid.uuid4())[:8]
    return slug[:60]


def publish_study(conn, guide_id, author_name="anonymous", author_id="", forked_from=None):
    """Publish a study as an immutable snapshot.

    Freezes the current state of the study into a published_studies record
    with a unique slug URL.

    Args:
        guide_id: Study guide ID to publish
        author_name: Display name of the author
        author_id: Optional author identifier
        forked_from: Optional slug of the study this was forked from

    Returns: dict with slug, url, id
    """
    guide = conn.execute("SELECT * FROM study_guides WHERE id = ?", (guide_id,)).fetchone()
    if not guide:
        return {"error": f"Study guide {guide_id} not found"}

    # Build the full content
    data = _build_study_json(conn, guide_id)
    if not data:
        return {"error": "Failed to build study data"}

    # Update author metadata
    data["author"] = {"name": author_name, "id": author_id}
    data["forked_from"] = forked_from
    data["published_at"] = datetime.now().isoformat()

    content_str = json.dumps(data, ensure_ascii=False)

    # Generate unique slug
    base_slug = _slugify(guide["title"])
    slug = base_slug
    counter = 1
    while conn.execute("SELECT 1 FROM published_studies WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{counter}"
        counter += 1

    pub_id = str(uuid.uuid4())[:8]
    conn.execute("""
        INSERT INTO published_studies (id, study_guide_id, title, description,
            author_name, author_id, forked_from, content_json, slug)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pub_id, guide_id, guide["title"], guide["description"] or "",
          author_name, author_id, forked_from or None, content_str, slug))
    conn.commit()

    return {
        "id": pub_id,
        "slug": slug,
        "url": f"/study/{slug}",
        "title": guide["title"],
    }


def get_published(conn, slug):
    """Get a published study by its slug.

    Args:
        slug: The URL slug

    Returns: dict with published study data, or None
    """
    row = conn.execute("SELECT * FROM published_studies WHERE slug = ?", (slug,)).fetchone()
    if not row:
        return None

    # Increment view count
    conn.execute("UPDATE published_studies SET view_count = view_count + 1 WHERE slug = ?", (slug,))
    conn.commit()

    data = json.loads(row["content_json"])
    return {
        "id": row["id"],
        "study_guide_id": row["study_guide_id"],
        "slug": row["slug"],
        "title": row["title"],
        "description": row["description"],
        "author": {"name": row["author_name"], "id": row["author_id"]},
        "forked_from": row["forked_from"],
        "version": row["version"],
        "view_count": row["view_count"] + 1,  # +1 for this view
        "fork_count": row["fork_count"],
        "created_at": row["created_at"],
        "steps": data.get("steps", []),
        "graph_summary": data.get("graph_summary", {}),
    }


def list_published(conn, limit=20, offset=0):
    """List published studies, most recent first."""
    rows = conn.execute("""
        SELECT id, slug, title, description, author_name, author_id,
               forked_from, version, view_count, fork_count, created_at
        FROM published_studies
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset)).fetchall()
    return [dict(r) for r in rows]


def fork_published(conn, slug, created_by="user"):
    """Fork a published study into a new mutable study guide.

    The new guide is pre-populated with all steps from the published study,
    linked via forked_from for attribution.

    Args:
        slug: Slug of the published study to fork
        created_by: Creator of the fork

    Returns: dict with new guide_id
    """
    pub = get_published(conn, slug)
    if not pub:
        return {"error": f"Published study '{slug}' not found"}

    # Create new guide
    result = create_guide(
        conn,
        title=pub["title"] + " (fork)",
        description=pub.get("description", ""),
        seed_verse=pub.get("steps", [{}])[0].get("verse", "") if pub.get("steps") else "",
        created_by=created_by,
    )
    gid = result["guide_id"]

    # Populate steps
    for s in pub.get("steps", []):
        add_step(
            conn, gid, s["step"],
            verse_id=s["verse"],
            title=s.get("title", ""),
            explanation=s.get("explanation", ""),
            connection_from=s.get("connection_from", ""),
            connection_type=s.get("connection_type", ""),
            connection_layer=s.get("connection_layer", ""),
            choices=s.get("choices", []),
        )

    conn.commit()

    # Increment fork count on original
    conn.execute("UPDATE published_studies SET fork_count = fork_count + 1 WHERE slug = ?", (slug,))
    conn.commit()

    return {"guide_id": gid, "title": pub["title"] + " (fork)", "forked_from": slug}


# ─── HTML Export ───


def export_html(conn, guide_id):
    """Export a study as a self-contained HTML page.

    Args:
        guide_id: Study guide ID

    Returns: HTML string
    """
    data = _build_study_json(conn, guide_id)
    if not data:
        return None
    return _render_html(data)


def _render_html(data):
    """Render a study as a standalone HTML page."""
    steps_html = ""
    for i, s in enumerate(data.get("steps", [])):
        step_num = i + 1
        verse = s.get("verse", "")
        title = s.get("title", f"Step {step_num}")
        explanation = s.get("explanation", "")
        verse_text = s.get("verse_text", "")
        book_title = s.get("book_title", "")
        connections = s.get("connections", [])

        # Verse reference
        parts = verse.split(".")
        ref_link = f"/study/{parts[0]}.{parts[1]}" if len(parts) >= 2 else "#"

        conns_html = ""
        if connections:
            items = ""
            for c in connections[:3]:
                items += f"""<li class="connection-item">
                    <span class="connection-type">{c.get('type', '').replace('_', ' ')}</span>
                    <span class="connection-meta">({c.get('layer', '')}, strength: {c.get('strength', 0):.2f})</span>
                    <span class="connection-target">→ {c.get('to', '')}</span>
                </li>"""
            if len(connections) > 3:
                items += f"<li class='connection-item muted'>+ {len(connections) - 3} more connections</li>"
            conns_html = f"""<div class="connections">
                <h4>Connections</h4>
                <ul>{items}</ul>
            </div>"""

        steps_html += f"""
        <div class="step">
            <div class="step-header">
                <span class="step-number">{step_num}</span>
                <h3 class="step-title">{title}</h3>
            </div>
            <div class="step-body">
                <div class="verse-ref">
                    <a href="{ref_link}" target="_blank" class="ref-link">📖 {verse}</a>
                    <span class="book-label">{book_title}</span>
                </div>
                <blockquote class="verse-text">{verse_text}</blockquote>
                <div class="explanation">{explanation}</div>
                {conns_html}
            </div>
        </div>"""

    # Graph summary
    gs = data.get("graph_summary", {})
    graph_summary_html = f"""
    <div class="graph-summary">
        <h3>Graph Summary</h3>
        <p>Total connections: {gs.get('total_connections', 0)}</p>
        <p>Layers: {', '.join(gs.get('unique_layers', []))}</p>
    </div>""" if gs.get('total_connections', 0) > 0 else ""

    author = data.get("author", {}).get("name", "anonymous")
    title = data.get("title", "Study")
    description = data.get("description", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — Scripture Study</title>
<style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
           color: #1a1a2e; background: #f8f9fa; line-height: 1.6; }}
    .container {{ max-width: 800px; margin: 0 auto; padding: 2rem 1rem; }}
    .header {{ margin-bottom: 2rem; padding-bottom: 1rem; border-bottom: 2px solid #e2e8f0; }}
    .header h1 {{ font-size: 1.5rem; font-weight: 700; color: #1a1a2e; }}
    .header .meta {{ font-size: 0.85rem; color: #64748b; margin-top: 0.5rem; }}
    .header .description {{ margin-top: 0.5rem; color: #475569; font-size: 0.95rem; }}
    .step {{ background: white; border: 1px solid #e2e8f0; border-radius: 8px;
            margin-bottom: 1rem; overflow: hidden; }}
    .step-header {{ display: flex; align-items: center; gap: 0.75rem;
                   padding: 0.75rem 1rem; background: #f1f5f9;
                   border-bottom: 1px solid #e2e8f0; }}
    .step-number {{ background: #3b82f6; color: white; font-weight: 700;
                   font-size: 0.75rem; width: 1.5rem; height: 1.5rem;
                   display: flex; align-items: center; justify-content: center;
                   border-radius: 9999px; }}
    .step-title {{ font-size: 1rem; font-weight: 600; color: #1e293b; }}
    .step-body {{ padding: 1rem; }}
    .verse-ref {{ display: flex; align-items: center; gap: 0.5rem;
                 margin-bottom: 0.5rem; }}
    .ref-link {{ font-size: 0.85rem; font-weight: 600; color: #3b82f6;
                text-decoration: none; }}
    .ref-link:hover {{ text-decoration: underline; }}
    .book-label {{ font-size: 0.75rem; color: #94a3b8; }}
    .verse-text {{ background: #f8fafc; border-left: 3px solid #3b82f6;
                  padding: 0.75rem 1rem; margin: 0.5rem 0; font-style: italic;
                  color: #334155; font-size: 0.9rem; border-radius: 0 4px 4px 0; }}
    .explanation {{ color: #475569; font-size: 0.9rem; margin-top: 0.5rem; }}
    .connections {{ margin-top: 0.75rem; padding-top: 0.75rem;
                   border-top: 1px solid #e2e8f0; }}
    .connections h4 {{ font-size: 0.8rem; font-weight: 600; color: #64748b;
                       margin-bottom: 0.25rem; text-transform: uppercase;
                       letter-spacing: 0.05em; }}
    .connections ul {{ list-style: none; }}
    .connection-item {{ font-size: 0.8rem; color: #475569; padding: 0.15rem 0; }}
    .connection-type {{ font-weight: 600; color: #6366f1; }}
    .connection-meta {{ color: #94a3b8; font-size: 0.75rem; }}
    .connection-target {{ color: #64748b; }}
    .connection-item.muted {{ color: #94a3b8; font-style: italic; }}
    .graph-summary {{ background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 8px;
                     padding: 1rem; margin-top: 1.5rem; }}
    .graph-summary h3 {{ font-size: 0.85rem; font-weight: 600; color: #64748b;
                         text-transform: uppercase; letter-spacing: 0.05em;
                         margin-bottom: 0.5rem; }}
    .graph-summary p {{ font-size: 0.85rem; color: #475569; }}
    .footer {{ text-align: center; padding: 2rem 1rem; font-size: 0.8rem;
               color: #94a3b8; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>{title}</h1>
        <div class="meta">by {author} · {len(data.get('steps', []))} steps</div>
        {f'<div class="description">{description}</div>' if description else ''}
    </div>
    {steps_html}
    {graph_summary_html}
    <div class="footer">
        Generated by Scripture Knowledge Engine ·
        <a href="#" style="color:#94a3b8;">Download JSON</a>
    </div>
</div>
</body>
</html>"""


def export_markdown(conn, guide_id):
    """Export a study as Markdown text."""
    data = _build_study_json(conn, guide_id)
    if not data:
        return None

    lines = []
    lines.append(f"# {data['title']}")
    lines.append("")
    if data.get("description"):
        lines.append(data["description"])
        lines.append("")
    author = data.get("author", {}).get("name", "anonymous")
    lines.append(f"*by {author} · {len(data.get('steps', []))} steps*")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, s in enumerate(data.get("steps", [])):
        lines.append(f"## {s.get('title', f'Step {i+1}')}")
        lines.append("")
        lines.append(f"**{s['verse']}** — {s.get('book_title', '')}")
        lines.append("")
        lines.append(f"> {s.get('verse_text', '')}")
        lines.append("")
        if s.get("explanation"):
            lines.append(s["explanation"])
            lines.append("")
        for c in s.get("connections", []):
            lines.append(f"- {c.get('type', '').replace('_', ' ')} → {c.get('to', '')} "
                        f"({c.get('layer', '')}, strength: {c.get('strength', 0):.2f})")
        if s.get("connections"):
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
