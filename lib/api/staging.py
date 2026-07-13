"""
Staging — proposed connections and study guides awaiting review.

Web UI / Chat LLM creates staging entries.
Devs approve via CLI (tools/staging.py) to promote into the real tables.
"""

import json


def stage_connection(conn, source_verse, target_verse, layer, type_name,
                     subtype="", strength=0.5, confidence=0.5,
                     metadata=None, reasoning="", submitted_by="llm"):
    """Submit a proposed connection to the staging table."""
    meta_json = json.dumps(metadata or {})
    try:
        cur = conn.execute("""
            INSERT INTO staging_connections
                (source_verse, target_verse, layer, type, subtype,
                 strength, confidence, metadata, reasoning, submitted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (source_verse, target_verse, layer, type_name, subtype,
              strength, confidence, meta_json, reasoning, submitted_by))
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def stage_study(conn, title, description="", theme="", seed_verse="",
                steps=None, metadata=None, submitted_by="llm"):
    """Submit a proposed study guide to the staging table."""
    steps_json = json.dumps(steps or [])
    meta_json = json.dumps(metadata or {})
    try:
        cur = conn.execute("""
            INSERT INTO staging_studies
                (title, description, theme, seed_verse, steps_json, metadata, submitted_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, description, theme, seed_verse, steps_json, meta_json, submitted_by))
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_staging_connections(conn, status="pending", layer=None, limit=50):
    """List staging connections, optionally filtered."""
    sql = "SELECT * FROM staging_connections WHERE status=? "
    params = [status]
    if layer:
        sql += "AND layer=? "
        params.append(layer)
    sql += "ORDER BY submitted_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def list_staging_studies(conn, status="submitted", limit=20):
    """List staging studies, optionally filtered."""
    rows = conn.execute("""
        SELECT * FROM staging_studies WHERE status=? ORDER BY submitted_at DESC LIMIT ?
    """, (status, limit)).fetchall()
    return [dict(r) for r in rows]


def approve_connection(conn, staging_id, reviewer="cli"):
    """Promote a staging connection to the real connections table."""
    row = conn.execute("SELECT * FROM staging_connections WHERE id=? AND status='pending'",
                       (staging_id,)).fetchone()
    if not row:
        return {"ok": False, "error": f"No pending staging connection #{staging_id}"}

    try:
        from lib.db import add_connection
        add_connection(conn, row["source_verse"], row["target_verse"],
                       layer=row["layer"], type_name=row["type"],
                       subtype=row["subtype"], strength=row["strength"],
                       confidence=row["confidence"],
                       discovered_by=row["submitted_by"],
                       metadata=json.loads(row["metadata"]) if row["metadata"] else {})
        conn.execute("""
            UPDATE staging_connections
            SET status='approved', reviewed_by=?, reviewed_at=datetime('now')
            WHERE id=?
        """, (reviewer, staging_id))
        conn.commit()
        return {"ok": True, "action": "approved", "id": staging_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def approve_study(conn, staging_id, reviewer="cli"):
    """Promote a staging study to the real study_guides table."""
    row = conn.execute("SELECT * FROM staging_studies WHERE id=? AND status='submitted'",
                       (staging_id,)).fetchone()
    if not row:
        return {"ok": False, "error": f"No submitted staging study #{staging_id}"}

    try:
        from lib.api.study import add_step, create_guide
        steps = json.loads(row["steps_json"]) if row["steps_json"] else []

        # Create the guide
        guide = create_guide(conn, row["title"], row["description"],
                             row["theme"], row["seed_verse"], row["submitted_by"])
        if not guide.get("ok"):
            return guide
        guide_id = guide["data"]["id"]

        # Add steps
        for s in steps:
            add_step(conn, guide_id, s["step_number"], s["verse"],
                     s.get("title", ""), s.get("explanation", ""),
                     s.get("choices_json", "[]"))

        conn.execute("""
            UPDATE staging_studies
            SET status='approved', reviewed_by=?, reviewed_at=datetime('now')
            WHERE id=?
        """, (reviewer, staging_id))
        conn.commit()
        return {"ok": True, "action": "approved", "id": staging_id, "guide_id": guide_id}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def reject_connection(conn, staging_id, reason="", reviewer="cli"):
    """Reject a staging connection."""
    conn.execute("""
        UPDATE staging_connections
        SET status='rejected', rejection_reason=?, reviewed_by=?, reviewed_at=datetime('now')
        WHERE id=?
    """, (reason, reviewer, staging_id))
    conn.commit()
    return {"ok": True, "action": "rejected", "id": staging_id}


def reject_study(conn, staging_id, reason="", reviewer="cli"):
    """Reject a staging study."""
    conn.execute("""
        UPDATE staging_studies
        SET status='rejected', rejection_reason=?, reviewed_by=?, reviewed_at=datetime('now')
        WHERE id=?
    """, (reason, reviewer, staging_id))
    conn.commit()
    return {"ok": True, "action": "rejected", "id": staging_id}


def promote_all_connections(conn, min_confidence=0.0, reviewer="cli"):
    """Approve all pending connections meeting a confidence threshold."""
    pending = conn.execute("""
        SELECT * FROM staging_connections
        WHERE status='pending' AND confidence >= ?
        ORDER BY submitted_at
    """, (min_confidence,)).fetchall()

    results = []
    for row in pending:
        result = approve_connection(conn, row["id"], reviewer)
        results.append(result)
    return results
