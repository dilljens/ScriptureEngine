"""MCP tools for the adaptive assessment system.

Session state is persisted to ~/.cache/scriptureengine/assess_sessions.json
so it survives across CLI invocations (separate processes).
Within a long-running MCP/HTTP server, the in-memory cache avoids disk I/O.
"""

import json
import os
import time
import urllib.request
import urllib.error

from lib.assessment import AssessmentEngine, KnowledgeState

_SESSION_DIR = os.path.expanduser("~/.cache/scriptureengine")
_SESSION_PATH = os.path.join(_SESSION_DIR, "assess_sessions.json")

# In-memory cache (ephemeral — survives only within a single process)
_cache = {}


def _load_all():
    """Load all sessions from disk into cache."""
    try:
        with open(_SESSION_PATH) as f:
            data = json.load(f)
        for uid, s in data.items():
            _cache[uid] = _deserialize(s)
    except (FileNotFoundError, json.JSONDecodeError):
        pass


def _save_all():
    """Write the entire cache to disk."""
    os.makedirs(_SESSION_DIR, exist_ok=True)
    data = {uid: _serialize(s) for uid, s in _cache.items()}
    tmp = _SESSION_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SESSION_PATH)


def _serialize(session):
    """Convert a session dict (with KnowledgeState/AssessmentEngine) to a JSON-safe dict."""
    state = session["state"]
    return {
        "user_id": state.user_id,
        "current_item": session.get("current_item"),
        "history": session.get("history", []),
        "target_layer": session.get("target_layer"),
        "status": session.get("status", "idle"),
        "max_items": session.get("max_items", 20),
        "mastery_prob": {str(k): v for k, v in state.mastery_prob.items()},
        "times_correct": {str(k): v for k, v in state.times_correct.items()},
        "times_wrong": {str(k): v for k, v in state.times_wrong.items()},
    }


def _deserialize(data):
    """Reconstruct a session dict from a JSON-safe dict."""
    state = KnowledgeState(user_id=data.get("user_id", "default"))
    state.mastery_prob = {int(k) if k.isdigit() else k: v for k, v in data.get("mastery_prob", {}).items()}
    state.times_correct = {int(k) if k.isdigit() else k: v for k, v in data.get("times_correct", {}).items()}
    state.times_wrong = {int(k) if k.isdigit() else k: v for k, v in data.get("times_wrong", {}).items()}
    return {
        "engine": None,
        "state": state,
        "current_item": data.get("current_item"),
        "history": data.get("history", []),
        "target_layer": data.get("target_layer"),
        "status": data.get("status", "idle"),
        "max_items": data.get("max_items", 20),
    }


def _get_session(user_id):
    """Get or create a session for the given user."""
    if user_id not in _cache:
        _load_all()
        if user_id not in _cache:
            _cache[user_id] = _deserialize({
                "user_id": user_id,
                "mastery_prob": {},
                "times_correct": {},
                "times_wrong": {},
                "history": [],
                "status": "idle",
                "max_items": 20,
            })
    return _cache[user_id]


def _save_session(user_id):
    """Persist a single session to disk immediately."""
    if user_id in _cache:
        os.makedirs(_SESSION_DIR, exist_ok=True)
        data = {}
        try:
            with open(_SESSION_PATH) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        data[user_id] = _serialize(_cache[user_id])
        tmp = _SESSION_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _SESSION_PATH)


def start_assessment(conn, user_id="default", target_layer=None, max_items=20):
    """Start a new assessment session.

    Args:
        user_id: User identifier (default: "default")
        target_layer: Optional PaRDeS level filter ("pshat", "remez", "drash", "sod")
        max_items: Maximum items to administer (default: 20)

    Returns:
        Dict with session info and first question
    """
    session = _get_session(user_id)
    session["engine"] = AssessmentEngine(conn)
    session["state"] = KnowledgeState(user_id)
    session["history"] = []
    session["target_layer"] = target_layer
    session["status"] = "active"
    session["max_items"] = max_items

    # Select first item
    item_id = session["engine"].select_item(session["state"], target_layer=target_layer)
    if item_id is None:
        session["status"] = "error"
        _save_session(user_id)
        return {"error": "No items available for assessment"}

    session["current_item"] = item_id

    # Get the question
    question = _get_question(conn, item_id)
    if not question:
        session["status"] = "error"
        _save_session(user_id)
        return {"error": f"Could not load question for item {item_id}"}

    _save_session(user_id)

    return {
        "ok": True,
        "user_id": user_id,
        "session_status": session["status"],
        "item_number": len(session["history"]) + 1,
        "total_items_planned": max_items,
        "question": question,
        "mastery": {
            "overall": session["state"].overall_mastery(),
            "by_layer": session["state"].mastery_by_layer(conn),
        },
    }


