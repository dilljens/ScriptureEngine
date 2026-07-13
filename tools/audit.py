#!/usr/bin/env python3
"""MCP Tool: scripture_audit — Full provenance and quality audit for connections.

Shows every detail about how a connection was discovered, its statistical
significance, and its current quality assessment.

Usage:
  python3 audit.py '{"verse": "gen.1.1"}'
  python3 audit.py '{"verse": "gen.1.1", "layer": "linguistic"}'
  python3 audit.py '{"connection_id": 12345}'
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.controls.calibration import QUALITY_LEVELS
from lib.db import get_db


def audit_connection(conn, c):
    """Build a full audit report for one connection."""
    r = dict(c)

    quality = r.get("quality_level", "unknown")
    qinfo = QUALITY_LEVELS.get(quality, {
        "label": quality, "emoji": "❓", "color": "#999",
    })

    report = {
        "id": r["id"],
        "type": r["type"],
        "layer": r["layer"],
        "subtype": r.get("subtype", ""),
        "source_verse": r["source_verse"],
        "target_verse": r["target_verse"],
        "quality": {
            "level": quality,
            "label": qinfo.get("label", quality),
            "emoji": qinfo.get("emoji", ""),
            "color": qinfo.get("color", "#999"),
            "description": qinfo.get("description", ""),
        },
        "statistics": {
            "strength": r.get("strength", 0),
            "confidence": r.get("confidence", 0),
            "p_value": r.get("p_value"),
            "null_control": r.get("null_control", "untested"),
            "cross_validated": bool(r.get("cross_validated")),
        },
        "provenance": {
            "discovered_by": r.get("discovered_by", ""),
            "preregistered": bool(r.get("preregistered")),
        },
        "deprecated": bool(r.get("deprecated")),
        "deprecation_reason": r.get("deprecation_reason", ""),
        "metadata": r.get("metadata", "{}"),
    }

    # Get verse texts
    for vid_key in ("source_verse", "target_verse"):
        vid = r[vid_key]
        vrow = conn.execute("""
            SELECT text_english, book_id, chapter, verse FROM verses WHERE id = ?
        """, (vid,)).fetchone()
        if vrow:
            report[f"{vid_key}_text"] = vrow["text_english"][:200]

    return report


def main():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else json.loads(sys.stdin.read())
    conn = get_db()

    if "connection_id" in args:
        rows = conn.execute("SELECT * FROM connections WHERE id = ?",
                          (args["connection_id"],)).fetchall()
        if rows:
            report = audit_connection(conn, rows[0])
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"error": f"Connection {args['connection_id']} not found"}))
        conn.close()
        return

    verse = args.get("verse", "")
    layer_filter = args.get("layer")

    if not verse:
        print(json.dumps({"error": "Provide verse or connection_id"}))
        conn.close()
        return

    sql = """
        SELECT c.*, v.text_english as target_text,
               b.title as target_book_title
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
    """
    params = [verse]
    if layer_filter:
        sql += " AND c.layer = ?"
        params.append(layer_filter)
    sql += " ORDER BY c.layer, c.type"

    rows = conn.execute(sql, params).fetchall()
    reports = [audit_connection(conn, r) for r in rows]

    result = {
        "verse": verse,
        "connection_count": len(reports),
        "connections": reports,
    }

    conn.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
