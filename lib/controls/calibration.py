"""Connection quality calibration — Bayesian ensemble rating system.

Every connection gets evaluated using likelihood ratio products instead of
a linear weighted sum. This naturally handles:
  - Multiple weak signals stacking into strong evidence
  - One strong signal being sufficient alone
  - Contradictory signals producing confidence < 0.5
  - Inter-source agreement as a natural Bayes factor

The rating considers 5 signal groups:
  - discovered_by:  who found this connection (text, tsk, llm, algorithm)
  - connection_type: what kind of connection (direct_quotation, etc.)
  - has_reasoning:  whether human-readable explanation exists
  - statistical:     p-value range, effect size from null-text controls
  - confirmation:    weighted agreement from multiple sources
"""


# ── Likelihood Ratios (Bayes factors) ──────────────────────────────────
# Each signal maps to a likelihood ratio: P(signal | real) / P(signal | chance)
# LR > 1 means the signal makes a real connection more likely
# LR < 1 means the signal makes a chance connection more likely

DISCOVERY_LR = {
    "text": 20.0,       # Text-explicit: 20x more likely for real connections
    "tsk": 10.0,         # Historical cross-reference: strong scholarly tradition
    "script": 8.0,       # Explicit scriptural connection
    "human": 6.0,        # Human-curated: scholar documented it
    "llm": 3.0,          # LLM-assisted: good pattern recognition, some noise
    "ai": 3.0,           # Same as llm
    "sefaria_api": 2.5,  # Sefaria links: rabbinic tradition references
    "lds_topical_guide": 2.0,  # LDS topical guide: curated but tradition-specific
    "shem_hamephorash_scanner": 1.5,  # Specialized scanner
    "algorithm": 1.5,    # Automated: weak on its own, stacks with others
    "bible_dictionary": 2.0,  # Bible dictionary entry
    "shared_verse_overlap": 1.2,  # Statistical overlap
}

DISCOVERY_LABELS = {
    "text": "Text-Explicit — the text itself makes this connection",
    "tsk": "Historical Cross-Reference — Treasury of Scripture Knowledge",
    "script": "Scriptural Connection — explicitly cross-referenced",
    "human": "Human-Curated — documented by a scholar",
    "llm": "LLM-Assisted — AI-identified, human-verified pattern",
    "ai": "LLM-Assisted — AI-identified, human-verified pattern",
    "sefaria_api": "Sefaria Links — rabbinic tradition cross-references",
    "lds_topical_guide": "LDS Topical Guide — tradition-specific curated links",
    "shem_hamephorash_scanner": "Shem HaMephorash Scanner — 72-name encoding pattern",
    "algorithm": "Algorithmic — machine-detected, not verified",
    "bible_dictionary": "Bible Dictionary — curated reference entry",
    "shared_verse_overlap": "Shared Verse Overlap — statistical co-occurrence",
}

# Source tier classification (S0 = most authoritative)
DISCOVERY_TIER = {
    "text": 0,
    "script": 0,
    "tsk": 1,
    "human": 2,
    "sefaria_api": 2,
    "lds_topical_guide": 2,
    "bible_dictionary": 2,
    "llm": 3,
    "ai": 3,
    "shem_hamephorash_scanner": 3,
    "algorithm": 4,
    "shared_verse_overlap": 4,
}

TIER_LABELS = {
    0: "S0 — Canonical Text",
    1: "S1 — Primary Tradition",
    2: "S2 — Scholarly Consensus",
    3: "S3 — AI-Assisted",
    4: "S4 — Algorithmic",
}


def _type_lr(conn_type):
    """Look up type likelihood ratio from TYPE_LR dict."""
    return TYPE_LR.get(conn_type, 1.5)


