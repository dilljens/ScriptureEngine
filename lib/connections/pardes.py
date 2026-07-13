"""PaRDeS — the four levels of scriptural interpretation.

P'shat (פְּשָׁט) — Simple/literal — what the text says
Remez (רֶמֶז)   — Hinted — what the text alludes to
Drash (דְּרַשׁ)  — Inquired — how the text connects across the canon
Sod (סוֹד)      — Hidden/mystical — deep structural and numerical patterns

Maps every connection type to its PaRDeS level.
"""

# PaRDeS levels
LEVELS = {
    "p'shat": {
        "hebrew": "פְּשָׁט",
        "name": "P'shat",
        "description": "Simple, literal meaning — what the text says on the surface",
        "color": "#4CAF50",  # Green
    },
    "remez": {
        "hebrew": "רֶמֶז",
        "name": "Remez",
        "description": "Hinted or allegorical meaning — what the text alludes to",
        "color": "#2196F3",  # Blue
    },
    "drash": {
        "hebrew": "דְּרַשׁ",
        "name": "Drash",
        "description": "Comparative or interpretive meaning — how the text connects across the canon",
        "color": "#FF9800",  # Orange
    },
    "sod": {
        "hebrew": "סוֹד",
        "name": "Sod",
        "description": "Hidden, mystical meaning — deep structural, numerical, and letter-level patterns",
        "color": "#9C27B0",  # Purple
    },
}

# Map every (layer, type) → PaRDeS level
# Format: {layer: {type: level, ...}, ...}
TYPE_PARDES = {
    "linguistic": {
        "same_lemma": "p'shat",
        "same_root": "p'shat",
        "same_morphology": "p'shat",
        "wordplay": "remez",
        "cognate": "remez",
        "semantic_domain": "remez",
        "nomen_est_omen": "remez",
        "hendiadys": "remez",
    },
    "numerical": {
        "same_gematria_standard": "sod",
        "same_gematria_ordinal": "sod",
        "same_gematria_reduced": "sod",
        "divine_name_value": "sod",
        "gematria_sum_relationship": "sod",
        "gematria_factor": "sod",
        "sacred_number": "sod",
        "verse_gematria_total": "sod",
    },
    "structural": {
        "chiastic": "remez",
        "parallel_synonymous": "p'shat",
        "parallel_antithetic": "p'shat",
        "parallel_synthetic": "p'shat",
        "parallel_step": "remez",
        "inclusio": "remez",
        "refrain": "remez",
        "seam": "p'shat",
        "formula_marker": "p'shat",
        "acrostic": "sod",
        "chiasm_detected": "remez",
        "emblematic_parallelism": "remez",
        "numerical_parallelism": "remez",
        "merismus": "remez",
        "keyword_linking": "p'shat",
        "rhetorical_pair": "remez",
    },
    "intertextual": {
        "direct_quotation": "remez",
        "modified_quotation": "remez",
        "allusion": "remez",
        "echo": "remez",
        "type_antitype": "drash",
        "prophetic_fulfillment": "drash",
        "midrashic_connection": "drash",
        "summarized": "remez",
    },
    "textual": {
        "textual_variant": "p'shat",
        "jst_change": "p'shat",
        "jst_addition": "p'shat",
        "jst_clarification": "drash",
        "septuagint_difference": "drash",
        "dead_sea_scrolls_variant": "p'shat",
        "quotation_variant": "p'shat",
        "peshitta_variant": "p'shat",
        "vulgate_variant": "p'shat",
        "inspired_revision": "drash",
    },
    "geographic": {
        "same_location": "p'shat",
        "journey_path": "drash",
        "wilderness_sojourn": "drash",
        "exile_route": "drash",
        "promised_land": "drash",
        "mountain_of_god": "remez",
        "temple_location": "remez",
        "garden_presence": "sod",
    },
    "chronological": {
        "same_time_period": "p'shat",
        "genealogical": "p'shat",
        "prophetic_timeline": "drash",
        "sabbatical_cycle": "sod",
        "jubilee_cycle": "sod",
        "dispensation": "drash",
        "chronological_marker": "p'shat",
        "feast_connection": "remez",
    },
    "interpretive": {
        "rabbinic_midrash": "drash",
        "patristic_reading": "drash",
        "reformation_view": "drash",
        "giliadi_pattern": "sod",
        "latter_day_saint_reading": "drash",
        "prophetic_quote": "drash",
        "critical_scholarship": "drash",
        "lectio_divina": "sod",
    },
    "frequency": {
        "divine_name_distribution": "sod",
        "formula_count": "p'shat",
        "7_fold_pattern": "sod",
        "10_fold_pattern": "drash",
        "12_fold_pattern": "sod",
        "40_fold_pattern": "sod",
        "hapax_legomenon": "p'shat",
        "dislegomenon": "p'shat",
        "concentration_index": "drash",
        "key_word_count": "p'shat",
        "repetition_pattern": "p'shat",
    },
    "symbolic": {
        "shared_symbol": "remez",
        "apocalyptic_creature": "remez",
        "apocalyptic_object": "remez",
        "apocalyptic_time": "remez",
        "apocalyptic_event": "remez",
        "person_type": "sod",
        "event_type": "sod",
        "institution_type": "sod",
        "object_type": "sod",
        "name_symbolic": "drash",
        "temple_symbol": "sod",
    },
    "sod": {
        "temple_ascent": "sod",
        "temple_microcosm": "sod",
        "temple_veil": "sod",
        "temple_creation": "sod",
        "temple_eschaton": "sod",
        "temple_throne": "sod",
        "eden_temple": "sod",
        "angel_of_yhwh": "sod",
        "divine_council": "sod",
        "divine_ascent": "sod",
        "holy_of_holies": "sod",
        "mercy_seat": "sod",
        "living_water": "sod",
        "cosmic_mountain": "sod",
        "sacred_center": "sod",
        "primordial_creation": "sod",
        "kingdom_priesthood": "sod",
        "divine_marriage": "sod",
        "theosis": "sod",
        "watchers_enedochic": "sod",
        "dss_sectarian": "sod",
    },
}