def submit_answer(conn, user_id="default", correct=False):
    """Submit an answer and get the next question.

    Args:
        user_id: User identifier
        correct: Whether the answer was correct (True/False)

    Returns:
        Dict with updated state and next question (or completion)
    """
    session = _get_session(user_id)
    if session["status"] != "active":
        return {"error": "No active session. Call start_assessment first."}

    # Re-attach engine (it wraps the db connection)
    session["engine"] = AssessmentEngine(conn)

    item_id = session["current_item"]
    if item_id is None:
        return {"error": "No current item to assess"}

    # Record response
    session["engine"].assess_response(session["state"], item_id, correct)
    session["history"].append({"item_id": item_id, "correct": correct})

    # If correct, give FIRe credit via the Go memorization service
    if correct:
        _fire_credit_for_item(conn, item_id)

    # Check termination
    should_stop, reason = session["engine"].should_terminate(
        session["state"],
        min_items=3,
        max_items=session.get("max_items", 20),
    )

    if should_stop:
        session["status"] = "completed"
        mastery_by_layer = session["state"].mastery_by_layer(conn)
        outer_fringe = session["engine"].get_outer_fringe(session["state"], limit=10)
        _save_session(user_id)
        return {
            "ok": True,
            "session_status": "completed",
            "reason": reason,
            "total_answered": len(session["history"]),
            "mastery": {
                "overall": session["state"].overall_mastery(),
                "by_layer": mastery_by_layer,
            },
            "outer_fringe": outer_fringe,
            "history": session["history"][-5:],
        }

    # Select next item
    next_item = session["engine"].select_item(
        session["state"],
        target_layer=session["target_layer"],
    )
    if next_item is None:
        session["status"] = "completed"
        _save_session(user_id)
        return {
            "ok": True,
            "session_status": "completed",
            "reason": "no more informative items",
            "total_answered": len(session["history"]),
            "mastery": {"overall": session["state"].overall_mastery()},
        }

    session["current_item"] = next_item
    question = _get_question(conn, next_item)

    _save_session(user_id)

    return {
        "ok": True,
        "user_id": user_id,
        "session_status": "active",
        "item_number": len(session["history"]) + 1,
        "question": question,
        "mastery": {
            "overall": session["state"].overall_mastery(),
            "by_layer": session["state"].mastery_by_layer(conn),
        },
    }


def get_progress(conn, user_id="default"):
    """Get current assessment progress without submitting an answer."""
    session = _get_session(user_id)
    session["engine"] = AssessmentEngine(conn)
    mastery_by_layer = session["state"].mastery_by_layer(conn)
    outer_fringe = session["engine"].get_outer_fringe(session["state"], limit=10) if session["engine"] else []

    return {
        "ok": True,
        "user_id": user_id,
        "session_status": session["status"],
        "total_answered": len(session["history"]),
        "mastery": {
            "overall": session["state"].overall_mastery(),
            "by_layer": mastery_by_layer,
        },
        "outer_fringe": outer_fringe,
    }


def _get_question(conn, item_id):
    """Get a question for a knowledge item from the assessment_items table."""
    # Try to get pre-generated question
    row = conn.execute(
        """SELECT id, question_type, question_text, options_json, correct_answer,
                  layer, bloom_level
           FROM assessment_items
           WHERE knowledge_item_id = ?
           ORDER BY RANDOM() LIMIT 1""",
        (item_id,)
    ).fetchone()

    if row:
        # row: (id, question_type, question_text, options_json, correct_answer, layer, bloom_level)
        opts = json.loads(row[3]) if row[3] else []
        return {
            "item_id": row[0],
            "type": row[1],
            "question": row[2],
            "options": opts,
            "layer": row[5],
            "bloom_level": row[6],
        }

    # Fallback: create question on the fly from knowledge_items
    ki = conn.execute(
        """SELECT id, verse_id, connection_type, target_verse, pa_r_de_s_level
           FROM knowledge_items WHERE id = ?""",
        (item_id,)
    ).fetchone()

    if not ki:
        return None

    return {
        "item_id": item_id,
        "type": "true_false",
        "question": f"Is there a {ki[2]} connection between {ki[1]} and {ki[3]}?",
        "options": ["True", "False"],
        "correct_answer": "True" if ki else "False",
        "layer": ki[4],
        "bloom_level": "remember",
    }