TYPE_LR = {
    # ── Explicit textual connections ──
    "direct_quotation": 8.0,
    "prophetic_fulfillment": 6.0,
    "inspired_revision": 5.0,
    "modified_quotation": 5.0,
    "type_antitype": 4.0,
    "midrashic_connection": 3.0,
    "lectio_divina": 2.5,
    "nomen_est_omen": 2.5,
    "wordplay": 2.0,
    "cognate": 2.0,
    "semantic_domain": 2.0,
    "summarized": 2.5,
    "prophetic_quote": 3.0,
    "apocalyptic_time": 2.0,
    # ── Textual variants ──
    "textual_variant": 3.0,
    "vulgate_variant": 2.5,
    "jst_change": 3.0,
    "dead_sea_scrolls_variant": 3.0,
    "peshitta_variant": 2.5,
    "septuagint_difference": 2.5,
    "quotation_variant": 3.0,
    # ── Structural patterns ──
    "chiastic": 2.0,
    "parallel_synonymous": 1.8,
    "parallel_antithetic": 1.8,
    "parallel_synthetic": 1.8,
    "parallel_step": 1.5,
    "inclusio": 2.0,
    "acrostic": 2.5,
    "refrain": 1.8,
    "formula_marker": 1.8,
    "keyword_linking": 1.5,
    "seam": 1.5,
    "emblematic_parallelism": 1.8,
    "numerical_parallelism": 1.5,
    "merismus": 1.5,
    "rhetorical_pair": 1.8,
    # ── Linguistic connections ──
    "same_lemma": 1.8,
    "same_root": 1.5,
    "same_morphology": 1.3,
    "hendiadys": 1.8,
    "semuchin": 1.5,
    # ── Intertextual ──
    "allusion": 2.5,
    "echo": 1.5,
    # ── Numerical (gematria) ──
    "same_gematria_standard": 1.5,
    "same_gematria_ordinal": 1.3,
    "same_gematria_reduced": 1.2,
    "divine_name_value": 1.8,
    "gematria_sum_relationship": 1.5,
    "gematria_factor": 1.3,
    "sacred_number": 1.3,
    "verse_gematria_total": 1.3,
    "divine_name_distribution": 1.3,
    # ── Frequency patterns ──
    "formula_count": 1.2,
    "7_fold_pattern": 1.2,
    "10_fold_pattern": 1.2,
    "12_fold_pattern": 1.2,
    "40_fold_pattern": 1.2,
    "hapax_legomenon": 1.5,
    "dislegomenon": 1.5,
    "concentration_index": 1.2,
    "key_word_count": 1.2,
    "repetition_pattern": 1.3,
    # ── Geographic ──
    "same_location": 1.8,
    "journey_path": 1.5,
    "wilderness_sojourn": 1.5,
    "exile_route": 1.5,
    "promised_land": 1.8,
    "mountain_of_god": 1.8,
    "temple_location": 2.0,
    "garden_presence": 2.0,
    # ── Chronological ──
    "same_time_period": 1.5,
    "genealogical": 2.0,
    "prophetic_timeline": 2.0,
    "sabbatical_cycle": 1.5,
    "jubilee_cycle": 1.5,
    "dispensation": 2.0,
    "chronological_marker": 1.5,
    "feast_connection": 2.0,
    # ── Symbolic ──
    "shared_symbol": 1.8,
    "apocalyptic_creature": 1.5,
    "apocalyptic_object": 1.5,
    "apocalyptic_event": 1.5,
    "person_type": 2.0,
    "event_type": 2.0,
    "institution_type": 2.0,
    "object_type": 1.8,
    "name_symbolic": 2.0,
    "temple_symbol": 2.0,
    # ── Interpretive ──
    "rabbinic_midrash": 1.8,
    "patristic_reading": 1.5,
    "reformation_view": 1.5,
    "giliadi_pattern": 1.3,
    "latter_day_saint_reading": 1.8,
    "critical_scholarship": 1.5,
    # ── Miscellaneous ──
    "chiasm_detected": 1.5,
}


def _discovery_lr(db):
    """Normalize discovered_by value and get its likelihood ratio."""
    db = (db or "algorithm").lower().strip()
    if db == "ai":
        db = "llm"
    return DISCOVERY_LR.get(db, 1.2)


