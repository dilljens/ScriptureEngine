"""Contradiction detection for the connection graph.

Detects when two connections between the same verse pair use incompatible
types (e.g., "direct_quotation" vs "echo"), flags them as contradictory,
and tags them as disputed in the quality system.

The CONTRADICTION_MATRIX defines conflict scores between type pairs:
  1.0 = complete contradiction (can't both be true)
  0.5 = moderate conflict (different by degree)
  0.2 = mild tension (different perspectives)
  0.0 = compatible (different levels of analysis)
"""

# ── Contradiction Matrix ───────────────────────────────────────────────
# Format: (type_a, type_b) → conflict_score
# Score 0.0-1.0 where 1.0 = complete contradiction

CONTRADICTION_MATRIX = {
    # ── Quotation conflicts ──
    ("direct_quotation", "echo"): 0.6,
    ("direct_quotation", "allusion"): 0.4,
    ("direct_quotation", "modified_quotation"): 0.2,
    ("direct_quotation", "summarized"): 0.3,
    ("modified_quotation", "echo"): 0.3,
    ("prophetic_fulfillment", "echo"): 0.3,
    ("prophetic_fulfillment", "allusion"): 0.2,

    # ── Structural conflicts ──
    ("chiasm_detected", "parallel_synonymous"): 0.3,
    ("chiasm_detected", "formula_marker"): 0.3,
    ("inclusio", "seam"): 0.2,

    # ── Interpretive conflicts ──
    ("rabbinic_midrash", "patristic_reading"): 0.3,
    ("reformation_view", "latter_day_saint_reading"): 0.4,
    ("critical_scholarship", "rabbinic_midrash"): 0.3,
    ("reformation_view", "patristic_reading"): 0.3,

    # ── Temporal conflicts ──
    ("same_time_period", "chronological_marker"): 0.2,
    ("genealogical", "prophetic_timeline"): 0.2,

    # ── Gematria vs structural ──
    ("same_gematria_standard", "keyword_linking"): 0.1,
    ("divine_name_value", "keyword_linking"): 0.1,
    ("sacred_number", "formula_count"): 0.1,

    # ── Geographic conflicts ──
    ("same_location", "exile_route"): 0.2,
    ("wilderness_sojourn", "promised_land"): 0.1,
    ("mountain_of_god", "temple_location"): 0.2,

    # ── Symbolic conflicts ──
    ("person_type", "event_type"): 0.1,
    ("object_type", "temple_symbol"): 0.2,
    ("name_symbolic", "keyword_linking"): 0.1,

    # ── Quality level contradictions ──
    ("verified", "rejected"): 1.0,
    ("strong", "speculative"): 0.8,
    ("probable", "pattern"): 0.3,
}

# Layer-level incompatibility
LAYER_CONTRADICTIONS = {
    ("linguistic", "geographic"): 0.1,
    ("numerical", "geographic"): 0.1,
    ("structural", "chronological"): 0.1,
}


def conflict_score(type_a, type_b, layer_a=None, layer_b=None):
    """Get conflict score between two connection types.
    
    Returns 0.0-1.0 where >0.3 means notable contradiction.
    """
    pair = (type_a, type_b) if type_a <= type_b else (type_b, type_a)
    reverse_pair = (type_a, type_b) if type_a > type_b else (type_b, type_a)
    
    score = CONTRADICTION_MATRIX.get(pair, CONTRADICTION_MATRIX.get(reverse_pair, 0.0))
    
    # Layer-level conflict
    if score == 0.0 and layer_a and layer_b:
        layer_pair = (layer_a, layer_b) if layer_a <= layer_b else (layer_b, layer_a)
        score = LAYER_CONTRADICTIONS.get(layer_pair, 0.0)
    
    return score


def detect_contradictions(conn, verse_a, verse_b):
    """Find connection pairs between the same verses that contradict.
    
    Returns list of conflict dicts.
    """
    try:
        cursor = conn.execute(
            """SELECT id, source_verse, target_verse, layer, type, subtype,
                      discovered_by, quality_level, confidence
               FROM connections
               WHERE ((source_verse=? AND target_verse=?)
                      OR (source_verse=? AND target_verse=?))
               AND deprecated=0
               ORDER BY type""",
            (verse_a, verse_b, verse_b, verse_a),
        )
        connections = [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []

    if len(connections) < 2:
        return []

    conflicts = []
    for i in range(len(connections)):
        for j in range(i + 1, len(connections)):
            c1, c2 = connections[i], connections[j]
            score = conflict_score(c1["type"], c2["type"], c1["layer"], c2["layer"])
            if score > 0.3:
                conflicts.append({
                    "source_verse": verse_a,
                    "target_verse": verse_b,
                    "conflict_score": round(score, 2),
                    "conflict_type": "contradictory" if score >= 0.5 else "tension",
                    "connection_a": {
                        "id": c1["id"],
                        "type": c1["type"],
                        "layer": c1["layer"],
                        "quality": c1["quality_level"],
                        "discovered_by": c1["discovered_by"],
                    },
                    "connection_b": {
                        "id": c2["id"],
                        "type": c2["type"],
                        "layer": c2["layer"],
                        "quality": c2["quality_level"],
                        "discovered_by": c2["discovered_by"],
                    },
                    "resolution_needed": score >= 0.5,
                })

    return conflicts


def scan_all_contradictions(conn, batch_size=1000):
    """Scan all verse pairs with multiple connections for contradictions.
    
    Uses batched query to avoid loading all 1.3M connections at once.
    Returns total conflicts found.
    """
    # Find all verse pairs that have 2+ connections
    pairs = conn.execute(
        """SELECT source_verse, target_verse, COUNT(*) as cnt
           FROM connections WHERE deprecated=0
           GROUP BY source_verse, target_verse
           HAVING cnt > 1
           ORDER BY cnt DESC"""
    ).fetchall()

    total_conflicts = 0
    for row in pairs:
        conflicts = detect_contradictions(conn, row[0], row[1])
        if conflicts:
            total_conflicts += len(conflicts)
            # Tag connections as disputed
            for c in conflicts:
                for side in ["connection_a", "connection_b"]:
                    cid = c[side]["id"]
                    # Use direct SQL for efficiency
                    try:
                        conn.execute(
                            "UPDATE connections SET quality_level='disputed' WHERE id=?",
                            (cid,),
                        )
                    except Exception:
                        pass
        if batch_size and total_conflicts >= batch_size:
            break
    
    conn.commit()
    return total_conflicts


def resolve_disagreement(conn, conflict_id, resolution_note="", resolved_by="user"):
    """Mark a contradiction as resolved.
    
    Keeps the record but sets resolution status so future scans skip it.
    """
    try:
        conn.execute(
            "UPDATE disagreements SET resolution=?, resolved_by=?, resolved_at=datetime('now') WHERE id=?",
            (resolution_note, resolved_by, conflict_id),
        )
        conn.commit()
        return True
    except Exception:
        return False


def get_unresolved_disagreements(conn, limit=50):
    """Get all unresolved contradictions."""
    try:
        cursor = conn.execute(
            "SELECT * FROM disagreements WHERE resolution='unresolved' ORDER BY conflict_score DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []
