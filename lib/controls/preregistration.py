"""Method pre-registration — prevents post-hoc pattern selection.

A detector must be pre-registered (method + parameters declared in advance)
before running against the data. Post-hoc discoveries get lower confidence.
"""

from datetime import datetime


def register_method(conn, method_name, parameters=None, null_control_plan="both"):
    """Pre-register a detection method before running it on real data.

    Args:
        conn: database connection
        method_name: unique name for the method (e.g. 'acrostic_detection_v2')
        parameters: dict of all tunable parameters
        null_control_plan: 'shuffled', 'random', or 'both'

    Returns:
        method_id: the registration ID
        preregistered_date: ISO timestamp
    """
    import json
    params_json = json.dumps(parameters or {})

    # Check if already registered
    existing = conn.execute("""
        SELECT id, preregistered, preregistered_date FROM method_registrations
        WHERE method_name = ?
    """, (method_name,)).fetchone()

    if existing:
        return {
            "id": existing["id"],
            "preregistered": bool(existing["preregistered"]),
            "date": existing["preregistered_date"],
            "note": "Already registered",
        }

    now = datetime.utcnow().isoformat()

    conn.execute("""
        INSERT INTO method_registrations (method_name, parameters_json, null_control_plan, preregistered, preregistered_date)
        VALUES (?, ?, ?, 1, ?)
    """, (method_name, params_json, null_control_plan, now))
    conn.commit()

    row = conn.execute("""
        SELECT id, preregistered_date FROM method_registrations WHERE method_name = ?
    """, (method_name,)).fetchone()

    return {
        "id": row["id"],
        "preregistered": True,
        "date": row["preregistered_date"],
    }


def is_method_registered(conn, method_name):
    """Check if a method is pre-registered.

    Returns dict with preregistered status and date, or None.
    """
    row = conn.execute("""
        SELECT * FROM method_registrations WHERE method_name = ?
    """, (method_name,)).fetchone()

    if row:
        return {
            "id": row["id"],
            "preregistered": bool(row["preregistered"]),
            "date": row["preregistered_date"],
            "parameters": row["parameters_json"],
            "status": row["status"],
        }
    return None


def list_methods(conn):
    """List all registered methods."""
    rows = conn.execute("""
        SELECT id, method_name, preregistered, preregistered_date, status
        FROM method_registrations ORDER BY preregistered_date DESC
    """).fetchall()
    return [dict(r) for r in rows]
