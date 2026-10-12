"""Hebrew session summarizer (grammar tracking Phase 2).

Stdlib-only, read-only rollup + persistence helpers. Pure functions taking
a sqlite3 connection -- no globals, no module-level DB handles.

Every query in :func:`summarize_hebrew_session` is defensive (try/except
returning empty defaults) so the summarizer can never crash a
session-complete call when tables/columns are absent.
"""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timezone

CATEGORIES = ("grammar", "verb", "syntax", "root", "word")

MASTERED_THRESHOLD = 0.8

MEMORY_KEY = "hebrew_knowledge_state"
MEMORY_SOURCE = "hebrew_session_summary"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso() -> str:
    return _utc_now().isoformat()


def summarize_hebrew_session(conn: sqlite3.Connection, user_id: str) -> dict:
    """Read-only rollup of a user's Hebrew practice state.

    Returns a JSON-serializable dict with keys: user_id, generated_at,
    categories, weakest_nodes, due_by_mode, new_today,
    confusion_hotspots.
    """
    generated_at = _utc_iso()
    categories = _category_stats(conn, user_id)
    weakest_nodes = _weakest_nodes(conn, user_id)
    due_by_mode = _due_by_mode(conn)
    new_today = _new_today(conn)
    confusion_hotspots = _confusion_hotspots(conn, user_id)
    return {
        "user_id": user_id,
        "generated_at": generated_at,
        "categories": categories,
        "weakest_nodes": weakest_nodes,
        "due_by_mode": due_by_mode,
        "new_today": new_today,
        "confusion_hotspots": confusion_hotspots,
    }


def _category_stats(conn: sqlite3.Connection, user_id: str) -> dict:
    defaults = {
        cat: {"avg_mastery": 0.0, "practiced_count": 0, "mastered_count": 0}
        for cat in CATEGORIES
    }
    try:
        rows = conn.execute(
            """
            SELECT n.category, p.mastery
            FROM hebrew_progress p
            JOIN hebrew_nodes n ON n.id = p.node_id
            WHERE p.user_id = ?
            """,
            (user_id,),
        ).fetchall()
    except Exception:
        return defaults
    buckets: dict[str, list[float]] = defaultdict(list)
    try:
        for category, mastery in rows:
            if category in CATEGORIES:
                try:
                    buckets[category].append(float(mastery or 0.0))
                except (TypeError, ValueError):
                    buckets[category].append(0.0)
    except Exception:
        return defaults
    for cat in CATEGORIES:
        vals = buckets.get(cat, [])
        if not vals:
            continue
        try:
            avg = sum(vals) / len(vals)
        except Exception:
            avg = 0.0
        defaults[cat] = {
            "avg_mastery": avg,
            "practiced_count": len(vals),
            "mastered_count": sum(1 for v in vals if v >= MASTERED_THRESHOLD),
        }
    return defaults


