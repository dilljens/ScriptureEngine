#!/usr/bin/env python3
"""Review and promote staging entries (connections + study guides).

Usage:
  python3 tools/staging.py '{"action": "list_connections"}'
  python3 tools/staging.py '{"action": "list_connections", "status": "pending", "layer": "sod"}'
  python3 tools/staging.py '{"action": "list_studies"}'
  python3 tools/staging.py '{"action": "approve", "type": "connection", "id": 5}'
  python3 tools/staging.py '{"action": "approve", "type": "study", "id": 3}'
  python3 tools/staging.py '{"action": "reject", "type": "connection", "id": 5, "reason": "not supported by text"}'
  python3 tools/staging.py '{"action": "promote_all", "min_confidence": 0.6}'
  python3 tools/staging.py '{"action": "stats"}'
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import get_db
from lib.api.staging import (
    approve_connection, approve_study,
    reject_connection, reject_study,
    list_staging_connections, list_staging_studies,
    promote_all_connections,
)

conn = get_db()


def cmd_list_connections(status="pending", layer=None, limit=50):
    items = list_staging_connections(conn, status, layer, limit)
    if not items:
        return {"ok": True, "data": [], "message": f"No {status} staging connections"}
    return {"ok": True, "data": items, "count": len(items)}


def cmd_list_studies(status="submitted", limit=20):
    items = list_staging_studies(conn, status, limit)
    if not items:
        return {"ok": True, "data": [], "message": f"No {status} staging studies"}
    return {"ok": True, "data": items, "count": len(items)}


def cmd_approve(staging_type, staging_id):
    if staging_type == "connection":
        return approve_connection(conn, staging_id, reviewer="cli")
    elif staging_type == "study":
        return approve_study(conn, staging_id, reviewer="cli")
    return {"ok": False, "error": f"Unknown type: {staging_type}"}


def cmd_reject(staging_type, staging_id, reason=""):
    if staging_type == "connection":
        return reject_connection(conn, staging_id, reason, reviewer="cli")
    elif staging_type == "study":
        return reject_study(conn, staging_id, reason, reviewer="cli")
    return {"ok": False, "error": f"Unknown type: {staging_type}"}


def cmd_promote_all(min_confidence=0.0):
    results = promote_all_connections(conn, min_confidence, reviewer="cli")
    approved = sum(1 for r in results if r.get("action") == "approved")
    failed = sum(1 for r in results if not r.get("ok"))
    return {"ok": True, "total": len(results), "approved": approved, "failed": failed}


def cmd_stats():
    pending_conn = conn.execute("SELECT COUNT(*) FROM staging_connections WHERE status='pending'").fetchone()[0]
    approved_conn = conn.execute("SELECT COUNT(*) FROM staging_connections WHERE status='approved'").fetchone()[0]
    rejected_conn = conn.execute("SELECT COUNT(*) FROM staging_connections WHERE status='rejected'").fetchone()[0]
    pending_studies = conn.execute("SELECT COUNT(*) FROM staging_studies WHERE status='submitted'").fetchone()[0]
    approved_studies = conn.execute("SELECT COUNT(*) FROM staging_studies WHERE status='approved'").fetchone()[0]
    return {
        "ok": True,
        "data": {
            "connections": {"pending": pending_conn, "approved": approved_conn, "rejected": rejected_conn},
            "studies": {"submitted": pending_studies, "approved": approved_studies},
        },
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    params = json.loads(sys.argv[1])
    action = params.get("action", "")

    if action == "list_connections":
        result = cmd_list_connections(params.get("status", "pending"),
                                      params.get("layer"),
                                      params.get("limit", 50))
    elif action == "list_studies":
        result = cmd_list_studies(params.get("status", "submitted"),
                                  params.get("limit", 20))
    elif action == "approve":
        result = cmd_approve(params.get("type"), params.get("id"))
    elif action == "reject":
        result = cmd_reject(params.get("type"), params.get("id"),
                            params.get("reason", ""))
    elif action == "promote_all":
        result = cmd_promote_all(params.get("min_confidence", 0.0))
    elif action == "stats":
        result = cmd_stats()
    else:
        result = {"error": f"Unknown action: {action}"}

    print(json.dumps(result, indent=2))
    conn.close()
