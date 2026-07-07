"""Connection quality calibration - multi-signal rating system.

Every connection gets evaluated on multiple independent axes so users
can see WHY a rating is what it is and apply their own trust criteria.

The rating considers 5 signals:
  - discovered_by:  who found this connection (text, tsk, llm, algorithm)
  - connection_type: what kind of connection (direct_quotation, etc.)
  - has_reasoning:  whether human-readable explanation exists
  - confidence:     the existing 0.0-1.0 statistical confidence
  - confirmation_count: how many users/agents have confirmed it
"""


def star_display(n):
    """Return star string - e.g. star_display(4) = '**** ' (partially filled)"""
    filled = "\u2605" * n
    empty = "\u2606" * (5 - n)
    return filled + empty


# Discovery method trust weights
DISCOVERY_WEIGHTS = {
    "text": 1.0,
    "tsk": 0.85,
    "llm": 0.75,
    "ai": 0.75,
    "human": 0.80,
    "algorithm": 0.35,
}

DISCOVERY_LABELS = {
    "text": "Text-Explicit - the text itself makes this connection",
    "tsk": "Historical Cross-Reference - compiled by Treasury of Scripture Knowledge scholars",
    "llm": "Agent-Driven - a person read both verses and judged the connection",
    "ai": "Agent-Driven - a person read both verses and judged the connection",
    "human": "Human-Curated - explicitly documented by a scholar",
    "algorithm": "Algorithmic - machine-detected pattern, not verified",
}


def _tw(conn_type):
    """Look up type weight from TYPE_WEIGHTS dict."""
    w = TYPE_WEIGHTS.get(conn_type, 0.5)
    return w


TYPE_WEIGHTS = {
    "direct_quotation": 1.0,
    "prophetic_fulfillment": 0.95,
    "modified_quotation": 0.9,
    "type_antitype": 0.85,
    "midrashic_connection": 0.85,
    "inspired_revision": 0.85,
    "lectio_divina": 0.7,
    "nomen_est_omen": 0.7,
    "wordplay": 0.7,
    "cognate": 0.65,
    "semantic_domain": 0.65,
    "summarized": 0.7,
    "prophetic_quote": 0.7,
    "apocalyptic_time": 0.65,
    "textual_variant": 0.8,
    "vulgate_variant": 0.8,
    "jst_change": 0.8,
    "dead_sea_scrolls_variant": 0.8,
    "peshitta_variant": 0.8,
    "septuagint_difference": 0.8,
    "quotation_variant": 0.8,
    "chiastic": 0.6,
    "parallel_synonymous": 0.5,
    "parallel_antithetic": 0.5,
    "parallel_synthetic": 0.5,
    "parallel_step": 0.5,
    "inclusio": 0.6,
    "acrostic": 0.7,
    "chiasm_detected": 0.4,
    "refrain": 0.5,
    "formula_marker": 0.55,
    "keyword_linking": 0.45,
    "seam": 0.45,
    "emblematic_parallelism": 0.55,
    "numerical_parallelism": 0.5,
    "merismus": 0.5,
    "rhetorical_pair": 0.5,
    "same_lemma": 0.5,
    "same_root": 0.45,
    "same_morphology": 0.35,
    "hendiadys": 0.5,
    "semuchin": 0.4,
    "allusion": 0.65,
    "echo": 0.35,
    "same_gematria_standard": 0.35,
    "same_gematria_ordinal": 0.3,
    "same_gematria_reduced": 0.3,
    "divine_name_value": 0.4,
    "gematria_sum_relationship": 0.35,
    "gematria_factor": 0.35,
    "sacred_number": 0.3,
    "verse_gematria_total": 0.35,
    "divine_name_distribution": 0.3,
    "formula_count": 0.3,
    "7_fold_pattern": 0.25,
    "10_fold_pattern": 0.25,
    "12_fold_pattern": 0.25,
    "40_fold_pattern": 0.25,
    "hapax_legomenon": 0.4,
    "dislegomenon": 0.4,
    "concentration_index": 0.3,
    "key_word_count": 0.3,
    "repetition_pattern": 0.3,
    "same_location": 0.45,
    "journey_path": 0.4,
    "wilderness_sojourn": 0.4,
    "exile_route": 0.4,
    "promised_land": 0.45,
    "mountain_of_god": 0.45,
    "temple_location": 0.5,
    "garden_presence": 0.5,
    "same_time_period": 0.4,
    "genealogical": 0.5,
    "prophetic_timeline": 0.5,
    "sabbatical_cycle": 0.35,
    "jubilee_cycle": 0.35,
    "dispensation": 0.5,
    "chronological_marker": 0.4,
    "feast_connection": 0.55,
    "shared_symbol": 0.5,
    "apocalyptic_creature": 0.4,
    "apocalyptic_object": 0.4,
    "apocalyptic_event": 0.4,
    "person_type": 0.5,
    "event_type": 0.5,
    "institution_type": 0.5,
    "object_type": 0.5,
    "name_symbolic": 0.6,
    "temple_symbol": 0.5,
    "rabbinic_midrash": 0.45,
    "patristic_reading": 0.4,
    "reformation_view": 0.35,
    "giliadi_pattern": 0.35,
    "latter_day_saint_reading": 0.45,
    "critical_scholarship": 0.35,
}