def _fire_credit_for_item(conn, item_id):
    """Give FIRe credit to verses involved in a knowledge item when answered correctly.
    
    Calls the Go memorization service to boost connected verse cards.
    """
    ki = conn.execute(
        "SELECT verse_id, target_verse FROM knowledge_items WHERE id = ?",
        (item_id,)
    ).fetchone()
    if not ki:
        return

    verse_id = ki[0]
    target = ki[1]
    if not verse_id or not target:
        return

    # Call Go FIRe credit endpoint for both verses (Good rating = 3)
    for vid in (verse_id, target):
        try:
            payload = json.dumps({"verse_id": vid, "rating": 3}).encode()
            req = urllib.request.Request(
                "http://localhost:8090/api/memorize/fire/credit",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            # Non-blocking — timeout after 2s
            urllib.request.urlopen(req, timeout=2)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass  # FIRe is optional — service may not be running


# ── Diagnostic Mode ──

def start_diagnostic(conn, user_id="default", max_items=30):
    """Start a pre-assessment diagnostic session.
    
    Unlike a regular assessment, the diagnostic:
    1. Samples broadly across all layers and connection types
    2. Uses conditional completion — stops asking about topics once confident
    3. Reports what the user already knows vs. needs to learn
    4. Gives FIRe credit for demonstrated knowledge
    
    Args:
        user_id: User identifier
        max_items: Maximum items to administer (default: 30)
    
    Returns:
        Dict with first question and session info
    """
    session = _get_session(user_id)
    session["engine"] = AssessmentEngine(conn)
    session["state"] = KnowledgeState(user_id)
    session["history"] = []
    session["target_layer"] = None  # all layers
    session["status"] = "diagnostic"
    session["max_items"] = max_items

    # Select first item (broad coverage, max information)
    item_id = session["engine"].select_item(session["state"], n_candidates=200)
    if item_id is None:
        session["status"] = "error"
        _save_session(user_id)
        return {"error": "No items available for diagnostic"}

    session["current_item"] = item_id
    question = _get_question(conn, item_id)
    if not question:
        session["status"] = "error"
        _save_session(user_id)
        return {"error": f"Could not load question for item {item_id}"}

    _save_session(user_id)

    return {
        "ok": True,
        "user_id": user_id,
        "mode": "diagnostic",
        "session_status": session["status"],
        "item_number": len(session["history"]) + 1,
        "total_items_planned": max_items,
        "question": question,
    }


def submit_diagnostic_answer(conn, user_id="default", correct=False):
    """Submit a diagnostic answer with conditional completion.
    
    Implements conditional completion from Math Academy Way (Ch 30):
    When mastery probability for a connection type + layer combination
    crosses 0.8, the system stops asking about that combination.
    
    Returns the diagnostic report when complete.
    """
    session = _get_session(user_id)
    if session["status"] not in ("diagnostic", "active"):
        return {"error": "No active diagnostic. Call start_diagnostic first."}

    session["engine"] = AssessmentEngine(conn)

    item_id = session["current_item"]
    if item_id is None:
        return {"error": "No current item"}

    # Record response
    session["engine"].assess_response(session["state"], item_id, correct)
    session["history"].append({"item_id": item_id, "correct": correct})

    # FIRe credit for correct answers
    if correct:
        _fire_credit_for_item(conn, item_id)

    # Check termination: max items reached
    total = len(session["history"])
    if total >= session.get("max_items", 30):
        return _finish_diagnostic(conn, session, user_id, reason="max_items")

    # Conditional completion: need at least 8 items before checking entropy
    probs = list(session["state"].mastery_prob.values())
    if len(probs) >= 8 and total >= 8:
        import math
        entropies = []
        for p in probs:
            if 0 < p < 1:
                e = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
                entropies.append(e)
        if entropies:
            avg_entropy = sum(entropies) / len(entropies)
            if avg_entropy < 0.08:  # strict threshold for diagnostic
                return _finish_diagnostic(conn, session, user_id, reason="converged")

    # Select next item with broad sampling
    next_item = session["engine"].select_item(
        session["state"],
        target_layer=None,  # all layers
        n_candidates=200,
    )
    if next_item is None:
        return _finish_diagnostic(conn, session, user_id, reason="no_more_items")

    session["current_item"] = next_item
    question = _get_question(conn, next_item)

    _save_session(user_id)

    if not question:
        return _finish_diagnostic(conn, session, user_id, reason="question_error")

    return {
        "ok": True,
        "user_id": user_id,
        "mode": "diagnostic",
        "session_status": session["status"],
        "item_number": total + 1,
        "question": question,
    }


def _finish_diagnostic(conn, session, user_id, reason):
    """Finalize diagnostic and generate report."""
    session["status"] = "completed"

    # Compute mastery by layer
    mastery_by_layer = session["state"].mastery_by_layer(conn)
    
    # Compute outer fringe (ready to learn)
    outer_fringe = session["engine"].get_outer_fringe(session["state"], limit=15)
    
    # Categorize known vs unknown by layer
    known_items = []
    unknown_items = []
    for item_id_str, prob in session["state"].mastery_prob.items():
        item_id = int(item_id_str) if isinstance(item_id_str, str) else item_id_str
        ki = conn.execute(
            "SELECT verse_id, connection_type, target_verse, pa_r_de_s_level FROM knowledge_items WHERE id = ?",
            (item_id,)
        ).fetchone()
        if ki:
            entry = {
                "item_id": item_id,
                "verse": ki["verse_id"],
                "target": ki["target_verse"],
                "type": ki["connection_type"],
                "layer": ki["pa_r_de_s_level"],
                "mastery": prob,
            }
            if prob >= 0.8:
                known_items.append(entry)
            elif prob <= 0.3:
                unknown_items.append(entry)

    report = {
        "ok": True,
        "session_status": "completed",
        "mode": "diagnostic",
        "reason": reason,
        "total_answered": len(session["history"]),
        "total_correct": sum(1 for h in session["history"] if h["correct"]),
        "total_wrong": sum(1 for h in session["history"] if not h["correct"]),
        "mastery": {
            "overall": session["state"].overall_mastery(),
            "by_layer": mastery_by_layer,
        },
        "known_count": len(known_items),
        "unknown_count": len(unknown_items),
        "outer_fringe": outer_fringe,
    }

    _save_session(user_id)
    return report


def get_diagnostic_report(conn, user_id="default"):
    """Get a diagnostic report without running a new assessment."""
    session = _get_session(user_id)
    session["engine"] = AssessmentEngine(conn)
    
    if not session["state"].mastery_prob:
        return {
            "ok": True,
            "has_diagnostic": False,
            "message": "No diagnostic data. Run start_diagnostic first.",
        }

    mastery_by_layer = session["state"].mastery_by_layer(conn)
    outer_fringe = session["engine"].get_outer_fringe(session["state"], limit=15)
    overall = session["state"].overall_mastery()

    # Count known/unknown items (top types)
    type_counts = {}
    for item_id_str, prob in session["state"].mastery_prob.items():
        item_id = int(item_id_str) if isinstance(item_id_str, str) else item_id_str
        ki = conn.execute(
            "SELECT connection_type FROM knowledge_items WHERE id = ?",
            (item_id,)
        ).fetchone()
        if ki:
            ct = ki["connection_type"]
            if ct not in type_counts:
                type_counts[ct] = {"known": 0, "unknown": 0, "total": 0}
            type_counts[ct]["total"] += 1
            if prob >= 0.8:
                type_counts[ct]["known"] += 1
            elif prob <= 0.3:
                type_counts[ct]["unknown"] += 1

    return {
        "ok": True,
        "has_diagnostic": True,
        "total_assessed": len(session["state"].mastery_prob),
        "overall_mastery": overall,
        "mastery_by_layer": mastery_by_layer,
        "outer_fringe": outer_fringe,
        "type_breakdown": type_counts,
    }
