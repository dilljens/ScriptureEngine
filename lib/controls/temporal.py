"""Temporal decay and revalidation for connection confidence.

Connections lose confidence over time — algorithmic discoveries decay faster
than human scholarship, and text-explicit connections don't decay at all.

Keeps the graph honest: old algorithmic connections get flagged for
periodic revalidation instead of persisting at original confidence forever.
"""

from datetime import datetime, timezone

# Half-life in years per discovery method
TEMPORAL_DECAY_HALF_LIFE = {
    "algorithm": 2.0,           # Algorithmic: 2 years — recheck often
    "shared_verse_overlap": 2.0,
    "shem_hamephorash_scanner": 2.5,
    "llm": 1.5,                 # LLM-generated: 18 months — fast decay
    "ai": 1.5,
    "sefaria_api": 3.0,         # Sefaria links: moderate decay
    "lds_topical_guide": 4.0,   # Curated guides: slower
    "bible_dictionary": 5.0,
    "human": 5.0,               # Human scholarship: 5 years
    "tsk": 20.0,                # Historical: very slow decay
    "script": 30.0,             # Scriptural: very slow
    "text": None,                # Text-explicit: never decays
}


def half_life_for(discovered_by):
    """Get half-life in years for a discovery method."""
    db = (discovered_by or "algorithm").lower().strip()
    if db == "ai":
        db = "llm"
    return TEMPORAL_DECAY_HALF_LIFE.get(db, 2.0)


def years_elapsed(created_at):
    """Calculate years between created_at and now."""
    if not created_at:
        return 0
    try:
        created = datetime.strptime(str(created_at)[:10], "%Y-%m-%d")
        now = datetime.now()
        return (now - created).days / 365.0
    except (ValueError, TypeError):
        return 0


def apply_temporal_decay(confidence, discovered_by, created_at):
    """Apply exponential decay to confidence based on elapsed time.
    
    Uses half-life model: confidence_decayed = confidence × 0.5^(years/half_life)
    Text-explicit connections (half_life=None) never decay.
    
    Args:
        confidence: original 0.0-1.0 confidence
        discovered_by: discovery method string
        created_at: date string or datetime
    
    Returns:
        Decayed confidence value.
    """
    hl = half_life_for(discovered_by)
    if hl is None:
        return confidence  # Never decays
    
    elapsed = years_elapsed(created_at)
    if elapsed <= 0:
        return confidence
    
    decay_factor = 0.5 ** (elapsed / hl)
    return round(confidence * decay_factor, 3)


def get_staleness(created_at, discovered_by):
    """Classify connection staleness.
    
    Returns one of: 'fresh', 'aging', 'stale', 'critical'
    """
    hl = half_life_for(discovered_by)
    if hl is None:
        return "fresh"  # Text never stales
    
    elapsed = years_elapsed(created_at)
    
    if elapsed < hl * 0.5:
        return "fresh"
    elif elapsed < hl:
        return "aging"
    elif elapsed < hl * 2:
        return "stale"
    else:
        return "critical"


def needs_revalidation(created_at, discovered_by, threshold=0.3):
    """Check if a connection falls below the confidence threshold after decay.
    
    Returns True if the connection's decayed confidence would be below threshold.
    """
    # We check if even full original confidence would decay below threshold
    elapsed = years_elapsed(created_at)
    if elapsed <= 0:
        return False
    
    hl = half_life_for(discovered_by)
    if hl is None:
        return False  # Text never needs revalidation
    
    # Original confidence 1.0 would decay to...
    max_decayed = 1.0 * (0.5 ** (elapsed / hl))
    return max_decayed < threshold


def revalidate_connection_row(row):
    """Apply temporal decay to a connection dict.
    
    Returns updated dict with decayed confidence and staleness info.
    """
    confidence = row.get("confidence", 0.5) or 0.5
    discovered_by = row.get("discovered_by", "algorithm")
    created_at = row.get("created_at", None)
    last_validated = row.get("last_validated", None)
    
    decayed = apply_temporal_decay(confidence, discovered_by, created_at)
    staleness = get_staleness(created_at, discovered_by)
    
    return {
        "original_confidence": confidence,
        "decayed_confidence": decayed,
        "staleness": staleness,
        "years_elapsed": round(years_elapsed(created_at), 2),
        "half_life_years": half_life_for(discovered_by),
        "needs_revalidation": needs_revalidation(created_at, discovered_by),
        "last_validated": last_validated,
    }
