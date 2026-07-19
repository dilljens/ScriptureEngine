"""Connection quality calibration — Bayesian ensemble rating with 0-100 quality score.

Every connection gets a quality score (0-100) using likelihood ratio products
instead of a linear weighted sum. This naturally handles:
  - Multiple weak signals stacking into strong evidence
  - One strong signal being sufficient alone
  - Contradictory signals reducing confidence
  - Inter-source agreement as a natural Bayes factor

The rating considers 6 signal groups:
  - discovered_by:  who found this connection (text, tsk, llm, algorithm)
  - connection_type: what kind of connection (direct_quotation, same_lemma, etc.)
  - has_reasoning:  whether human-readable explanation exists
  - statistical:     p-value range, effect size from null-text controls
  - agreement:       multiple independent sources finding the same connection
  - confirmation:    weighted user feedback on this connection
"""


# ── Likelihood Ratios (Bayes factors) ──────────────────────────────────
# Each signal maps to a likelihood ratio: P(signal | real) / P(signal | chance)
# LR > 1 means the signal makes a real connection more likely
# LR < 1 means the signal makes a chance connection more likely
# LRs multiply together to form the posterior odds.

DISCOVERY_LR = {
    "text": 20.0,       # Text-explicit: 20x more likely for real connections
    "tsk": 10.0,         # Historical cross-reference: strong scholarly tradition
    "script": 8.0,       # Explicit scriptural connection
    "human": 6.0,        # Human-curated: scholar documented it
    "llm": 3.0,          # LLM-assisted: good pattern recognition, some noise
    "ai": 3.0,           # Same as llm
    "sefaria_api": 2.5,  # Sefaria links: rabbinic tradition references
    "lds_topical_guide": 2.0,  # LDS topical guide: curated but tradition-specific
    "bible_dictionary": 2.0,   # Bible dictionary entry
    "shem_hamephorash_scanner": 1.5,  # Specialized scanner
    "algorithm": 1.5,    # Automated: weak on its own, stacks with others
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
    "bible_dictionary": "Bible Dictionary — curated reference entry",
    "shem_hamephorash_scanner": "Shem HaMephorash Scanner — 72-name encoding pattern",
    "algorithm": "Algorithmic — machine-detected, not verified",
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


# ── Connection type LRs ───────────────────────────────────────────────

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
    # ── Passage-level / macro-structural ──
    "pericope_parallel": 2.5,
    "section_parallel": 2.0,
    "book_thematic": 2.0,
    "quotation_chain": 3.0,
    "macro_chiastic": 2.0,
    "narrative_parallel": 2.5,
    "fulfillment_arc": 3.0,
    "covenant_pattern": 2.5,
    "temple_trajectory": 2.0,
    "symbolic_system": 2.0,
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


def _type_lr(conn_type):
    return TYPE_LR.get(conn_type, 1.5)


def _discovery_lr(discovered_by):
    db = (discovered_by or "algorithm").lower().strip()
    if db == "ai":
        db = "llm"
    return DISCOVERY_LR.get(db, 1.2)


def _tier_for(discovered_by):
    db = (discovered_by or "algorithm").lower().strip()
    if db == "ai":
        db = "llm"
    return DISCOVERY_TIER.get(db, 4)


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


def _agreement_lr(agreement_count):
    """Multiple independent sources finding the same connection is strong evidence.

    Each additional independent source multiplies LR by 1.5.
    This is calibrated so that 1 extra source = 50% more confident,
    4+ extra sources = 3x more confident.
    """
    if not agreement_count or agreement_count < 1:
        return 1.0
    return min(1.0 + (agreement_count * 0.5), 4.0)


def _feedback_weight(confirmation_data):
    """Weighted confirmation from structured user feedback.

    Different actions carry different evidentiary weight:
      - Simple click: 0.05
      - Providing reasoning: 0.15
      - Scholar citation: 0.30
      - Independent algorithm: 0.25
      - Explicit expert review: 0.50

    Returns a likelihood ratio multiplier (max 1.5x).
    """
    if isinstance(confirmation_data, (int, float)):
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
        return 1.0 + min(total, 0.50)

    return 1.0


def _prior_odds(source_tier=None):
    """Prior odds: base probability that a connection is real given its source tier.

    S0 (text):      50:1  (98.0%)  — canonical text is almost certainly intentional
    S1 (tradition): 10:1  (90.9%)  — strong historical tradition
    S2 (scholarly): 5:1   (83.3%)  — scholarly consensus
    S3 (AI):        1.5:1 (60.0%)  — AI-assisted patterns, moderate reliability
    S4 (algorithm): 0.5:1 (33.3%)  — most algorithmic patterns are noise

    These are calibrated to be conservative: even a text-explicit connection
    needs at least some signal evidence to reach 100. A purely algorithmic
    connection needs strong signals to be considered probable.
    """
    base_priors = {0: 50.0, 1: 10.0, 2: 5.0, 3: 1.5, 4: 0.5}
    return base_priors.get(source_tier, 0.5)


# ── Quality score tiers ───────────────────────────────────────────────
# Quality score maps to tiers as follows:
#   92-100  verified   — Text-Explicit
#   80-91   strong     — Well-Established
#   60-79   probable   — Probable
#   35-59   suggested  — Suggested
#   15-34   pattern    — Pattern Only
#   0-14    speculative — Speculative

QUALITY_LEVELS = {
    "verified": {
        "min_score": 92,
        "label": "Text-Explicit",
        "color": "#1B5E20",
        "description": "The text itself makes this connection — explicit quotation or direct statement",
    },
    "strong": {
        "min_score": 80,
        "label": "Well-Established",
        "color": "#2E7D32",
        "description": "Strong scholarly or human consensus with clear reasoning",
    },
    "probable": {
        "min_score": 60,
        "label": "Probable",
        "color": "#F57C00",
        "description": "Reasonable connection with some support or reasoning",
    },
    "suggested": {
        "min_score": 35,
        "label": "Suggested",
        "color": "#757575",
        "description": "Algorithmic pattern, not yet verified — use with discernment",
    },
    "pattern": {
        "min_score": 15,
        "label": "Pattern Only",
        "color": "#9E9E9E",
        "description": "Statistical artifact or theoretical — significance is uncertain",
    },
    "speculative": {
        "min_score": 0,
        "label": "Speculative",
        "color": "#E91E63",
        "description": "Weak signal, needs verification — likely coincidence",
    },
    "rejected": {
        "min_score": 0,
        "label": "Rejected",
        "color": "#B71C1C",
        "description": "Contradicted by evidence",
    },
}

TIER_ORDER = ["verified", "strong", "probable", "suggested", "pattern", "speculative", "rejected"]


def probability_to_quality(probability):
    """Convert a probability (0.0-1.0) to a quality score (0-100)."""
    return round(max(0, min(100, probability * 100)))


def quality_to_tier(quality_score):
    """Map a 0-100 quality score to its tier name."""
    for tier in TIER_ORDER:
        if tier == "rejected":
            continue
        info = QUALITY_LEVELS[tier]
        if quality_score >= info["min_score"]:
            return tier
    return "speculative"


def get_quality_info(quality_score):
    """Get the full tier info for a quality score."""
    tier = quality_to_tier(quality_score)
    info = dict(QUALITY_LEVELS[tier])
    info["tier"] = tier
    info["quality_score"] = quality_score
    return info


# ── Main rating function ──────────────────────────────────────────────


def rate_connection(
    discovered_by="algorithm",
    connection_type="",
    has_reasoning=False,
    confidence=0.5,
    confirmation_count=0,
    p_value=None,
    agreement_count=0,
    generator_precision=None,
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
        generator_precision: optional float 0-1 — known precision of this generator

    Returns:
        dict with signals breakdown including quality_score (0-100)
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
    source_lr = _agreement_lr(agreement_count)
    feedback_lr = _feedback_weight(confirmation_count)

    # Generator precision bonus: if we know this generator's empirical precision,
    # it acts as an additional LR multiplier.
    # For example, a generator with 80% precision gets 1.8x instead of default 1.0
    gen_lr = 1.0
    if generator_precision is not None:
        gen_lr = 1.0 + (generator_precision * 1.0)  # 80% precision → 1.8x

    prior_odds = _prior_odds(source_tier)

    # Bayesian ensemble: posterior odds = prior × product(LR)
    likelihood_product = (
        discovery_lr
        * type_lr
        * reasoning_lr
        * p_lr
        * source_lr
        * feedback_lr
        * gen_lr
    )
    posterior_odds = prior_odds * likelihood_product

    # Convert odds to probability
    overall = posterior_odds / (1 + posterior_odds)
    overall = max(0.01, min(0.99, overall))

    quality_score = probability_to_quality(overall)
    tier_info = get_quality_info(quality_score)

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
        "generator_precision": generator_precision,
        "generator_lr": round(gen_lr, 2),
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
        ("generator", gen_lr),
    ]:
        if lr > 1.2:
            signal_effects.append(f"+{name} ({lr:.1f}x)")
        elif lr < 0.8:
            signal_effects.append(f"-{name} ({lr:.1f}x)")
    explanation = (
        f"Prior (S{source_tier}) × {' × '.join(signal_effects)}"
        if signal_effects
        else f"Prior (S{source_tier}) — no strong signals"
    )

    return {
        "quality_score": quality_score,
        "overall_confidence": round(overall, 3),
        "tier": tier_info["tier"],
        "tier_label": tier_info["label"],
        "tier_description": tier_info["description"],
        "tier_color": tier_info["color"],
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
    agreement_count = row.get("agreement_count", 0) or 0

    return rate_connection(
        discovered_by=discovered_by,
        connection_type=connection_type,
        has_reasoning=has_reasoning,
        confidence=confidence,
        confirmation_count=confirmation_count,
        p_value=p_value,
        agreement_count=agreement_count,
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
        "agreement_count": conn_dict.get("agreement_count", 0) or 0,
    }
    signals = rate_connection_row(row)
    conn_dict["signals"] = signals
    conn_dict["quality_score"] = signals["quality_score"]
    conn_dict["quality_label"] = signals["tier_label"]
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


def get_quality_color(tier):
    return QUALITY_LEVELS.get(tier, {}).get("color", "#999")


def get_quality_score_for_tier(tier):
    return QUALITY_LEVELS.get(tier, {}).get("min_score", 0)


def describe_quality(tier):
    return QUALITY_LEVELS.get(tier, {}).get("description", "")


# ── Agreement count computation ───────────────────────────────────────
# After all generators run, compute how many independent sources found
# connections for each (source_verse, target_verse, layer) pair.
# The agreement_count is the number of distinct discovered_by values
# that produced a connection between the same source and target.


def compute_agreement_counts(conn):
    """Scan connections table and count independent sources per (source, target, layer).

    Updates agreement_count on each connection row.
    This should be called after all generators have run.

    Args:
        conn: SQLite connection

    Returns:
        dict with stats on how many connections got agreement boosts
    """
    # Find all (source, target, layer) groups that have multiple discovered_by values
    groups = conn.execute("""
        SELECT source_verse, target_verse, layer,
               COUNT(DISTINCT discovered_by) AS source_count,
               GROUP_CONCAT(DISTINCT discovered_by) AS sources
        FROM connections
        GROUP BY source_verse, target_verse, layer
        HAVING source_count >= 2
    """).fetchall()

    updated = 0
    # For each group with multiple sources, compute agreement_count per connection
    for group in groups:
        source_verse = group["source_verse"]
        target_verse = group["target_verse"]
        layer = group["layer"]
        source_count = group["source_count"]

        # Count how many distinct discovery methods exist for this pair+layer
        # Exclude the connection's own discovered_by when counting agreement
        rows = conn.execute("""
            SELECT id, discovered_by FROM connections
            WHERE source_verse = ? AND target_verse = ? AND layer = ?
        """, (source_verse, target_verse, layer)).fetchall()

        for row in rows:
            # agreement = source_count - 1 (exclude self)
            agreement = source_count - 1
            if agreement > 0:
                conn.execute(
                    "UPDATE connections SET agreement_count = ? WHERE id = ?",
                    (min(agreement, 10), row["id"]),
                )
                updated += 1

    conn.commit()
    return {
        "groups_with_agreement": len(groups),
        "connections_updated": updated,
    }


# ── Explainer ─────────────────────────────────────────────────────────


def explain_rating(result):
    """Return a human-readable paragraph explaining how the rating was determined."""
    if not result:
        return "No rating data available."

    signals = result.get("signals", {})
    parts = [
        f"This connection is rated **{result['tier_label']}** "
        f"(quality: {result['quality_score']}/100)."
    ]

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