def get_pardes_level(layer, type_name):
    """Get the PaRDeS level for a (layer, type) pair."""
    return TYPE_PARDES.get(layer, {}).get(type_name, "p'shat")


# Flat reverse map: type_name -> PaRDeS level
_TYPE_TO_PARDES = {}
for _layer, _types in TYPE_PARDES.items():
    for _t, _level in _types.items():
        _TYPE_TO_PARDES[_t] = _level


def get_pardes_level_for_type(type_name):
    """Get the PaRDeS level for a connection type name alone.

    Since every connection type belongs to exactly one layer in TYPE_PARDES,
    this is safe for all defined types. Unknown types default to 'p'shat'.
    """
    return _TYPE_TO_PARDES.get(type_name, "p'shat")


def get_connections_by_level(conn_by_layer):
    """Group connection summary by PaRDeS level instead of layer.

    Args:
        conn_by_layer: dict from get_connections_by_layer() or similar

    Returns:
        {level_name: {count, types, connections_by_type}}
    """
    result = {
        "p'shat": _empty_level("p'shat"),
        "remez": _empty_level("remez"),
        "drash": _empty_level("drash"),
        "sod": _empty_level("sod"),
        "unmapped": _empty_level(None),
    }

    for layer_name, layer_data in conn_by_layer.items():
        if isinstance(layer_data, dict) and "types" in layer_data:
            # From get_all_layers_for_verse format
            for type_name, type_data in layer_data["types"].items():
                level = get_pardes_level(layer_name, type_name)
                if level not in result:
                    level = "unmapped"
                result[level]["count"] += type_data.get("count", len(type_data.get("connections", [])))
                if layer_name not in result[level]["layers"]:
                    result[level]["layers"].append(layer_name)
                if type_name not in result[level]["types"]:
                    result[level]["types"].append(type_name)
        else:
            # From get_connections format (list per layer)
            for conn in layer_data if isinstance(layer_data, list) else []:
                type_name = conn.get("type", "")
                level = get_pardes_level(layer_name, type_name)
                if level not in result:
                    level = "unmapped"
                result[level]["count"] += 1
                if layer_name not in result[level]["layers"]:
                    result[level]["layers"].append(layer_name)

    return result


def _empty_level(level_name):
    info = LEVELS.get(level_name, {"name": "Unmapped", "description": ""})
    return {
        "name": info["name"],
        "hebrew": info.get("hebrew", ""),
        "description": info.get("description", ""),
        "color": info.get("color", "#999"),
        "count": 0,
        "layers": [],
        "types": [],
    }


def get_layer_stats(conn):
    """Get statistics about connections grouped by PaRDeS level."""
    rows = conn.execute("""
        SELECT layer, type, COUNT(*) as c
        FROM connections
        GROUP BY layer, type
    """).fetchall()

    stats = {
        "p'shat": _empty_level("p'shat"),
        "remez": _empty_level("remez"),
        "drash": _empty_level("drash"),
        "sod": _empty_level("sod"),
        "unmapped": _empty_level(None),
    }

    for r in rows:
        level = get_pardes_level(r["layer"], r["type"])
        if level not in stats:
            level = "unmapped"
        stats[level]["count"] += r["c"]
        if r["type"] not in stats[level]["types"]:
            stats[level]["types"].append(r["type"])

    return stats
