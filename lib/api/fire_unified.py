"""
Unified FIRe (Fluency-boosted Interleaved Review) — multi-mode credit flow.

Replaces the two separate FIRe implementations (memorize.py verse→verse,
hebrew.py concept→concept) with a single engine that handles cross-domain
propagation: a verse review boosts Hebrew concepts that appear in that verse,
and vice versa.

Credit flows through the connection graph AND through verse→entity mappings.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Credit configuration ──────────────────────────────────────────────
SUCCESS_CREDIT = 0.5       # base credit on correct review (rating ≥ 3)
FAILURE_PENALTY = 0.5      # base penalty on incorrect (rating < 3)
CREDIT_DECAY_DAILY = 0.1   # 10% decay per day overdue
KNOCKOUT_THRESHOLD = 1.0   # credit ≥ 1.0 → card is credited as reviewed
MAX_PROPAGATION_DEPTH = 2  # how many hops credit propagates
LEARN_CREDIT_WEIGHT = 0.3  # weight for learn module credit propagation


# ═══════════════════════════════════════════════════════════════════════
# Schema: creates fi_re_credits table if not exists
# ═══════════════════════════════════════════════════════════════════════

FIRE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS fi_re_credits (
    user_id     TEXT NOT NULL DEFAULT 'default',
    item_type   TEXT NOT NULL,   -- 'verse', 'hebrew_concept', 'learning_module'
    item_id     TEXT NOT NULL,
    credit      REAL DEFAULT 0.0,
    last_updated TEXT DEFAULT (datetime('now')),
    source_item_type TEXT DEFAULT NULL,  -- what gave this credit
    source_item_id   TEXT DEFAULT NULL,
    PRIMARY KEY (user_id, item_type, item_id)
);

-- Track cross-domain connections: which entities/concepts appear in which verses
CREATE TABLE IF NOT EXISTS entity_verse_bridge (
    item_type   TEXT NOT NULL,   -- 'hebrew_concept', 'entity'
    item_id     TEXT NOT NULL,
    verse_id    TEXT NOT NULL,
    weight      REAL DEFAULT 0.5,
    PRIMARY KEY (item_type, item_id, verse_id)
);
"""


# ═══════════════════════════════════════════════════════════════════════
# Core FIRe engine
# ═══════════════════════════════════════════════════════════════════════

def ensure_fire_schema(conn):
    """Create fi_re_credits and entity_verse_bridge tables."""
    conn.executescript(FIRE_SCHEMA_SQL)
    conn.commit()


