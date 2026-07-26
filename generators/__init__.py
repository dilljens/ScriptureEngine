"""Connection generator registry.

Each generator module exports a `run(conn, book_ids=None) -> int` function.
The registry discovers all generators and provides a unified runner.
"""

import hashlib
import importlib
import time

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
        "tier": "idle",
        "cost": "free",
        "precision": 0.82,
        "avg_run_time_s": 120,
    },
    {
        "name": "Structural — Chiastic Pairs",
        "module_path": ".structural",
        "layers": ["structural"],
        "automatic": True,
        "requires": "known_chiasms table + chiastic detector",
        "description": "Connects A↔A', B↔B' pairs from known and detected chiasms",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.95,
        "avg_run_time_s": 2,
    },
    {
        "name": "Intertextual — Quotation Detection",
        "module_path": ".intertextual",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through shared rare-word clusters indicating quotations/allusions",
        "tier": "periodic",
        "cost": "free",
        "precision": 0.71,
        "avg_run_time_s": 480,
    },
    {
        "name": "Frequency — Distribution",
        "module_path": ".frequency",
        "layers": ["frequency"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses with shared word frequency patterns",
        "tier": "idle",
        "cost": "free",
        "precision": 0.88,
        "avg_run_time_s": 45,
    },
    {
        "name": "Geographic — Location",
        "module_path": ".geographic",
        "layers": ["geographic"],
        "automatic": False,
        "requires": "place name gazetteer (simple seed included)",
        "description": "Connects verses mentioning the same biblical location",
        "tier": "idle",
        "cost": "free",
        "precision": 0.85,
        "avg_run_time_s": 30,
    },
    {
        "name": "Numerical — Full Gematria",
        "module_path": ".numerical_full",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Expands gematria connections beyond divine names to all sacred numbers and value matches",
        "tier": "idle",
        "cost": "free",
        "precision": 0.93,
        "avg_run_time_s": 90,
    },

    # ── Sod Layer Generators (Scholar Frameworks) ──

    {
        "name": "Divine Council — Heiser Framework",
        "module_path": ".heiser_divine_council",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects divine council passages (sons of God, heavenly court, territorial spirits) following Michael Heiser's framework",
        "tier": "idle",
        "cost": "free",
        "precision": 0.79,
        "avg_run_time_s": 60,
    },
    {
        "name": "Temple-Creation — Beale Framework",
        "module_path": ".beale_temple_creation",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects temple/tabernacle passages to creation typology following G.K. Beale's framework",
        "tier": "idle",
        "cost": "free",
        "precision": 0.82,
        "avg_run_time_s": 60,
    },
    {
        "name": "Angel of YHWH — Barker Framework",
        "module_path": ".barker_angel_yhwh",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects Angel of YHWH, Day of Atonement, and temple microcosm passages following Margaret Barker's Temple Theology",
        "tier": "idle",
        "cost": "free",
        "precision": 0.84,
        "avg_run_time_s": 60,
    },
    {
        "name": "Merkabah — Orlov/Schäfer Framework",
        "module_path": ".orlov_merkabah",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects throne visions, heavenly ascent, and two-powers passages following Orlov and Schäfer's merkabah tradition",
        "tier": "idle",
        "cost": "free",
        "precision": 0.77,
        "avg_run_time_s": 60,
    },
    {
        "name": "Temple Themes — Living Water, Throne, Veil, Creation, Center",
        "module_path": ".temple_themes",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects passages for 5 empty sod types: living water, temple throne, temple veil, primordial creation, sacred center",
        "tier": "idle",
        "cost": "free",
        "precision": 0.81,
        "avg_run_time_s": 45,
    },

    # ── Orphan Generators (Structural + Frequency) ──

    {
        "name": "Chiasm Detection — Algorithmic",
        "module_path": ".chiasm_detector",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Algorithmic chiastic structure detection on each book",
        "tier": "idle",
        "cost": "free",
        "precision": 0.73,
        "avg_run_time_s": 180,
    },
    {
        "name": "Formula Markers — Structural Seams",
        "module_path": ".formula_markers",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects formula markers ('And it came to pass', 'Thus says the Lord') as structural seams",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.91,
        "avg_run_time_s": 5,
    },
    {
        "name": "Refrain Detection — Repeated Phrases",
        "module_path": ".refrain",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Finds repeated phrases at structural intervals across books",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.87,
        "avg_run_time_s": 8,
    },
    {
        "name": "Parallelism — Poetic Structures",
        "module_path": ".parallelism",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects synonymous, antithetic, synthetic, and step parallelism",
        "tier": "idle",
        "cost": "free",
        "precision": 0.76,
        "avg_run_time_s": 120,
    },
    {
        "name": "Acrostic Detection",
        "module_path": ".acrostic",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects alphabetic/acrostic structures in Hebrew poetry",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.94,
        "avg_run_time_s": 3,
    },
    {
        "name": "Hapax & Dislegomenon",
        "module_path": ".hapax_dislegomenon",
        "layers": ["frequency"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses through rare words (hapax legomena and dislegomena)",
        "tier": "idle",
        "cost": "free",
        "precision": 0.85,
        "avg_run_time_s": 40,
    },

    # ── Ordinal + Reduced Gematria ──

    {
        "name": "Ordinal & Reduced Gematria",
        "module_path": ".ordinal_reduced_gematria",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Adds ordinal and reduced gematria connections",
        "tier": "idle",
        "cost": "free",
        "precision": 0.92,
        "avg_run_time_s": 90,
    },
    {
        "name": "Gematria Factor — Sacred Number Factors",
        "module_path": ".gematria_factor",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses where gematria values factor into sacred numbers",
        "tier": "idle",
        "cost": "free",
        "precision": 0.89,
        "avg_run_time_s": 60,
    },
    {
        "name": "Gematria Sum — Word Relationships",
        "module_path": ".gematria_sum",
        "layers": ["numerical"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects words where A + B = C in gematria",
        "tier": "idle",
        "cost": "free",
        "precision": 0.88,
        "avg_run_time_s": 60,
    },

    # ── Linguistic ──

    {
        "name": "Same Root — Triconsonantal Roots",
        "module_path": ".same_root",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses sharing the same triconsonantal Hebrew root",
        "tier": "idle",
        "cost": "free",
        "precision": 0.83,
        "avg_run_time_s": 80,
    },
    {
        "name": "Staircase Chains — Word-Link Structures",
        "module_path": ".staircase_chains",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects staircase parallelism (last word of one line = first word of next)",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.9,
        "avg_run_time_s": 4,
    },
    {
        "name": "Hendiadys — Two Words, One Idea",
        "module_path": ".hendiadys",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects hendiadys: two words expressing one idea",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.92,
        "avg_run_time_s": 3,
    },
    {
        "name": "Morphology — Grammatical Forms",
        "module_path": ".morphology",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects verses sharing the same grammatical form (verb stem, tense, etc.)",
        "tier": "idle",
        "cost": "free",
        "precision": 0.8,
        "avg_run_time_s": 70,
    },

    # ── Chronological ──

    {
        "name": "Genealogical — Family Lines",
        "module_path": ".genealogical",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects genealogical passages and family lineage references",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.93,
        "avg_run_time_s": 6,
    },
    {
        "name": "Chronological Markers — Time References",
        "module_path": ".chronological_marker",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses sharing chronological markers (regn years, feast days, etc.)",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.9,
        "avg_run_time_s": 5,
    },
    {
        "name": "Cyclical Time — Jubilee/Sabbatical Cycles",
        "module_path": ".cyclical_time",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through sabbatical and jubilee cycle references",
        "tier": "idle",
        "cost": "free",
        "precision": 0.86,
        "avg_run_time_s": 30,
    },
    {
        "name": "Feast Connections — Holy Days",
        "module_path": ".feast_connection",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses mentioning the same biblical feast or holy day",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.94,
        "avg_run_time_s": 4,
    },
    {
        "name": "Mukdam u'Meuchar — Non-Chronological Order",
        "module_path": ".mukdam_umeuchar",
        "layers": ["chronological"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Detects non-chronological order passages in narrative",
        "tier": "idle",
        "cost": "free",
        "precision": 0.78,
        "avg_run_time_s": 25,
    },

    # ── Geographic ──

    {
        "name": "Geographic — Location Subtypes",
        "module_path": ".geographic_subtypes",
        "layers": ["geographic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Refines geographic connections with location subtypes (wilderness, mountain, temple)",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.91,
        "avg_run_time_s": 5,
    },

    # ── Interpretive ──

    {
        "name": "Interpretive — Traditonal Readings",
        "module_path": ".interpretive",
        "layers": ["interpretive"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses through shared interpretive traditions",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.95,
        "avg_run_time_s": 2,
    },

    # ── Hebrew Language Tools ──

    {
        "name": "Kal v'Chomer — Light/Heavy Argument",
        "module_path": ".kal_vchomer",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Detects kal v'chomer (light to heavy) argument patterns",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.89,
        "avg_run_time_s": 4,
    },
    {
        "name": "Semuchin — Adjacent Verses",
        "module_path": ".semuchin",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present)",
        "description": "Connects adjacent verses that share lemma-based links",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.84,
        "avg_run_time_s": 10,
    },

    # ── Cross-Canon (Extended Connections) ──

    {
        "name": "Cross-Canon Chaos Motifs",
        "module_path": ".cross_canon_chaos",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Applies Isaiah's de-creation motifs (dust, chaff, stubble) to other books",
        "tier": "idle",
        "cost": "free",
        "precision": 0.75,
        "avg_run_time_s": 120,
    },
    {
        "name": "Cross-Canon Pseudonyms",
        "module_path": ".cross_canon_pseudonyms",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Extends Giliadi's pseudonym keyword system beyond Isaiah",
        "tier": "idle",
        "cost": "free",
        "precision": 0.78,
        "avg_run_time_s": 100,
    },
    {
        "name": "Cross-Canon Experiment — Unknown Psalms",
        "module_path": ".experiment_cross_canon",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Experimental: connects 5 Psalms of David to canon parallels",
        "tier": "idle",
        "cost": "free",
        "precision": 0.7,
        "avg_run_time_s": 60,
    },

    # ── Sod Fill (sparse connection types) ──

    {
        "name": "Sod Fill — Sparse Connection Types",
        "module_path": ".sod_fill",
        "layers": ["sod"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Fills sparse sod connection types: mercy_seat, heavenly_council, theophany, divine_mediator, holy_of_holies, kingdom_priesthood, divine_marriage, theosis, angelophany",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.86,
        "avg_run_time_s": 6,
    },

# ── Phrase + Title + Typology + Inclusio (New) ──

    {
        "name": "Divine Titles — Epithets for God",
        "module_path": ".divine_titles",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses sharing the same divine title/epithet (Holy One of Israel, Lord of Hosts, Rock of Israel, etc.)",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.93,
        "avg_run_time_s": 5,
    },
    {
        "name": "Typology — Type/Antitype Pairs",
        "module_path": ".typology",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects OT types to their NT antitypes (Adam→Christ, Passover→Crucifixion, Bronze Serpent→Cross)",
        "tier": "idle",
        "cost": "free",
        "precision": 0.87,
        "avg_run_time_s": 35,
    },
    {
        "name": "Phrase Match — Hebrew + English Key Phrases",
        "module_path": ".phrase_match",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Connects verses sharing significant multi-word phrases (son of man, day of the Lord, living water)",
        "tier": "idle",
        "cost": "free",
        "precision": 0.84,
        "avg_run_time_s": 40,
    },
    {
        "name": "Inclusio Detection — Repeated Phrases Bookending",
        "module_path": ".structural_inclusio",
        "layers": ["structural"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Finds repeated phrases at beginning and end of literary units",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.88,
        "avg_run_time_s": 8,
    },

# ── Isaiah-Specific (scoped to book=isa) ──

    {
        "name": "Isaiah — Advanced Giliadi Techniques",
        "module_path": ".isaiah_advanced",
        "layers": ["structural", "symbolic", "chronological"],
        "automatic": True,
        "requires": "verses table (present), book=isa",
        "description": "Seeds 11 Giliadi techniques: Day of Jehovah, threats, curses↔blessings, cyclical types, DSS markers",
        "tier": "idle",
        "cost": "free",
        "precision": 0.76,
        "avg_run_time_s": 90,
    },
    {
        "name": "Isaiah — Hebrew Keyword Linking",
        "module_path": ".isaiah_keywords",
        "layers": ["linguistic"],
        "automatic": True,
        "requires": "gematria table (present), book=isa",
        "description": "Hebrew keyword discovery from Isaiah's 7-part parallel structure",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.9,
        "avg_run_time_s": 10,
    },
    {
        "name": "Isaiah — Pseudonym Twin-Pairs",
        "module_path": ".isaiah_pseudonyms",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "verses table (present), book=isa",
        "description": "Connects pseudonym occurrences (hand/rod/sword) to servant/tyrant hubs",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.88,
        "avg_run_time_s": 8,
    },
    {
        "name": "Spiritual Levels — Giliadi's 7-Level Framework",
        "module_path": ".spiritual_levels",
        "layers": ["symbolic"],
        "automatic": True,
        "requires": "gematria table (present), book=isa",
        "description": "Classifies Isaiah verses into 7 spiritual levels (Perdition→Jehovah)",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.85,
        "avg_run_time_s": 6,
    },
    # ── Passage-level (macro-structural) ────────────────────────────────
    {
        "name": "Passage — Density Cluster",
        "module_path": ".passage.density_cluster",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "connections table (present)",
        "description": "Finds passage pairs with high connection density by sliding-window aggregation of verse-level connections.",
        "tier": "idle",
        "cost": "free",
        "precision": 0.8,
        "avg_run_time_s": 30,
    },
    {
        "name": "Passage — Book Coherence",
        "module_path": ".passage.book_coherence",
        "layers": ["intertextual"],
        "automatic": True,
        "requires": "connections table (present)",
        "description": "Aggregates verse-level connections into book-level summaries showing inter-book connection strengths.",
        "tier": "idle",
        "cost": "free",
        "precision": 0.75,
        "avg_run_time_s": 60,
    },
    {
        "name": "Passage — Chiastic Promoter",
        "module_path": ".passage.chiastic_promoter",
        "layers": ["structural"],
        "automatic": True,
        "requires": "known_chiasms table (populated)",
        "description": "Elevates known chiastic structures to passage-level connections with labeled parallel sections.",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.92,
        "avg_run_time_s": 5,
    },
    {
        "name": "Passage — Genre Tagger",
        "module_path": ".passage.genre_tagger",
        "layers": ["interpretive"],
        "automatic": True,
        "requires": "verses table (present)",
        "description": "Classifies passages by literary genre and creates same-genre passage connections across the canon.",
        "tier": "lightweight",
        "cost": "free",
        "precision": 0.83,
        "avg_run_time_s": 8,
    },
    {
        "name": "Passage — Theme Tracer",
        "module_path": ".passage.theme_tracer",
        "layers": ["interpretive"],
        "automatic": True,
        "requires": "verses table (present), text_english column",
        "description": "Traces 16 biblical themes (temple, covenant, exile, etc.) through the canon and creates passage-level connections between same-theme passages.",
        "tier": "idle",
        "cost": "free",
        "precision": 0.81,
        "avg_run_time_s": 45,
    },
    # ── Kabbalistic ─────────────────────────────────────────────────────
    {
        "name": "Sefirot — Kabbalistic Tree of Life",
        "module_path": ".sefirot_mapper",
        "layers": ["symbolic", "sod"],
        "automatic": True,
        "requires": "gematria table (present), verses table (present)",
        "description": "Tags verses with sefirah labels (10 sefirot of the Kabbalistic tree of life) using Hebrew/English keyword matching, and creates connections between verses sharing a sefirah label.",
        "tier": "idle",
        "cost": "free",
        "precision": 0.79,
        "avg_run_time_s": 30,
    }
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


def _compute_source_hash(conn, gen_def):
    """Compute a quick hash of source tables for change detection.

    Hashes the row count of the generator's primary input table(s).
    Used to skip re-generation when data hasn't changed.
    """
    requires = gen_def.get("requires", "")
    # Map requirements to tables we can hash
    table_map = {
        "gematria": "gematria",
        "verses": "verses",
        "connections": "connections",
        "known_chiasms": "known_chiasms",
        "structural_formulas": "structural_formulas",
    }
    hash_input = ""
    for key, table in table_map.items():
        if key in requires:
            try:
                row = conn.execute(f"SELECT COUNT(*) as c, COALESCE(MAX(rowid), 0) as m FROM {table}").fetchone()
                hash_input += f"{table}:{row['c']}:{row['m']};"
            except Exception:
                hash_input += f"{table}:0;"
    return hashlib.md5(hash_input.encode()).hexdigest()[:12] if hash_input else ""


def _record_generator_run(conn, gen_def, count, duration_ms):
    """Record generator run in generator_meta table."""
    try:
        source_hash = _compute_source_hash(conn, gen_def)
        conn.execute("""
            INSERT OR REPLACE INTO generator_meta
            (generator_name, last_run_at, source_hash, connection_count, duration_ms)
            VALUES (?, datetime('now'), ?, ?, ?)
        """, (gen_def["name"], source_hash, count, duration_ms))
    except Exception:
        pass


def _should_skip_generator(conn, gen_def):
    """Check if generator can be skipped (data hasn't changed since last run)."""
    try:
        row = conn.execute(
            "SELECT source_hash FROM generator_meta WHERE generator_name = ?",
            (gen_def["name"],),
        ).fetchone()
        if row is None:
            return False  # Never run — must run
        current_hash = _compute_source_hash(conn, gen_def)
        return current_hash == row["source_hash"]
    except Exception:
        return False


def run_generator(conn, name, book_ids=None):
    """Run a single generator by name."""
    for gen in GENERATOR_DEFS:
        if gen["name"] == name:
            if not gen.get("loaded"):
                return {"error": f"Generator '{name}' not loaded: {gen.get('load_error', 'unknown')}"}
            t0 = time.time()
            try:
                count = gen["module"].run(conn, book_ids)
                conn.commit()
                duration_ms = int((time.time() - t0) * 1000)
                _record_generator_run(conn, gen, count, duration_ms)
                conn.commit()
                return {"generator": name, "connections": count, "layers": gen["layers"]}
            except Exception as e:
                conn.rollback()
                return {"error": f"Generator '{name}' failed: {e}"}
    return {"error": f"Generator '{name}' not found"}


def run_all(conn, book_ids=None, automatic_only=True, incremental=False):
    """Run all loaded generators and return stats.

    Args:
        conn: SQLite connection
        book_ids: Optional list of book IDs to scope generation
        automatic_only: Skip non-automatic generators
        incremental: If True, skip generators whose source data hasn't changed

    Returns:
        list of result dicts
    """
    results = []
    for gen in GENERATOR_DEFS:
        if automatic_only and not gen["automatic"]:
            continue
        if not gen.get("loaded"):
            results.append({"generator": gen["name"], "status": "skipped", "error": gen.get("load_error", "not loaded")})
            continue

        # Incremental: skip if source data unchanged
        if incremental and _should_skip_generator(conn, gen):
            results.append({"generator": gen["name"], "status": "skipped", "reason": "source unchanged since last run"})
            continue

        t0 = time.time()
        try:
            count = gen["module"].run(conn, book_ids)
            conn.commit()
            duration_ms = int((time.time() - t0) * 1000)
            _record_generator_run(conn, gen, count, duration_ms)
            conn.commit()
            results.append({"generator": gen["name"], "connections": count, "layers": gen["layers"], "status": "ok"})
        except Exception as e:
            conn.rollback()
            results.append({"generator": gen["name"], "status": "error", "error": str(e)})
    return results


def fire_lightweight_hooks(conn, source_verse, target_verse):
    """Fire lightweight discovery hooks after a connection is added.

    Runs targeted SQL checks against the source/target verse pair to find
    additional shared patterns. Results go to staging_connections for review.

    Only fires generators marked tier='lightweight' and automatic=True.

    Args:
        conn: SQLite connection.
        source_verse: Source verse ID.
        target_verse: Target verse ID.

    Returns:
        dict with {'hooks_fired': int, 'new_suggestions': int}
    """
    hooks_fired = 0
    new_suggestions = 0

    for gen in GENERATOR_DEFS:
        if not gen.get("loaded"):
            continue
        if not gen.get("automatic", False):
            continue
        if gen.get("tier") != "lightweight":
            continue

        try:
            # Each lightweight generator that supports hooks receives
            # a per-connection call. Only fire if the module has a
            # hook_connection function.
            module = gen.get("module")
            if module is None:
                continue
            hook_fn = getattr(module, "hook_connection", None)
            if hook_fn is None:
                continue

            count = hook_fn(conn, source_verse, target_verse)
            if count > 0:
                conn.commit()
                new_suggestions += count
            hooks_fired += 1
        except Exception:
            conn.rollback()
            continue

    return {"hooks_fired": hooks_fired, "new_suggestions": new_suggestions}


def list_generators(tier=None, cost=None, automatic_only=False):
    """List all registered generators and their status.

    Args:
        tier: Optional filter — 'lightweight', 'idle', or 'periodic'.
        cost: Optional filter — 'free', 'llm_call', or 'external_api'.
        automatic_only: If True, only include automatic generators.

    Returns:
        List of generator metadata dicts.
    """
    result = []
    for g in GENERATOR_DEFS:
        if automatic_only and not g["automatic"]:
            continue
        if tier and g.get("tier") != tier:
            continue
        if cost and g.get("cost") != cost:
            continue
        result.append({
            "name": g["name"],
            "layers": g["layers"],
            "automatic": g["automatic"],
            "tier": g.get("tier", "idle"),
            "cost": g.get("cost", "free"),
            "precision": g.get("precision"),
            "avg_run_time_s": g.get("avg_run_time_s"),
            "requires": g["requires"],
            "description": g["description"],
            "loaded": g.get("loaded", False),
        })
    return result


# Import all at module load
_import_all()
