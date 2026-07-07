"""Connection generator registry.

Each generator module exports a `run(conn, book_ids=None) -> int` function.
The registry discovers all generators and provides a unified runner.
"""

import importlib
import pkgutil
from pathlib import Path

# Generator registry — populated at import time
REGISTRY = {}

# Generator metadata — each entry has:
#   name: display name
#   module: the Python module
#   layers: list of layer names this generator populates
#   automatic: True if can run without AI review
#   requires: data dependencies

GENERATOR_DEFS = [
    {
        "name": "Linguistic — Same Lemma",
        "module_path": ".linguistic",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses sharing rare Hebrew lemmas (Strong's numbers)",
    },
    {
        "name": "Structural — Chiastic Pairs",
        "module_path": ".structural",
        "layers": ["structural"],
        "automatic": True,
        "requires": "known_chiasms table + chiastic detector",
        "description": "Connects A↔A', B↔B' pairs from known and detected chiasms",
    },
    {
        "name": "Intertextual — Quotation Detection",
        "module_path": ".intertextual",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through shared rare-word clusters indicating quotations/allusions",
    },
    {
        "name": "Frequency — Distribution",
        "module_path": ".frequency",
        "layers": ["frequency"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses with shared word frequency patterns",
    },
    {
        "name": "Geographic — Location",
        "module_path": ".geographic",
        "layers": ["geographic"],
        "automatic": False,
        "requires": "place name gazetteer (simple seed included)",
        "description": "Connects verses mentioning the same biblical location",
    },
    {
        "name": "Numerical — Full Gematria",
        "module_path": ".numerical_full",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Expands gematria connections beyond divine names to all sacred numbers and value matches",
    },

    # ── Sod Layer Generators (Scholar Frameworks) ──

    {
        "name": "Divine Council — Heiser Framework",
        "module_path": ".heiser_divine_council",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects divine council passages (sons of God, heavenly court, territorial spirits) following Michael Heiser's framework",
    },
    {
        "name": "Temple-Creation — Beale Framework",
        "module_path": ".beale_temple_creation",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects temple/tabernacle passages to creation typology following G.K. Beale's framework",
    },
    {
        "name": "Angel of YHWH — Barker Framework",
        "module_path": ".barker_angel_yhwh",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects Angel of YHWH, Day of Atonement, and temple microcosm passages following Margaret Barker's Temple Theology",
    },
    {
        "name": "Merkabah — Orlov/Schäfer Framework",
        "module_path": ".orlov_merkabah",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects throne visions, heavenly ascent, and two-powers passages following Orlov and Schäfer's merkabah tradition",
    },
    {
        "name": "Temple Themes — Living Water, Throne, Veil, Creation, Center",
        "module_path": ".temple_themes",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects passages for 5 empty sod types: living water, temple throne, temple veil, primordial creation, sacred center",
    },

    # ── Orphan Generators (Structural + Frequency) ──

    {
        "name": "Chiasm Detection — Algorithmic",
        "module_path": ".chiasm_detector",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Algorithmic chiastic structure detection on each book",
    },
    {
        "name": "Formula Markers — Structural Seams",
        "module_path": ".formula_markers",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects formula markers ('And it came to pass', 'Thus says the Lord') as structural seams",
    },
    {
        "name": "Refrain Detection — Repeated Phrases",
        "module_path": ".refrain",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Finds repeated phrases at structural intervals across books",
    },
    {
        "name": "Parallelism — Poetic Structures",
        "module_path": ".parallelism",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects synonymous, antithetic, synthetic, and step parallelism",
    },
    {
        "name": "Acrostic Detection",
        "module_path": ".acrostic",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects alphabetic/acrostic structures in Hebrew poetry",
    },
    {
        "name": "Hapax & Dislegomenon",
        "module_path": ".hapax_dislegomenon",
        "layers": ["frequency"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses through rare words (hapax legomena and dislegomena)",
    },

    # ── Ordinal + Reduced Gematria ──

    {
        "name": "Ordinal & Reduced Gematria",
        "module_path": ".ordinal_reduced_gematria",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Adds ordinal and reduced gematria connections",
    },
    {
        "name": "Gematria Factor — Sacred Number Factors",
        "module_path": ".gematria_factor",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses where gematria values factor into sacred numbers",
    },
    {
        "name": "Gematria Sum — Word Relationships",
        "module_path": ".gematria_sum",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects words where A + B = C in gematria",
    },

    # ── Linguistic ──

    {
        "name": "Same Root — Triconsonantal Roots",
        "module_path": ".same_root",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses sharing the same triconsonantal Hebrew root",
    },
    {
        "name": "Staircase Chains — Word-Link Structures",
        "module_path": ".staircase_chains",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects staircase parallelism (last word of one line = first word of next)",
    },
    {
        "name": "Hendiadys — Two Words, One Idea",
        "module_path": ".hendiadys",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects hendiadys: two words expressing one idea",
    },
    {
        "name": "Morphology — Grammatical Forms",
        "module_path": ".morphology",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses sharing the same grammatical form (verb stem, tense, etc.)",
    },

    # ── Chronological ──

    {
        "name": "Genealogical — Family Lines",
        "module_path": ".genealogical",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects genealogical passages and family lineage references",
    },
    {
        "name": "Chronological Markers — Time References",
        "module_path": ".chronological_marker",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses sharing chronological markers (regn years, feast days, etc.)",
    },
    {
        "name": "Cyclical Time — Jubilee/Sabbatical Cycles",
        "module_path": ".cyclical_time",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through sabbatical and jubilee cycle references",
    },
    {
        "name": "Feast Connections — Holy Days",
        "module_path": ".feast_connection",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses mentioning the same biblical feast or holy day",
    },
    {
        "name": "Mukdam u'Meuchar — Non-Chronological Order",
        "module_path": ".mukdam_umeuchar",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects non-chronological order passages in narrative",
    },

    # ── Geographic ──

    {
        "name": "Geographic — Location Subtypes",
        "module_path": ".geographic_subtypes",
        "layers": ["geographic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Refines geographic connections with location subtypes (wilderness, mountain, temple)",
    },

    # ── Interpretive ──

    {
        "name": "Interpretive — Traditonal Readings",
        "module_path": ".interpretive",
        "layers": ["interpretive"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through shared interpretive traditions",
    },

    # ── Hebrew Language Tools ──

    {
        "name": "Kal v'Chomer — Light/Heavy Argument",
        "module_path": ".kal_vchomer",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Detects kal v'chomer (light to heavy) argument patterns",
    },
    {
        "name": "Semuchin — Adjacent Verses",
        "module_path": ".semuchin",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects adjacent verses that share lemma-based links",
    },

    # ── Cross-Canon (Extended Connections) ──

    {
        "name": "Cross-Canon Chaos Motifs",
        "module_path": ".cross_canon_chaos",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Applies Isaiah's de-creation motifs (dust, chaff, stubble) to other books",
    },
    {
        "name": "Cross-Canon Pseudonyms",
        "module_path": ".cross_canon_pseudonyms",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Extends Giliadi's pseudonym keyword system beyond Isaiah",
    },
    {
        "name": "Cross-Canon Experiment — Unknown Psalms",
        "module_path": ".experiment_cross_canon",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Experimental: connects 5 Psalms of David to canon parallels",
    },

    # ── Isaiah-Specific (scoped to book=isa) ──

    {
        "name": "Isaiah — Advanced Giliadi Techniques",
        "module_path": ".isaiah_advanced",
        "layers": ["structural", "symbolic", "chronological"],
        "automatic": True,
        "requires": "verses table (present), book=isa",
        "description": "Seeds 11 Giliadi techniques: Day of Jehovah, threats, curses↔blessings, cyclical types, DSS markers",
    },
    {
        "name": "Isaiah — Hebrew Keyword Linking",
        "module_path": ".isaiah_keywords",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present), book=isa",
        "description": "Hebrew keyword discovery from Isaiah's 7-part parallel structure",
    },
    {
        "name": "Isaiah — Pseudonym Twin-Pairs",
        "module_path": ".isaiah_pseudonyms",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present), book=isa",
        "description": "Connects pseudonym occurrences (hand/rod/sword) to servant/tyrant hubs",
    },
    {
        "name": "Spiritual Levels — Giliadi's 7-Level Framework",
        "module_path": ".spiritual_levels",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "gematria table (present), book=isa",
        "description": "Classifies Isaiah verses into 7 spiritual levels (Perdition→Jehovah)",
    },
]

# Import all generator modules
def _import_all():
    for gen_def in GENERATOR_DEFS:
        module_path = gen_def["module_path"]
        try:
            module = importlib.import_module(module_path, package="generators")
            gen_def["module"] = module
            gen_def["loaded"] = True
        except Exception as e:
            gen_def["module"] = None
            gen_def["loaded"] = False
            gen_def["load_error"] = str(e)


def run_generator(conn, name, book_ids=None):
    """Run a single generator by name."""
    for gen in GENERATOR_DEFS:
        if gen["name"] == name:
            if not gen.get("loaded"):
                return {"error": f"Generator '{name}' not loaded: {gen.get('load_error', 'unknown')}"}
            try:
                count = gen["module"].run(conn, book_ids)
                conn.commit()
                return {"generator": name, "connections": count, "layers": gen["layers"]}
            except Exception as e:
                conn.rollback()
                return {"error": f"Generator '{name}' failed: {e}"}
    return {"error": f"Generator '{name}' not found"}


def run_all(conn, book_ids=None, automatic_only=True):
    """Run all loaded generators and return stats."""
    results = []
    for gen in GENERATOR_DEFS:
        if automatic_only and not gen["automatic"]:
            continue
        if not gen.get("loaded"):
            results.append({"generator": gen["name"], "status": "skipped", "error": gen.get("load_error", "not loaded")})
            continue
        try:
            count = gen["module"].run(conn, book_ids)
            conn.commit()
            results.append({"generator": gen["name"], "connections": count, "layers": gen["layers"], "status": "ok"})
        except Exception as e:
            conn.rollback()
            results.append({"generator": gen["name"], "status": "error", "error": str(e)})
    return results


def list_generators():
    """List all registered generators and their status."""
    return [
        {
            "name": g["name"],
            "layers": g["layers"],
            "automatic": g["automatic"],
            "requires": g["requires"],
            "description": g["description"],
            "loaded": g.get("loaded", False),
        }
        for g in GENERATOR_DEFS
    ]


# Import all at module load
_import_all()