def compute_fire_credit(
    conn,
    item_type: str,       # 'verse', 'hebrew_concept', 'learning_module'
    item_id: str,         # verse ref, node_id, or module_id
    rating: int,          # 1-4 scale (Again/Hard/Good/Easy)
    user_id: str = "default",
    decay_days: int = 7,
):
    """Compute and apply FIRe credit across all connected domains.

    For a successful review (rating ≥ 3):
      1. Boost connected items of the SAME type (verse→verse via connections)
      2. Boost items of OTHER types via entity bridge (verse→hebrew_concept)
      3. Update fi_re_credits table

    For a failed review (rating < 3):
      1. Penalize connected same-type items
      2. Reduce cross-domain credit

    Args:
        conn: SQLite connection to memorize.db or scripture.db
        item_type: Which domain ('verse', 'hebrew_concept', 'learning_module')
        item_id: The reviewed item's ID
        rating: 1=Again, 2=Hard, 3=Good, 4=Easy
        user_id: Who reviewed
        decay_days: Days over which existing credit decays

    Returns:
        dict with propagation results
    """
    ensure_fire_schema(conn)
    is_success = rating >= 3
    credit_base = SUCCESS_CREDIT if is_success else FAILURE_PENALTY

    # Rating multipliers
    rating_factor = {1: 0.0, 2: 0.3, 3: 1.0, 4: 1.5}.get(rating, 1.0)
    base_boost = credit_base * rating_factor

    results = {
        "item_type": item_type,
        "item_id": item_id,
        "rating": rating,
        "is_success": is_success,
        "boosts_applied": 0,
        "penalties_applied": 0,
        "cross_domain_boosts": 0,
        "recipients": [],
    }

    # ── Phase 1: Same-type propagation ──
    same_type_conns = _get_same_type_connections(conn, item_type, item_id)
    for target_id, strength in same_type_conns:
        boost = base_boost * strength * rating_factor * 0.3
        _apply_credit(conn, user_id, item_type, target_id, boost, is_success,
                      source_type=item_type, source_id=item_id)
        results["boosts_applied" if is_success else "penalties_applied"] += 1
        results["recipients"].append({
            "type": item_type, "id": target_id, "boost": round(boost, 4)
        })

    # ── Phase 1b: Stability penalty on failure (verse only) ──
    # When failing a verse, reduce FSRS stability of more complex connected verses.
    # This makes them due sooner — the gap the memorize route's compute_fire_credit
    # handled but the unified module was missing.
    if item_type == "verse" and not is_success and rating >= 1 and rating < 3:
        _apply_verse_stability_penalty(conn, item_id, rating, same_type_conns)

    # ── Phase 2: Cross-domain propagation (via entity bridge) ──
    if item_type == "verse":
        # Verse reviewed → credit Hebrew concepts in that verse
        concepts = _get_verse_hebrew_concepts(conn, item_id)
        for concept_id, weight in concepts:
            boost = base_boost * weight * 0.2
            _apply_credit(conn, user_id, "hebrew_concept", concept_id,
                          boost, is_success,
                          source_type="verse", source_id=item_id)
            results["cross_domain_boosts"] += 1
            results["recipients"].append({
                "type": "hebrew_concept", "id": concept_id,
                "boost": round(boost, 4)
            })

        # Verse reviewed → credit learning modules
        modules = _get_verse_learning_modules(conn, item_id)
        for module_id, weight in modules:
            boost = base_boost * weight * LEARN_CREDIT_WEIGHT
            _apply_credit(conn, user_id, "learning_module", module_id,
                          boost, is_success,
                          source_type="verse", source_id=item_id)
            results["cross_domain_boosts"] += 1

    elif item_type == "hebrew_concept":
        # Hebrew concept reviewed → credit verses that use it
        verses = _get_concept_verses(conn, item_id)
        for verse_id, weight in verses:
            boost = base_boost * weight * 0.2
            _apply_credit(conn, user_id, "verse", verse_id,
                          boost, is_success,
                          source_type="hebrew_concept", source_id=item_id)
            results["cross_domain_boosts"] += 1

    elif item_type == "learning_module":
        # Module reviewed → credit verses in this module
        verses = _get_module_verses(conn, item_id)
        for verse_id, weight in verses:
            boost = base_boost * weight * LEARN_CREDIT_WEIGHT
            _apply_credit(conn, user_id, "verse", verse_id,
                          boost, is_success,
                          source_type="learning_module", source_id=item_id)
            results["cross_domain_boosts"] += 1

    conn.commit()
    return results


def get_fire_status(conn, item_type: str, item_id: str,
                    user_id: str = "default") -> dict:
    """Get current FIRe credit status for an item."""
    row = conn.execute(
        """SELECT credit, source_item_type, source_item_id, last_updated
           FROM fi_re_credits
           WHERE user_id = ? AND item_type = ? AND item_id = ?""",
        (user_id, item_type, item_id),
    ).fetchone()

    if row:
        return {
            "credit": round(row["credit"], 4),
            "knocked_out": row["credit"] >= KNOCKOUT_THRESHOLD,
            "source_type": row["source_item_type"],
            "source_id": row["source_item_id"],
            "last_updated": row["last_updated"],
        }
    return {"credit": 0.0, "knocked_out": False}


# ═══════════════════════════════════════════════════════════════════════
# Internal helpers
# ═══════════════════════════════════════════════════════════════════════

def _apply_credit(conn, user_id, item_type, item_id, boost, is_success,
                  source_type=None, source_id=None):
    """Apply a credit boost or penalty to an item."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    existing = conn.execute(
        "SELECT credit FROM fi_re_credits WHERE user_id=? AND item_type=? AND item_id=?",
        (user_id, item_type, item_id),
    ).fetchone()

    current = existing["credit"] if existing else 0.0

    if is_success:
        new_credit = min(KNOCKOUT_THRESHOLD, current + boost)
    else:
        new_credit = max(0.0, current - boost)

    conn.execute("""
        INSERT OR REPLACE INTO fi_re_credits
        (user_id, item_type, item_id, credit, last_updated, source_item_type, source_item_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, item_type, item_id, new_credit, now, source_type, source_id))