def _tier_for(db):
    """Get numeric source tier for a discovery method."""
    db = (db or "algorithm").lower().strip()
    if db == "ai":
        db = "llm"
    return DISCOVERY_TIER.get(db, 4)


def star_display(n):
    """Return star string — e.g. star_display(4) = '★★★★☆'"""
    filled = "\u2605" * n
    empty = "\u2606" * (5 - n)
    return filled + empty


def _p_value_lr(p):
    """Convert p-value to likelihood ratio.
    
    A p-value of 0.001 means the pattern has 0.1% chance of being random.
    The LR = 1/p for significant results, capped at 20.
    """
    if p is None or p >= 0.05:
        return 1.0
    if p < 0.001:
        return 20.0
    if p < 0.01:
        return 5.0
    return 2.0


def _reasoning_lr(has_reasoning):
    """Whether human-readable reasoning exists."""
    return 2.0 if has_reasoning else 1.0


def _source_count_lr(agreement_count):
    """Multiple independent sources finding the same connection is strong evidence.
    
    Each additional source multiplies the LR by 1.5 (independent discovery is unlikely by chance).
    """
    if not agreement_count or agreement_count < 1:
        return 1.0
    return 1.0 + (agreement_count * 0.5)


def _feedback_weight(confirmation_data):
    """Weighted confirmation from structured user feedback.
    
    Different actions carry different evidentiary weight:
      - Simple click: 0.05
      - Providing reasoning: 0.15
      - Scholar citation: 0.30
      - Independent algorithm: 0.25
      - Explicit expert review: 0.50
    
    Returns a likelihood ratio multiplier.
    """
    if isinstance(confirmation_data, (int, float)):
        # Legacy: flat count
        return 1.0 + min(float(confirmation_data) * 0.03, 0.15)
    
    if isinstance(confirmation_data, dict):
        weights = {
            "click": 0.05,
            "reasoning": 0.15,
            "scholar_cite": 0.30,
            "independent_algorithm": 0.25,
            "expert_review": 0.50,
        }
        total = sum(confirmation_data.get(k, 0) * w for k, w in weights.items())
        return 1.0 + min(total, 0.30)
    
    return 1.0


def _prior_odds(source_tier=None):
    """Prior odds: what's the base rate of real connections at this source tier?
    
    S0 (text): 20:1 — almost certainly real
    S1 (tradition): 5:1 — strong tradition
    S2 (scholarly): 3:1 — scholarly consensus likely correct
    S3 (AI-assisted): 1:1 — 50/50
    S4 (algorithmic): 0.3:1 — most algorithmic patterns are noise
    """
    base_priors = {0: 20.0, 1: 5.0, 2: 3.0, 3: 1.0, 4: 0.3}
    return base_priors.get(source_tier, 1.0)