def rate_connection(discovered_by="algorithm", connection_type="", has_reasoning=False, confidence=0.5, confirmation_count=0):
    """Compute a multi-signal rating for a connection.

    Returns a dict with all signals broken out so the API can surface them.

    Args:
        discovered_by: 'text', 'tsk', 'llm', 'ai', 'human', or 'algorithm'
        connection_type: the type field (direct_quotation, same_lemma, etc.)
        has_reasoning: bool - does the metadata have a reasoning field?
        confidence: the existing 0.0-1.0 statistical confidence
        confirmation_count: how many confirmations (0 = none)

    Returns:
        dict with signals breakdown including star rating
    """
    db = discovered_by.lower().strip() if discovered_by else "algorithm"
    if db == "ai":
        db = "llm"

    discovery_weight = DISCOVERY_WEIGHTS.get(db, 0.35)
    discovery_label = DISCOVERY_LABELS.get(db, DISCOVERY_LABELS["algorithm"])

    type_weight = _tw(connection_type)

    reasoning_bonus = 0.15 if has_reasoning else 0.0
    confirm_bonus = min(confirmation_count * 0.05, 0.15) if confirmation_count > 0 else 0.0

    raw = (discovery_weight * 0.40 + type_weight * 0.30 + confidence * 0.15 +
           reasoning_bonus * 0.10 + confirm_bonus * 0.05)

    overall = max(0.0, min(1.0, raw))

    if overall >= 0.85:
        tier = "verified"
        tier_label = "Text-Explicit"
        tier_description = "The text itself makes this connection - explicit quotation or direct statement"
        stars = 5
        color = "#1B5E20"
    elif overall >= 0.70:
        tier = "strong"
        tier_label = "Well-Established"
        tier_description = "Strong scholarly or human consensus with clear reasoning"
        stars = 4
        color = "#2E7D32"
    elif overall >= 0.50:
        tier = "probable"
        tier_label = "Probable"
        tier_description = "Reasonable connection with some support or reasoning"
        stars = 3
        color = "#F57C00"
    elif overall >= 0.28:
        tier = "suggested"
        tier_label = "Suggested"
        tier_description = "Algorithmic pattern, not yet verified - use with discernment"
        stars = 2
        color = "#757575"
    else:
        tier = "pattern"
        tier_label = "Pattern Only"
        tier_description = "Statistical artifact or theoretical - significance is uncertain"
        stars = 1
        color = "#9E9E9E"

    return {
        "overall_confidence": round(overall, 3),
        "stars": stars,
        "max_stars": 5,
        "star_display": star_display(stars),
        "tier": tier,
        "tier_label": tier_label,
        "tier_description": tier_description,
        "tier_color": color,
        "signals": {
            "discovery_method": db,
            "discovery_explanation": discovery_label,
            "connection_type": connection_type,
            "type_weight": round(type_weight, 3),
            "has_reasoning": has_reasoning,
            "statistical_confidence": round(confidence, 3),
            "confirmation_count": confirmation_count,
        }
    }