def _get_connection_count(conn, verse_id: str) -> int:
    """Count non-deprecated connections for a verse (complexity proxy)."""
    try:
        row = conn.execute("""
            SELECT COUNT(*) as c FROM connections
            WHERE (source_verse=? OR target_verse=?) AND deprecated=0
        """, (verse_id, verse_id)).fetchone()
        return row["c"] if row else 0
    except Exception:
        return 0


def _apply_verse_stability_penalty(conn, verse_id: str, rating: int,
                                    same_type_conns: list):
    """Reduce FSRS stability of more complex connected verses on failure.

    Penalty direction: simpler → complex.
    If you fail Gen 1:1, connected verses that are MORE complex
    (have MORE connections) get their stability reduced.

    Args:
        conn: DB connection
        verse_id: The verse that was reviewed
        rating: 1 (Again) or 2 (Hard)
        same_type_conns: list of (target_id, strength) from _get_same_type_connections
    """
    reviewed_count = _get_connection_count(conn, verse_id)

    penalty_factor = 1.0 if rating == 1 else 0.3  # Again=full, Hard=partial

    for target_id, strength in same_type_conns:
        if target_id == verse_id:
            continue

        # Check if connected verse is more complex
        target_count = _get_connection_count(conn, target_id)
        if target_count <= reviewed_count:
            continue  # Don't penalize simpler/equal verses

        # Calculate penalty from connection strength
        conn_strength = strength or 0.5
        penalty = min(0.5, conn_strength * penalty_factor * 0.5)
        if penalty < 0.01:
            continue

        # Reduce stability in memorize_progress table
        try:
            prog = conn.execute(
                "SELECT stability FROM memorize_progress WHERE user_id='default' AND verse_id=?",
                (target_id,)
            ).fetchone()
            if prog and prog["stability"]:
                new_stability = prog["stability"] / (1.0 + penalty)
                conn.execute(
                    "UPDATE memorize_progress SET stability=? WHERE user_id='default' AND verse_id=?",
                    (round(new_stability, 2), target_id)
                )

            # Also reduce fi_re_credit in memorize_progress
            credit_row = conn.execute(
                "SELECT fi_re_credit FROM memorize_progress WHERE user_id='default' AND verse_id=?",
                (target_id,)
            ).fetchone()
            if credit_row and credit_row["fi_re_credit"]:
                new_credit = max(0.0, credit_row["fi_re_credit"] - penalty)
                conn.execute(
                    "UPDATE memorize_progress SET fi_re_credit=? WHERE user_id='default' AND verse_id=?",
                    (round(new_credit, 3), target_id)
                )
        except Exception:
            continue


def _get_same_type_connections(conn, item_type: str, item_id: str) -> list:
    """Get same-type connected items with strength.

    For verses: use connections table.
    For hebrew_concepts: use hebrew_edges table.
    For learning_modules: use new module_connections table.
    """
    if item_type == "verse":
        try:
            rows = conn.execute("""
                SELECT CASE WHEN source_verse = ? THEN target_verse ELSE source_verse END as vid,
                       strength
                FROM connections
                WHERE (source_verse = ? OR target_verse = ?)
                  AND deprecated = 0 AND strength > 0.3
                ORDER BY strength DESC LIMIT 20
            """, (item_id, item_id, item_id)).fetchall()
            return [(r["vid"], r["strength"]) for r in rows]
        except Exception:
            return []

    elif item_type == "hebrew_concept":
        try:
            rows = conn.execute("""
                SELECT target_id as vid, strength
                FROM hebrew_edges
                WHERE source_id = ?
                UNION
                SELECT source_id as vid, strength
                FROM hebrew_edges
                WHERE target_id = ?
                ORDER BY strength DESC LIMIT 20
            """, (item_id, item_id)).fetchall()
            return [(r["vid"], r["strength"] or 0.5) for r in rows]
        except Exception:
            return []

    elif item_type == "learning_module":
        try:
            rows = conn.execute("""
                SELECT related_module_id as vid, 0.5 as strength
                FROM module_connections
                WHERE module_id = ?
                UNION
                SELECT module_id as vid, 0.5 as strength
                FROM module_connections
                WHERE related_module_id = ?
                LIMIT 10
            """, (item_id, item_id)).fetchall()
            return [(r["vid"], r["strength"]) for r in rows]
        except Exception:
            return []

    return []


