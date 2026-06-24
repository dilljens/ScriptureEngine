"""
Connection type definitions — the 11 layers of the scripture connection graph.

Each connection between two verses has:
  - layer:       top-level category
  - type:        specific connection type
  - subtype:     optional refinement
  - strength:    0.0–1.0 how strong/clear the connection is
  - confidence:  0.0–1.0 how sure we are it's real
  - discovered_by:  'human', 'algorithm', 'ai'
"""

# === LAYER DEFINITIONS ===

LAYERS = {
    "linguistic": {
        "name": "Linguistic",
        "description": "Word-level language connections — same lemma, root, morphology, wordplay",
        "types": [
            "same_lemma",        # Same Strong's number / lexical form
            "same_root",         # Same triconsonantal root
            "same_morphology",   # Same grammatical form (same verb stem, tense, etc.)
            "wordplay",          # Pun, double meaning, paronomasia
            "cognate",           # Words from same root in related languages
            "semantic_domain",   # Words in the same conceptual category
            "nomen_est_omen",    # Name meaning is significant to context
            "hendiadys",         # Two words expressing one idea
            "keyword_linking",   # Hebrew catchwords linking adjacent passages (Isaiah keyword experiments)
        ]
    },
    "numerical": {
        "name": "Numerical (Gematria)",
        "description": "Gematria values, divine name values, numerical relationships",
        "types": [
            "same_gematria_standard",   # Same standard gematria value
            "same_gematria_ordinal",    # Same ordinal gematria value
            "same_gematria_reduced",    # Same reduced gematria value
            "divine_name_value",        # Gematria equals a divine name value
            "gematria_sum_relationship", # Word A + Word B = Word C gematria
            "gematria_factor",          # Gematria factors into sacred numbers
            "sacred_number",            # Value is a sacred number (7, 12, 40, etc.)
            "verse_gematria_total",     # Verse-level gematria total significance
        ]
    },
    "structural": {
        "name": "Structural",
        "description": "Literary structures — chiasms, parallelisms, inclusios, refrains, acrostics",
        "types": [
            "chiastic",                # A-B-C-C'-B'-A' mirror structure
            "parallel_synonymous",     # Same idea restated in different words
            "parallel_antithetic",     # Opposite ideas contrasted
            "parallel_synthetic",      # First line completed/expanded by second
            "parallel_step",           # Escalating/climbing parallelism
            "inclusio",                # Same phrase opens and closes a unit
            "emblematic_parallelism",  # "As... so..." comparison
            "numerical_parallelism",   # "Three things... yea, four"
            "merismus",                # Paired opposites = totality (heaven+earth)
            "keyword_linking",         # Same root linking adjacent passages
            "rhetorical_pair",         # Parallel rhetorical questions
            "refrain",                 # Repeated phrase at structural intervals
            "seam",                    # Structural join point / transition
            "formula_marker",          # "And it came to pass", "Thus says the Lord"
            "acrostic",                # Alphabetic/acrostic structure
            "chiasm_detected",         # Algorithmically detected chiasm
        ]
    },
    "intertextual": {
        "name": "Intertextual",
        "description": "How texts quote, allude to, or echo other texts",
        "types": [
            "direct_quotation",        # Verbatim or near-verbatim quote
            "modified_quotation",      # Quote with intentional changes
            "allusion",                # Clear reference without direct quote
            "echo",                    # Subtle linguistic echo
            "type_antitype",           # Prophetic pattern → fulfillment
            "prophetic_fulfillment",   # Specific prediction → specific event
            "midrashic_connection",    # Interpretive re-use of earlier text
            "summarized",              # Earlier text summarized in later text
            "semantic_domain",         # Cross-canon semantic domain connections
        ]
    },
    "textual": {
        "name": "Textual",
        "description": "Textual variants, manuscript traditions, translation differences",
        "types": [
            "textual_variant",         # Different manuscript reading
            "jst_change",              # Joseph Smith Translation modified wording
            "jst_addition",            # Joseph Smith Translation expanded text
            "septuagint_difference",   # Where LXX differs from MT
            "dead_sea_scrolls_variant",# DSS reading that differs
            "quotation_variant",       # NT quotes OT from LXX vs MT
            "peshitta_variant",        # Syriac Peshitta reading
            "vulgate_variant",         # Latin Vulgate reading
            "inspired_revision",       # Modern prophetic revision (Moses, Abraham)
        ]
    },
    "geographic": {
        "name": "Geographic",
        "description": "Geographical and spatial connections between passages",
        "types": [
            "same_location",           # Both passages mention the same place
            "journey_path",            # Part of the same journey route
            "wilderness_sojourn",      # Wilderness experience connections
            "exile_route",             # Exile/deportation connections
            "promised_land",           # Land/covenant land connections
            "mountain_of_god",         # Sinai/Zion/temple mount connections
            "temple_location",         # Temple/House of the Lord connections
            "garden_presence",         # Eden/temple/presence connections
        ]
    },
    "chronological": {
        "name": "Chronological",
        "description": "Temporal connections — same time, genealogy, prophetic timelines",
        "types": [
            "same_time_period",        # Events happening in the same era
            "genealogical",            # Family lineage connections
            "prophetic_timeline",      # Prediction → fulfillment dating
            "sabbatical_cycle",        # 7-year cycle connections
            "jubilee_cycle",           # 50-year cycle connections
            "dispensation",            # Same gospel dispensation
            "chronological_marker",    # Marked by time references
            "feast_connection",        # Connected by feast day / holy day
        ]
    },
    "interpretive": {
        "name": "Interpretive Tradition",
        "description": "How the text has been interpreted across traditions",
        "types": [
            "rabbinic_midrash",        # Talmud/Midrash interpretation
            "patristic_reading",       # Early church father's interpretation
            "reformation_view",        # Lutheran/Reformed interpretation
            "giliadi_pattern",         # Avraham Giliadi structural observation
            "latter_day_saint_reading",# Distinctive LDS interpretation
            "prophetic_quote",         # Modern prophet cited this passage
            "critical_scholarship",    # Source/form/redaction critical view
            "lectio_divina",           # Monastic/spiritual reading tradition
            "midrashic_connection",    # Interpretive re-use across traditions
        ]
    },
    "frequency": {
        "name": "Frequency",
        "description": "Occurrence counts, distribution patterns, formula statistics",
        "types": [
            "divine_name_distribution",
            "formula_count",
            "7_fold_pattern",
            "10_fold_pattern",
            "12_fold_pattern",
            "40_fold_pattern",
            "hapax_legomenon",
            "dislegomenon",
            "concentration_index",
            "key_word_count",
            "repetition_pattern",
        ]
    },
    "symbolic": {
        "name": "Symbolic",
        "description": "Shared symbols, apocalyptic vocabulary, typology — conceptual connections across the canon",
        "types": [
            "shared_symbol",            # Same symbol used in multiple books (lamb, throne, fire, etc.)
            "apocalyptic_creature",     # Composite beings — beasts, cherubim, living creatures
            "apocalyptic_object",       # Scrolls, trumpets, seals, bowls, measuring rods
            "apocalyptic_time",         # Symbolic time periods — 1260 days, time/times/half-time
            "apocalyptic_event",        # Cosmic disturbances — earthquakes, darkness, stars falling
            "person_type",              # Person as a type of another (Adam→Christ, Melchizedek→Christ)
            "event_type",               # Event as a type of another (Exodus→Redemption, Flood→Baptism)
            "institution_type",         # Institution as a type (Tabernacle→Heaven, Sacrifices→Atonement)
            "object_type",              # Object as a type (Bronze Serpent→Cross, Manna→Bread of Life)
            "name_symbolic",            # Place/person names as symbols (Babylon=opposition, Zion=covenant)
            "temple_symbol",            # Temple/tabernacle furnishings and rituals as symbols
        ]
    },
    "sod": {
        "name": "Sod (Hidden / Temple)",
        "description": "Deep temple-theology, mystical, ascent, and hidden connections — the inner meaning of the text",
        "types": [
            "temple_ascent",            # Mountain-of-the-Lord / ascent motif
            "temple_microcosm",         # Temple as miniature creation/universe
            "temple_veil",              # Veil as boundary between realms
            "temple_creation",          # Temple building as creation act
            "temple_eschaton",          # Temple as new creation goal
            "temple_throne",            # Temple as divine throne room
            "eden_temple",              # Garden of Eden as prototype temple
            "angel_of_yhwh",            # Malach YHWH theophany / divine mediator
            "divine_council",           # Heavenly council / sons of God
            "divine_ascent",            # Ascent to heaven / visionary ascent
            "holy_of_holies",           # Access to the Holy of Holies
            "mercy_seat",               # Kapporet / mercy seat typology
            "living_water",             # Temple as source of living water
            "cosmic_mountain",          # Temple mount as cosmic mountain
            "sacred_center",            # Temple as navel of the world / axis mundi
            "primordial_creation",      # Creation temple themes from ancient near east
            "kingdom_priesthood",       # Royal priesthood / Melchizedek
            "divine_marriage",          # Temple as divine marriage / hieros gamos
            "theosis",                  # Deification / becoming divine through covenant
            "watchers_enedochic",       # Enochic / Watcher tradition connections
            "dss_sectarian",            # Dead Sea Scrolls sectarian parallels
            # Orphan types — already populated in DB by generators/seed data
            "angelomorphic",            # Human-like divine figures / angelomorphic christology
            "angelophany",              # Angelic theophany appearances
            "divine_mediator",          # Figures who mediate between God and humanity
            "heavenly_ascent",          # Ascent to heaven / visionary journeys
            "heavenly_council",         # Heavenly council assembly scenes
            "hekhalot",                 # Heavenly temple / palace traditions (hekhalot mysticism)
            "merkabah",                 # Throne-chariot visions / merkabah mysticism
            "theophany",                # Direct divine manifestation / theophany
            "two_powers",               # Two powers in heaven tradition
        ]
    },
}