def rate_connection_row(row):
    """Pass a connection dict (from DB or passage guide) and get signals."""
    discovered_by = row.get("discovered_by", "algorithm")
    connection_type = row.get("type", "")

    metadata = row.get("metadata", "{}")
    if isinstance(metadata, str):
        import json
        try:
            meta = json.loads(metadata)
            has_reasoning = bool(meta.get("reasoning"))
        except (json.JSONDecodeError, TypeError):
            has_reasoning = False
    elif isinstance(metadata, dict):
        has_reasoning = bool(metadata.get("reasoning"))
    else:
        has_reasoning = False

    confidence = row.get("confidence", 0.5) or 0.5
    confirmation_count = row.get("confirmation_count", 0) or 0

    return rate_connection(
        discovered_by=discovered_by,
        connection_type=connection_type,
        has_reasoning=has_reasoning,
        confidence=confidence,
        confirmation_count=confirmation_count,
    )


def enrich_connection(conn_dict):
    """Add signal breakdown to a connection dict from passage guides."""
    row = {
        "discovered_by": conn_dict.get("discovered_by", "algorithm"),
        "type": conn_dict.get("type", ""),
        "confidence": conn_dict.get("confidence", 0.5),
        "confirmation_count": conn_dict.get("confirmation_count", 0),
        "metadata": conn_dict.get("metadata", "{}"),
    }
    signals = rate_connection_row(row)
    conn_dict["signals"] = signals
    conn_dict["quality_label"] = signals["tier_label"]
    conn_dict["star_display"] = signals["star_display"]
    return conn_dict


def calibrate_connection(p_value, effect_size, preregistered=0, cross_validated=0):
    """Legacy: determine quality level from statistical evidence alone.

    Kept for backward compatibility with validate_connections.py.
    Uses the new multi-signal system behind the scenes.
    """
    if preregistered:
        db = "human"
    elif cross_validated:
        db = "tsk"
    else:
        db = "algorithm"

    result = rate_connection(
        discovered_by=db,
        connection_type="",
        has_reasoning=False,
        confidence=0.5,
        confirmation_count=0,
    )

    return result["tier"], round(result["overall_confidence"], 2)


QUALITY_LEVELS = {
    "verified": {"rank": 0, "label": "Text-Explicit", "stars": 5, "color": "#1B5E20",
        "description": "The text itself makes this connection - explicit quotation or direct statement"},
    "strong": {"rank": 1, "label": "Well-Established", "stars": 4, "color": "#2E7D32",
        "description": "Strong scholarly or human consensus with clear reasoning"},
    "probable": {"rank": 2, "label": "Probable", "stars": 3, "color": "#F57C00",
        "description": "Reasonable connection with some support or reasoning"},
    "suggested": {"rank": 3, "label": "Suggested", "stars": 2, "color": "#757575",
        "description": "Algorithmic pattern, not yet verified"},
    "pattern": {"rank": 4, "label": "Pattern Only", "stars": 1, "color": "#9E9E9E",
        "description": "Statistical artifact or theoretical - significance is uncertain"},
    "speculative": {"rank": 4, "label": "Speculative", "stars": 1, "color": "#E91E63",
        "description": "Weak signal, needs verification"},
    "rejected": {"rank": 5, "label": "Rejected", "stars": 0, "color": "#B71C1C",
        "description": "Contradicted by evidence"},
}


def get_quality_color(quality_level):
    return QUALITY_LEVELS.get(quality_level, {}).get("color", "#999")


def get_quality_stars(quality_level):
    return QUALITY_LEVELS.get(quality_level, {}).get("stars", 0)


def describe_quality(quality_level):
    return QUALITY_LEVELS.get(quality_level, {}).get("description", "")
