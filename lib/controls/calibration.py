"""Connection quality calibration — the standard rubric.

Every connection gets a quality level based on statistical evidence.
This is the user-facing confidence metric.
"""

# Quality level definitions
QUALITY_LEVELS = {
    "verified": {
        "rank": 0,
        "label": "Verified",
        "description": "Confirmed by multiple independent methods, passes null-text controls",
        "color": "#2E7D32",  # Dark green
        "emoji": "🔒",
        "min_p_value": 0.001,
        "min_effect_size": 1.0,
        "requires_cross_validation": True,
        "requires_preregistration": False,
    },
    "strong": {
        "rank": 1,
        "label": "Strong",
        "description": "High statistical significance, passes null-text controls",
        "color": "#4CAF50",  # Green
        "emoji": "✅",
        "min_p_value": 0.01,
        "min_effect_size": 0.6,
        "requires_cross_validation": False,
        "requires_preregistration": False,
    },
    "probable": {
        "rank": 2,
        "label": "Probable",
        "description": "Statistically significant, null-text control passed",
        "color": "#FF9800",  # Orange
        "emoji": "📊",
        "min_p_value": 0.05,
        "min_effect_size": 0.3,
        "requires_cross_validation": False,
        "requires_preregistration": False,
    },
    "suggested": {
        "rank": 3,
        "label": "Suggested",
        "description": "Detected by algorithm, not yet null-tested",
        "color": "#9E9E9E",  # Gray
        "emoji": "💡",
        "min_p_value": None,
        "min_effect_size": None,
        "requires_cross_validation": False,
        "requires_preregistration": False,
    },
    "speculative": {
        "rank": 4,
        "label": "Speculative",
        "description": "AI-proposed or weak signal, needs verification",
        "color": "#E91E63",  # Pink
        "emoji": "❓",
        "min_p_value": None,
        "min_effect_size": None,
        "requires_cross_validation": False,
        "requires_preregistration": False,
    },
    "rejected": {
        "rank": 5,
        "label": "Rejected",
        "description": "Failed null-text controls or contradicted by evidence",
        "color": "#B71C1C",  # Dark red
        "emoji": "❌",
        "min_p_value": None,
        "min_effect_size": None,
        "requires_cross_validation": False,
        "requires_preregistration": False,
    },
}


def calibrate_connection(p_value, effect_size, preregistered=0, cross_validated=0):
    """Determine quality level from statistical evidence.
    
    Args:
        p_value: probability of observing this pattern by chance
        effect_size: Cohen's d
        preregistered: 1 if method was pre-registered
        cross_validated: 1 if independently confirmed
    
    Returns:
        (quality_level, confidence_score)
    """
    # Rejected: no significance
    if p_value is None or p_value >= 0.10:
        return "speculative", 0.3
    
    # Check each level from highest to lowest
    for level_name, level in sorted(QUALITY_LEVELS.items(), key=lambda x: x[1]["rank"]):
        if level_name in ("speculative", "rejected"):
            continue
        
        min_p = level.get("min_p_value")
        min_es = level.get("min_effect_size")
        
        p_pass = min_p is None or p_value < min_p
        es_pass = min_es is None or effect_size >= min_es
        cv_pass = not level.get("requires_cross_validation", False) or cross_validated
        
        if p_pass and es_pass and cv_pass:
            # Compute confidence score for this level
            p_score = max(0, (0.05 - p_value) / 0.05) if p_value < 0.05 else 0
            es_score = min(effect_size / 2.0, 1.0)
            reg_score = 0.1 if preregistered else 0.0
            cv_score = 0.15 if cross_validated else 0.0
            
            base = {
                "verified": 0.85,
                "strong": 0.75,
                "probable": 0.60,
                "suggested": 0.45,
                "speculative": 0.25,
                "rejected": 0.0,
            }.get(level_name, 0.3)
            
            confidence = min(0.99, base + p_score * 0.1 + es_score * 0.1 + reg_score + cv_score)
            return level_name, round(confidence, 2)
    
    return "suggested", 0.45


def get_quality_color(quality_level):
    """Get display color for a quality level."""
    return QUALITY_LEVELS.get(quality_level, {}).get("color", "#999")


def get_quality_emoji(quality_level):
    """Get display emoji for a quality level."""
    return QUALITY_LEVELS.get(quality_level, {}).get("emoji", "❓")


def describe_quality(quality_level):
    """Get full description text."""
    return QUALITY_LEVELS.get(quality_level, {}).get("description", "")
