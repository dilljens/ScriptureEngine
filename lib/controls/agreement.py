"""Inter-source agreement scoring.

When multiple independent sources find the same connection between a verse
pair, the confidence should be higher than any single source alone.
This is the "multiple attestation" principle from textual criticism.

Sources are considered "independent" if they have different discovered_by
values. Same source type from different runs is NOT independent.
"""


def count_independent_sources(conn, verse_a, verse_b, conn_type=None, layer=None):
    """Count distinct discovery methods for the same verse-pair.
    
    Returns the number of independent sources that found this connection.
    """
    if not conn:
        return 0
    
    try:
        if conn_type and layer:
            cursor = conn.execute(
                """SELECT COUNT(DISTINCT discovered_by)
                   FROM connections
                   WHERE ((source_verse=? AND target_verse=?)
                          OR (source_verse=? AND target_verse=?))
                   AND type=? AND layer=?
                   AND deprecated=0""",
                (verse_a, verse_b, verse_b, verse_a, conn_type, layer),
            )
        else:
            cursor = conn.execute(
                """SELECT COUNT(DISTINCT discovered_by)
                   FROM connections
                   WHERE ((source_verse=? AND target_verse=?)
                          OR (source_verse=? AND target_verse=?))
                   AND deprecated=0""",
                (verse_a, verse_b, verse_b, verse_a),
            )
        return cursor.fetchone()[0]
    except Exception:
        return 0


def agreement_multiplier(source_count):
    """Compute a likelihood ratio multiplier from independent source count.
    
    Each additional independent source makes a real connection more likely
    (and a spurious one less likely). The multiplier follows:
      - 1 source: 1.0× (baseline — no agreement to measure)
      - 2 sources: 1.5× (two independent methods agree — notable)
      - 3 sources: 2.5× (three methods — strong corroboration)
      - 4+ sources: 3.0× (comprehensive agreement)
    """
    if source_count <= 1:
        return 1.0
    elif source_count == 2:
        return 1.5
    elif source_count == 3:
        return 2.5
    elif source_count >= 4:
        return 3.0
    return 1.0


def agreement_boost(confidence, source_count):
    """Apply a simple multiplicative boost to confidence based on agreement.
    
    This is a lighter-weight alternative to the likelihood ratio approach,
    useful for bulk operations where you don't want to re-run the full
    Bayesian ensemble.
    
    Returns boosted confidence capped at 0.99.
    """
    mult = agreement_multiplier(source_count)
    return min(confidence * mult, 0.99)
