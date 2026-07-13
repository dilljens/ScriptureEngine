#!/usr/bin/env python3
"""
MCP Tool: scripture_guided_study
Create and manage AI-guided study paths through the connection graph.

Usage:
  python3 guided_study.py '{"action": "create", "title": "Angel of the Lord", "seed": "gen.16.7"}'
  python3 guided_study.py '{"action": "add_step", "guide_id": 1, "verse": "gen.16.7", ...}'
  python3 guided_study.py '{"action": "get", "guide_id": 1}'
  python3 guided_study.py '{"action": "suggest_path", "seed": "gen.16.7", "theme": "angel_of_the_lord"}'
  python3 guided_study.py '{"action": "list"}'
  python3 guided_study.py '{"action": "build_tab", "guide_id": 1, "tab_name": "Angel of the Lord"}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.connections.graph import find_all_paths, get_connections
from lib.db import get_db


def create(conn, title, description="", theme="", seed_verse="", created_by="ai"):
    """Create a new study guide."""
    conn.execute("""
        INSERT INTO study_guides (title, description, theme, seed_verse, created_by)
        VALUES (?, ?, ?, ?, ?)
    """, (title, description, theme, seed_verse, created_by))
    conn.commit()
    row = conn.execute("SELECT id FROM study_guides ORDER BY id DESC LIMIT 1").fetchone()
    guide_id = row["id"] if row else None

    return {"status": "created", "guide_id": guide_id, "title": title}


def add_step(conn, guide_id, step_number, verse_id, title="", explanation="",
             connection_from="", connection_type="", connection_layer="",
             choices=None):
    """Add a step to a study guide."""
    choices = choices or []
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
          connection_from, connection_type, connection_layer,
          json.dumps(choices)))
    conn.commit()

    # Update the guide's updated_at
    conn.execute("UPDATE study_guides SET updated_at = datetime('now') WHERE id = ?",
                (guide_id,))

    return {
        "status": "step_added",
        "guide_id": guide_id,
        "step_number": step_number,
        "verse_id": verse_id,
    }


def get(conn, guide_id):
    """Get a study guide with all steps."""
    guide = conn.execute("SELECT * FROM study_guides WHERE id = ?",
                        (guide_id,)).fetchone()
    if not guide:
        return {"error": "Study guide not found"}

    steps = conn.execute("""
        SELECT s.*, v.text_english, v.text_hebrew,
               b.title as book_title
        FROM study_guide_steps s
        JOIN verses v ON v.id = s.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE s.study_guide_id = ?
        ORDER BY s.step_number
    """, (guide_id,)).fetchall()

    return {
        "guide": dict(guide),
        "steps": [dict(s) for s in steps],
        "step_count": len(steps),
    }


def list_guides(conn, theme=None):
    """List all study guides."""
    sql = """
        SELECT sg.*, COUNT(ss.id) as step_count
        FROM study_guides sg
        LEFT JOIN study_guide_steps ss ON ss.study_guide_id = sg.id
    """
    params = []
    if theme:
        sql += " WHERE sg.theme = ?"
        params.append(theme)
    sql += " GROUP BY sg.id ORDER BY sg.updated_at DESC LIMIT 50"
    rows = conn.execute(sql, params).fetchall()
    return {"guides": [dict(r) for r in rows]}


def suggest_path(conn, seed, theme="", max_steps=10):
    """AI-assist: suggest a path through the connection graph from a seed verse.

    This returns structured data the AI can use to build a study guide.
    It walks the connection graph outward from the seed, suggesting
    the most interesting next steps at each layer.
    """
    # Get immediate connections from the seed
    direct = get_connections(conn, seed)

    # Get the verse text
    seed_verse = conn.execute("""
        SELECT v.*, b.title as book_title
        FROM verses v JOIN books b ON b.id = v.book_id WHERE v.id = ?
    """, (seed,)).fetchone()

    # Group connections by layer
    by_layer = {}
    for c in direct:
        layer = c["layer"]
        if layer not in by_layer:
            by_layer[layer] = []
        target = conn.execute("""
            SELECT v.text_english, b.title as book_title
            FROM verses v JOIN books b ON b.id = v.book_id WHERE v.id = ?
        """, (c["target_verse"],)).fetchone()
        by_layer[layer].append({
            "verse": c["target_verse"],
            "type": c["type"],
            "subtype": c.get("subtype", ""),
            "text": target["text_english"][:120] if target else "",
            "book": target["book_title"] if target else "",
            "strength": c.get("strength", 0),
        })

    # Get the next hop — paths of depth 2
    deeper = find_all_paths(conn, seed, max_depth=2)
    # Filter to only depth-2 paths (one intermediate hop)
    depth2 = [p for p in deeper if p["depth"] == 2][:15]

    # Build structured suggestions
    suggestions = {
        "seed_verse": {
            "id": seed,
            "text": seed_verse["text_english"][:200] if seed_verse else "",
            "book": seed_verse["book_title"] if seed_verse else "",
        },
        "theme": theme,
        "direct_connections": by_layer,
        "deeper_paths": [
            {
                "path": p["path"],
                "end_verse": p["end"],
                "hops": len(p["path"]),
            }
            for p in depth2
        ],
        "available_layers": list(by_layer.keys()),
    }

    return suggestions


def build_tab(conn, guide_id, tab_name, parent_tab_id=None):
    """Create a custom tab linked to a study guide."""
    from lib.db import add_tab_content, create_custom_tab

    # Create the tab
    tab_id = create_custom_tab(conn, tab_name, parent_id=parent_tab_id,
                               icon="study")

    # Link it to the study guide
    add_tab_content(conn, tab_id, "study_guide", str(guide_id),
                    label=f"Guided: {tab_name}")

    return {
        "status": "tab_created",
        "tab_id": tab_id,
        "tab_name": tab_name,
        "guide_id": guide_id,
    }


def main():
    args = json.loads(sys.stdin.read()) if len(sys.argv) < 2 else json.loads(sys.argv[1])

    conn = get_db()
    action = args.get("action", "list")

    if action == "create":
        result = create(conn, args.get("title", ""), args.get("description", ""),
                       args.get("theme", ""), args.get("seed", ""),
                       args.get("created_by", "ai"))

    elif action == "add_step":
        result = add_step(conn, args.get("guide_id"), args.get("step_number"),
                         args.get("verse"), args.get("title", ""),
                         args.get("explanation", ""),
                         args.get("connection_from", ""),
                         args.get("connection_type", ""),
                         args.get("connection_layer", ""),
                         args.get("choices"))

    elif action == "get":
        result = get(conn, args.get("guide_id"))

    elif action == "list":
        result = list_guides(conn, args.get("theme"))

    elif action == "suggest_path":
        result = suggest_path(conn, args.get("seed", ""), args.get("theme", ""),
                            args.get("max_steps", 10))

    elif action == "build_tab":
        result = build_tab(conn, args.get("guide_id"), args.get("tab_name"),
                          args.get("parent_tab_id"))

    else:
        result = {"error": f"Unknown action: {action}"}

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