def rate_connection(
    discovered_by="algorithm",
    connection_type="",
    has_reasoning=False,
    confidence=0.5,
    confirmation_count=0,
    p_value=None,
    agreement_count=0,
):
    """Compute a multi-signal rating for a connection using Bayesian ensemble.

    Returns a dict with all signals broken out so the API can surface them.

    Args:
        discovered_by: 'text', 'tsk', 'llm', 'ai', 'human', or 'algorithm'
        connection_type: the type field (direct_quotation, same_lemma, etc.)
        has_reasoning: bool — does the metadata have a reasoning field?
        confidence: the existing 0.0-1.0 statistical confidence (legacy)
        confirmation_count: int or dict — flat count or structured feedback
        p_value: optional p-value from null-text Monte Carlo
        agreement_count: number of independent sources agreeing on this pair+type

    Returns:
        dict with signals breakdown including star rating
    """
    discovery_lr = _discovery_lr(discovered_by)
    discovery_label = DISCOVERY_LABELS.get(
        (discovered_by or "algorithm").lower().strip(),
        DISCOVERY_LABELS["algorithm"],
    )
    source_tier = _tier_for(discovered_by)
    type_lr = _type_lr(connection_type)
    reasoning_lr = _reasoning_lr(has_reasoning)
    p_lr = _p_value_lr(p_value)
    source_lr = _source_count_lr(agreement_count)
    feedback_lr = _feedback_weight(confirmation_count)

    prior_odds = _prior_odds(source_tier)

    # Bayesian ensemble: posterior odds = prior × product(LR)
    likelihood_product = (
        discovery_lr
        * type_lr
        * reasoning_lr
        * p_lr
        * source_lr
        * feedback_lr
    )
    posterior_odds = prior_odds * likelihood_product

    # Convert odds to probability
    overall = posterior_odds / (1 + posterior_odds)

    overall = max(0.01, min(0.99, overall))

    if overall >= 0.92:
        tier = "verified"
        tier_label = "Text-Explicit"
        tier_description = "The text itself makes this connection — explicit quotation or direct statement"
        stars = 5
        color = "#1B5E20"
    elif overall >= 0.80:
        tier = "strong"
        tier_label = "Well-Established"
        tier_description = "Strong scholarly or human consensus with clear reasoning"
        stars = 4
        color = "#2E7D32"
    elif overall >= 0.60:
        tier = "probable"
        tier_label = "Probable"
        tier_description = "Reasonable connection with some support or reasoning"
        stars = 3
        color = "#F57C00"
    elif overall >= 0.35:
        tier = "suggested"
        tier_label = "Suggested"
        tier_description = "Algorithmic pattern, not yet verified — use with discernment"
        stars = 2
        color = "#757575"
    elif overall >= 0.15:
        tier = "pattern"
        tier_label = "Pattern Only"
        tier_description = "Statistical artifact or theoretical — significance is uncertain"
        stars = 1
        color = "#9E9E9E"
    else:
        tier = "speculative"
        tier_label = "Speculative"
        tier_description = "Weak signal, needs verification — likely coincidence"
        stars = 0
        color = "#E91E63"

    # Build explanation of which signals drove the score
    signals_contrib = {
        "discovery_method": discovered_by,
        "discovery_lr": round(discovery_lr, 2),
        "discovery_label": discovery_label,
        "connection_type": connection_type,
        "type_lr": round(type_lr, 2),
        "has_reasoning": has_reasoning,
        "reasoning_lr": round(reasoning_lr, 2),
        "p_value": p_value,
        "p_value_lr": round(p_lr, 2),
        "agreement_count": agreement_count,
        "agreement_lr": round(source_lr, 2),
        "confirmation_lr": round(feedback_lr, 2),
    }

    # Show which signals helped (+) and which hurt (-)
    signal_effects = []
    for name, lr in [
        ("discovery", discovery_lr),
        ("connection_type", type_lr),
        ("reasoning", reasoning_lr),
        ("p_value", p_lr),
        ("inter_source_agreement", source_lr),
        ("confirmation", feedback_lr),
    ]:
        if lr > 1.2:
            signal_effects.append(f"+{name} ({lr:.1f}x)")
        elif lr < 0.8:
            signal_effects.append(f"-{name} ({lr:.1f}x)")
    explanation = f"Prior (S{source_tier}) × {' × '.join(signal_effects)}" if signal_effects else f"Prior (S{source_tier}) — no strong signals"

    return {
        "overall_confidence": round(overall, 3),
        "stars": stars,
        "max_stars": 5,
        "star_display": star_display(stars),
        "tier": tier,
        "tier_label": tier_label,
        "tier_description": tier_description,
        "tier_color": color,
        "source_tier": source_tier,
        "source_tier_label": TIER_LABELS.get(source_tier, "S4"),
        "explanation": explanation,
        "signals": signals_contrib,
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
    p_value = row.get("p_value", None)

    return rate_connection(
        discovered_by=discovered_by,
        connection_type=connection_type,
        has_reasoning=has_reasoning,
        confidence=confidence,
        confirmation_count=confirmation_count,
        p_value=p_value,
        agreement_count=0,  # Will be populated by Track D
    )


def enrich_connection(conn_dict):
    """Add signal breakdown to a connection dict from passage guides."""
    row = {
        "discovered_by": conn_dict.get("discovered_by", "algorithm"),
        "type": conn_dict.get("type", ""),
        "confidence": conn_dict.get("confidence", 0.5),
        "confirmation_count": conn_dict.get("confirmation_count", 0),
        "metadata": conn_dict.get("metadata", "{}"),
        "p_value": conn_dict.get("p_value", None),
    }
    signals = rate_connection_row(row)
    conn_dict["signals"] = signals
    conn_dict["quality_label"] = signals["tier_label"]
    conn_dict["star_display"] = signals["star_display"]
    return conn_dict


def calibrate_connection(p_value, effect_size, preregistered=0, cross_validated=0):
    """Legacy: determine quality level from statistical evidence alone.

    Kept for backward compatibility with validate_connections.py.
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
        p_value=p_value,
    )

    return result["tier"], round(result["overall_confidence"], 2)


QUALITY_LEVELS = {
    "verified": {"rank": 0, "label": "Text-Explicit", "stars": 5, "color": "#1B5E20",
        "description": "The text itself makes this connection — explicit quotation or direct statement"},
    "strong": {"rank": 1, "label": "Well-Established", "stars": 4, "color": "#2E7D32",
        "description": "Strong scholarly or human consensus with clear reasoning"},
    "probable": {"rank": 2, "label": "Probable", "stars": 3, "color": "#F57C00",
        "description": "Reasonable connection with some support or reasoning"},
    "suggested": {"rank": 3, "label": "Suggested", "stars": 2, "color": "#757575",
        "description": "Algorithmic pattern, not yet verified"},
    "pattern": {"rank": 4, "label": "Pattern Only", "stars": 1, "color": "#9E9E9E",
        "description": "Statistical artifact or theoretical — significance is uncertain"},
    "speculative": {"rank": 5, "label": "Speculative", "stars": 0, "color": "#E91E63",
        "description": "Weak signal, needs verification"},
    "rejected": {"rank": 6, "label": "Rejected", "stars": 0, "color": "#B71C1C",
        "description": "Contradicted by evidence"},
}


def get_quality_color(quality_level):
    return QUALITY_LEVELS.get(quality_level, {}).get("color", "#999")


def get_quality_stars(quality_level):
    return QUALITY_LEVELS.get(quality_level, {}).get("stars", 0)


def describe_quality(quality_level):
    return QUALITY_LEVELS.get(quality_level, {}).get("description", "")

# ── Explainer ───────────────────────────────────────────────────────────

def explain_rating(result):
    """Return a human-readable paragraph explaining how the rating was determined."""
    if not result:
        return "No rating data available."
    
    signals = result.get("signals", {})
    parts = [f"This connection is rated **{result['tier_label']}** ({result['stars']}/5 stars)."]
    
    # Source tier
    st = result.get("source_tier", 4)
    parts.append(f"Source authority: S{st} ({signals.get('discovery_method', 'unknown')}).")
    
    # Key drivers
    drivers = []
    if signals.get("discovery_lr", 1.0) > 2.0:
        drivers.append(f"strong discovery method ({signals['discovery_lr']}x)")
    if signals.get("p_value_lr", 1.0) > 2.0:
        drivers.append(f"statistical significance (p={signals.get('p_value', 'N/A')})")
    if signals.get("reasoning_lr", 1.0) > 1.0:
        drivers.append("has human-readable reasoning")
    if signals.get("agreement_count", 0) > 1:
        drivers.append(f"{signals['agreement_count']} independent sources agree")
    
    if drivers:
        parts.append("Driven by: " + "; ".join(drivers) + ".")
    else:
        parts.append("No strong signals — this is an algorithmic pattern awaiting verification.")
    
    return " ".join(parts)