def _get_verse_hebrew_concepts(conn, verse_id: str) -> list:
    """Find Hebrew concepts that appear in a verse.

    Uses entity_verse_bridge if available, falls back to matching
    verse_entities + entity_links lookup.
    """
    # Try bridge table first
    try:
        rows = conn.execute("""
            SELECT item_id, weight FROM entity_verse_bridge
            WHERE item_type = 'hebrew_concept' AND verse_id = ?
        """, (verse_id,)).fetchall()
        if rows:
            return [(r["item_id"], r["weight"]) for r in rows]
    except Exception:
        pass

    # Fallback: match via verse_entities → entity_links where type is concept
    try:
        rows = conn.execute("""
            SELECT DISTINCT ve.entity_id, 0.5 as weight
            FROM verse_entities ve
            JOIN entity_links el ON el.entity_id = ve.entity_id
            WHERE ve.verse_id = ? AND el.entity_type IN ('concept', 'person', 'place')
            LIMIT 20
        """, (verse_id,)).fetchall()
        return [(r["entity_id"], r["weight"]) for r in rows]
    except Exception:
        return []


def _get_concept_verses(conn, concept_id: str) -> list:
    """Find verses that contain a Hebrew concept."""
    try:
        rows = conn.execute("""
            SELECT verse_id, confidence as weight FROM verse_entities
            WHERE entity_id = ? AND confidence >= 0.3
            LIMIT 20
        """, (concept_id,)).fetchall()
        return [(r["verse_id"], r["weight"]) for r in rows]
    except Exception:
        return []


def _get_verse_learning_modules(conn, verse_id: str) -> list:
    """Find learning modules that reference a verse."""
    try:
        rows = conn.execute("""
            SELECT lm.id as module_id, 0.5 as weight
            FROM learning_modules lm
            JOIN module_questions mq ON mq.module_id = lm.id
            WHERE mq.verse_id = ?
            LIMIT 10
        """, (verse_id,)).fetchall()
        return [(r["module_id"], r["weight"]) for r in rows]
    except Exception:
        return []


def _get_module_verses(conn, module_id: str) -> list:
    """Find verses referenced by a learning module."""
    try:
        rows = conn.execute("""
            SELECT DISTINCT verse_id, 0.5 as weight
            FROM module_questions
            WHERE module_id = ? AND verse_id IS NOT NULL
            LIMIT 20
        """, (module_id,)).fetchall()
        return [(r["verse_id"], r["weight"]) for r in rows]
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════════════
# Cross-domain bridge builder
# ═══════════════════════════════════════════════════════════════════════

def build_entity_verse_bridge(conn):
    """Build the entity_verse_bridge table from existing data.

    Maps Hebrew concepts to verses where they appear using the
    gematria table (word-level) and lexicon entries.
    """
    ensure_fire_schema(conn)
    conn.execute("DELETE FROM entity_verse_bridge")
    count = 0

    # Map from gematria entries → lexicon → concepts
    try:
        rows = conn.execute("""
            SELECT DISTINCT g.verse_id, l.lemma
            FROM gematria g
            JOIN lexicon l ON l.hebrew_plain = g.hebrew_plain
            WHERE l.lemma IS NOT NULL
            LIMIT 5000
        """).fetchall()
    except Exception:
        rows = []

    for r in rows:
        conn.execute("""
            INSERT OR IGNORE INTO entity_verse_bridge
            (item_type, item_id, verse_id, weight)
            VALUES ('hebrew_concept', ?, ?, 0.5)
        """, (r["lemma"], r["verse_id"]))
        count += 1

    conn.commit()
    return {"bridges_created": count}