# Flat list of all connection types (for validation)
ALL_TYPES = []
for layer_name, layer_data in LAYERS.items():
    for t in layer_data["types"]:
        ALL_TYPES.append((layer_name, t))


def get_layer_info(layer_name):
    """Get layer definition by name."""
    return LAYERS.get(layer_name)


def get_type_info(layer_name, type_name):
    """Check if a type exists in a layer."""
    layer = LAYERS.get(layer_name)
    if layer and type_name in layer["types"]:
        return layer
    return None


def describe_connection(layer, type_name, subtype=""):
    """Get a human-readable description of a connection."""
    descriptions = {
        "chiastic": "Chiastic mirror structure (A-B-C-C'-B'-A')",
        "parallel_synonymous": "Synonymous parallelism — same idea restated",
        "parallel_antithetic": "Antithetic parallelism — opposites contrasted",
        "direct_quotation": "Direct quotation of earlier scripture",
        "allusion": "Allusion to earlier scripture",
        "echo": "Subtle linguistic echo of earlier text",
        "same_gematria_standard": "Shares the same standard gematria value",
        "divine_name_value": "Gematria value equals a divine name",
        "type_antitype": "Prophetic type finding its antitype fulfillment",
        "inclusio": "Same phrase bookends the unit",
        "jst_change": "Revised in the Joseph Smith Translation",
    }
    key = f"{layer}.{type_name}"
    if subtype:
        key += f".{subtype}"
    return descriptions.get(key) or descriptions.get(f"{layer}.{type_name}") or f"{layer}/{type_name}"