def _weakest_nodes(conn: sqlite3.Connection, user_id: str, limit: int = 5) -> list:
    try:
        rows = conn.execute(
            """
            SELECT p.node_id, n.title, n.category, p.mastery, p.attempts,
                   COALESCE(SUM(r.lapses), 0) AS lapses
            FROM hebrew_progress p
            LEFT JOIN hebrew_nodes n ON n.id = p.node_id
            LEFT JOIN hebrew_review_state r
                   ON r.node_id = p.node_id AND r.user_id = p.user_id
            WHERE p.user_id = ? AND COALESCE(p.attempts, 0) > 0
            GROUP BY p.node_id, n.title, n.category, p.mastery, p.attempts
            ORDER BY p.mastery ASC, lapses DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    except Exception:
        return []
    out = []
    try:
        for node_id, title, category, mastery, attempts, lapses in rows:
            try:
                out.append(
                    {
                        "node_id": node_id,
                        "title": title if title is not None else node_id,
                        "category": category if category is not None else "",
                        "mastery": float(mastery or 0.0),
                        "attempts": int(attempts or 0),
                        "lapses": int(lapses or 0),
                    }
                )
            except (TypeError, ValueError):
                continue
    except Exception:
        return []
    return out


def _due_by_mode(conn: sqlite3.Connection) -> dict:
    try:
        now = _utc_now().strftime("%Y-%m-%d %H:%M:%S")
        rows = conn.execute(
            """
            SELECT card_mode, COUNT(*)
            FROM hebrew_review_state
            WHERE due <= ?
            GROUP BY card_mode
            """,
            (now,),
        ).fetchall()
    except Exception:
        return {}
    out: dict[str, int] = {}
    try:
        for mode, count in rows:
            try:
                out[str(mode)] = int(count)
            except (TypeError, ValueError):
                continue
    except Exception:
        return {}
    return out


def _new_today(conn: sqlite3.Connection) -> int:
    try:
        rows = conn.execute(
            """
            SELECT COUNT(DISTINCT node_id)
            FROM hebrew_review_state
            WHERE date(last_review) = date('now')
            """
        ).fetchone()
    except Exception:
        return 0
    try:
        return int(rows[0] or 0) if rows else 0
    except (TypeError, ValueError):
        return 0


def _confusion_hotspots(conn: sqlite3.Connection, user_id: str, limit: int = 3) -> list:
    try:
        rows = conn.execute(
            """
            SELECT e.node_id, n.title, COUNT(*) AS misses
            FROM hebrew_attempt_events e
            LEFT JOIN hebrew_nodes n ON n.id = e.node_id
            WHERE e.user_id = ?
              AND COALESCE(e.correct, 1) = 0
              AND date(e.created_at) >= date('now', '-7 days')
            GROUP BY e.node_id, n.title
            ORDER BY misses DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    except Exception:
        return []
    out = []
    try:
        for node_id, title, misses in rows:
            try:
                out.append(
                    {
                        "node_id": node_id,
                        "title": title if title is not None else node_id,
                        "misses": int(misses or 0),
                    }
                )
            except (TypeError, ValueError):
                continue
    except Exception:
        return []
    return out


def write_session_summary(
    conn: sqlite3.Connection, user_id: str, summary: dict
) -> dict:
    """Persist a summary to tutor_memory + tutor_session_summary.

    Uses INSERT ... ON CONFLICT for tutor_memory(user_id, key) so a
    re-run updates the existing 'hebrew_knowledge_state' row.
    """
    value = json.dumps(summary)
    updated_at = _utc_iso()
    try:
        weakest = summary.get("weakest_nodes") or []
        weakest_title = (
            weakest[0].get("title", "?") if isinstance(weakest, list) and weakest else "none"
        )
        practiced_total = 0
        categories = summary.get("categories") or {}
        if isinstance(categories, dict):
            for stats in categories.values():
                try:
                    practiced_total += int(stats.get("practiced_count", 0))
                except (TypeError, ValueError, AttributeError):
                    continue
        evidence = f"{practiced_total} practiced, weakest: {weakest_title}"
    except Exception:
        evidence = "hebrew session summary"
    conn.execute(
        """
        INSERT INTO tutor_memory (user_id, key, value, source, evidence, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, key) DO UPDATE SET
            value = excluded.value,
            source = excluded.source,
            evidence = excluded.evidence,
            updated_at = excluded.updated_at
        """,
        (user_id, MEMORY_KEY, value, MEMORY_SOURCE, evidence, updated_at),
    )
    session_key = f"hebrew-{date.today().isoformat()}"
    try:
        turn_count = 0
        categories = summary.get("categories") or {}
        if isinstance(categories, dict):
            for stats in categories.values():
                try:
                    turn_count += int(stats.get("practiced_count", 0))
                except (TypeError, ValueError, AttributeError):
                    continue
    except Exception:
        turn_count = 0
    conn.execute(
        """
        INSERT INTO tutor_session_summary
            (session_key, user_id, summary, turn_count, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(session_key) DO UPDATE SET
            user_id = excluded.user_id,
            summary = excluded.summary,
            turn_count = excluded.turn_count,
            updated_at = excluded.updated_at
        """,
        (session_key, user_id, value, turn_count, updated_at),
    )
    try:
        conn.commit()
    except Exception:
        pass
    return {"ok": True, "memory_key": MEMORY_KEY}
