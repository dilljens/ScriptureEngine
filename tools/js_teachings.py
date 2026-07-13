#!/usr/bin/env python3
"""Joseph Smith teachings search and connection tools.

Usage:
  python3 tools/js_teachings.py '{"action": "list"}'
  python3 tools/js_teachings.py '{"action": "search", "query": "priesthood"}'
  python3 tools/js_teachings.py '{"action": "get", "ref_id": "js.1844.04.07"}'
  python3 tools/js_teachings.py '{"action": "connect", "ref_id": "js.1844.04.07", "verse": "gen.1.26"}'
  python3 tools/js_teachings.py '{"action": "connections", "ref_id": "js.1844.04.07"}'
  python3 tools/js_teachings.py '{"action": "purge_orphans"}'
  python3 tools/js_teachings.py '{"action": "verse_refs", "verse": "gen.1.26"}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db

conn = get_db()


def list_sources():
    """List all JS teachings in the corpus."""
    rows = conn.execute("""
        SELECT ref_id, title, date, source_type, length(text) as char_count
        FROM js_sources ORDER BY date
    """).fetchall()

    result = []
    for r in rows:
        result.append({
            "ref_id": r["ref_id"],
            "title": r["title"],
            "date": r["date"],
            "source_type": r["source_type"],
            "char_count": r["char_count"],
        })

    return {"ok": True, "data": result, "count": len(result)}


def search_sources(query, limit=20):
    """Full-text search JS teachings corpus."""
    if not query.strip():
        return {"ok": False, "error": "Query required"}

    try:
        rows = conn.execute("""
            SELECT js.ref_id, js.title, js.date, js.source_type, js.location,
                   snippet(js_sources_fts, 1, '<b>', '</b>', '...', 48) as snippet
            FROM js_sources_fts
            JOIN js_sources js ON js_sources_fts.rowid = js.rowid
            WHERE js_sources_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit)).fetchall()
    except Exception as e:
        return {"ok": False, "error": f"FTS5 query error: {e}"}

    result = []
    for r in rows:
        result.append({
            "ref_id": r["ref_id"],
            "title": r["title"],
            "date": r["date"],
            "source_type": r["source_type"],
            "location": r["location"],
            "snippet": r["snippet"],
        })

    return {"ok": True, "data": result, "count": len(result), "query": query}


def get_source(ref_id):
    """Get a JS teaching by ref_id with full text."""
    row = conn.execute("""
        SELECT * FROM js_sources WHERE ref_id = ?
    """, (ref_id,)).fetchone()

    if not row:
        return {"ok": False, "error": f"Source '{ref_id}' not found"}

    return {"ok": True, "data": {
        "ref_id": row["ref_id"],
        "title": row["title"],
        "date": row["date"],
        "source_type": row["source_type"],
        "location": row["location"],
        "source": row["source"],
        "text": row["text"],
        "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
    }}


def connect_source_to_verse(ref_id, verse_id, ref_type="quotation", certainty=0.5, notes=""):
    """Create a cross-reference between a JS teaching and a scripture verse."""
    source = conn.execute("SELECT 1 FROM js_sources WHERE ref_id=?", (ref_id,)).fetchone()
    if not source:
        return {"ok": False, "error": f"Source '{ref_id}' not found"}

    verse = conn.execute("SELECT id FROM verses WHERE id=?", (verse_id,)).fetchone()
    if not verse:
        return {"ok": False, "error": f"Verse '{verse_id}' not found"}

    try:
        conn.execute("""
            INSERT OR REPLACE INTO js_scripture_refs (js_ref_id, verse_id, ref_type, certainty, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (ref_id, verse_id, ref_type, certainty, notes))
        conn.commit()
        return {"ok": True, "data": {"ref": f"{ref_id} ↔ {verse_id} ({ref_type})"}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_connections_for_source(ref_id):
    """Get all scripture cross-references for a JS teaching."""
    source = conn.execute("SELECT title FROM js_sources WHERE ref_id=?", (ref_id,)).fetchone()
    if not source:
        return {"ok": False, "error": f"Source '{ref_id}' not found"}

    rows = conn.execute("""
        SELECT r.verse_id, r.ref_type, r.certainty, r.notes, v.text_english as verse_text
        FROM js_scripture_refs r
        LEFT JOIN verses v ON v.id = r.verse_id
        WHERE r.js_ref_id = ?
        ORDER BY r.ref_type
    """, (ref_id,)).fetchall()

    result = []
    for r in rows:
        result.append({
            "verse": r["verse_id"],
            "ref_type": r["ref_type"],
            "certainty": r["certainty"],
            "notes": r["notes"],
            "verse_text": (r["verse_text"] or "")[:100],
        })

    return {"ok": True, "data": result, "count": len(result), "source": source["title"]}


def purge_orphan_refs():
    """Remove scripture refs for JS sources that no longer exist."""
    conn.execute("""
        DELETE FROM js_scripture_refs
        WHERE js_ref_id NOT IN (SELECT ref_id FROM js_sources)
    """)
    deleted = conn.total_changes
    conn.commit()
    return {"ok": True, "data": {"deleted": deleted}}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    params = json.loads(sys.argv[1])
    action = params.get("action", "")

    if action == "list":
        result = list_sources()
    elif action == "search":
        result = search_sources(params.get("query", ""), params.get("limit", 20))
    elif action == "get":
        result = get_source(params.get("ref_id", ""))
    elif action == "connect":
        result = connect_source_to_verse(params.get("ref_id", ""), params.get("verse", ""), params.get("ref_type", "quotation"), params.get("certainty", 0.5), params.get("notes", ""))
    elif action == "connections":
        result = get_connections_for_source(params.get("ref_id", ""))
    elif action == "verse_refs":
        verse_id = params.get("verse", "")
        rows = conn.execute("""
            SELECT r.js_ref_id, r.ref_type, r.certainty, js.title, js.date
            FROM js_scripture_refs r
            JOIN js_sources js ON js.ref_id = r.js_ref_id
            WHERE r.verse_id = ?
            ORDER BY js.date
        """, (verse_id,)).fetchall()
        result = {"ok": True, "data": [dict(r) for r in rows], "count": len(rows), "verse": verse_id}
    elif action == "purge_orphans":
        result = purge_orphan_refs()
    else:
        result = {"error": f"Unknown action: {action}"}

    print(json.dumps(result, indent=2))
    conn.close()
