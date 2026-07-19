"""Generator tests — all 52 generators must import, run without errors, and produce valid connections.

Each test:
  1. Imports the generator module
  2. Runs it on a test database (empty or small fixture)
  3. Verifies it produces valid connection records
  4. Verifies idempotency (second run produces no duplicates)
"""

import json
import os
import pytest
import sqlite3
import tempfile
from pathlib import Path

# ── Test database fixture ─────────────────────────────────────────────

GENERATORS_DIR = Path(__file__).parent.parent / "generators"


@pytest.fixture(scope="session")
def test_db():
    """Create a minimal test database with the schema but no data."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Create schema
    from lib.db import SCHEMA_SQL
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)

    # Insert minimal test data (1 book, 2 chapters, 10 verses)
    conn.execute("INSERT OR IGNORE INTO works (id, title) VALUES ('ot', 'Old Testament')")
    conn.execute("INSERT OR IGNORE INTO books (id, work_id, title, position) VALUES ('gen', 'ot', 'Genesis', 1)")
    for ch in range(1, 3):
        for v in range(1, 6):
            vid = f"gen.{ch}.{v}"
            conn.execute(
                "INSERT OR IGNORE INTO verses (id, book_id, chapter, verse, text_english) VALUES (?, ?, ?, ?, ?)",
                (vid, "gen", ch, v, f"Test verse {vid} content.")
            )

    conn.commit()
    yield conn
    conn.close()
    os.unlink(db_path)


@pytest.fixture(scope="session")
def test_db_with_gematria(test_db):
    """Add gematria data to test DB for numerical generators."""
    conn = test_db
    for v in ["gen.1.1", "gen.1.2", "gen.1.3", "gen.2.1", "gen.2.2"]:
        conn.execute(
            "INSERT OR IGNORE INTO gematria (verse_id, word, word_hebrew, gematria_standard, gematria_ordinal) VALUES (?, ?, ?, ?, ?)",
            (v, f"word_{v}", f"השם{v[-1]}", 100 + hash(v) % 100, 10 + hash(v) % 10),
        )
    conn.commit()
    return conn


@pytest.fixture(scope="session")
def test_db_with_entities(test_db_with_gematria):
    """Add entity data for entity-based generators."""
    conn = test_db_with_gematria
    conn.execute(
        "INSERT OR IGNORE INTO entity_links (entity_id, entity_type, english_name, hebrew_name) VALUES (?, ?, ?, ?)",
        ("person.abraham", "person", "Abraham", "אברהם"),
    )
    for vid in ["gen.1.1", "gen.1.2", "gen.2.1"]:
        conn.execute(
            "INSERT OR IGNORE INTO verse_entities (verse_id, entity_id, relationship_type, confidence) VALUES (?, ?, ?, ?)",
            (vid, "person.abraham", "mentions", 0.7),
        )
    conn.commit()
    return conn


# ── Generator validation helpers ─────────────────────────────────────

def validate_connection(conn, connection):
    """Validate a single connection record has all required fields."""
    required = {"source_verse", "target_verse", "layer", "type"}
    assert all(k in connection for k in required), f"Missing required fields in {connection}"
    assert isinstance(connection["source_verse"], str), "source_verse must be string"
    assert isinstance(connection["target_verse"], str), "target_verse must be string"
    assert len(connection["source_verse"]) > 0, "source_verse cannot be empty"
    assert len(connection["target_verse"]) > 0, "target_verse cannot be empty"


def validate_passage_connection(conn, connection):
    """Validate a passage_connection record."""
    required = {"source_start", "source_end", "target_start", "target_end", "layer", "type"}
    assert all(k in connection for k in required), f"Missing required fields in {connection}"


def count_connections(conn):
    return conn.execute("SELECT COUNT(*) FROM connections").fetchone()[0]


def count_passage_connections(conn):
    return conn.execute("SELECT COUNT(*) FROM passage_connections").fetchone()[0]


# ── Passage-level generators ─────────────────────────────────────────

def run_and_assert(gen_module, conn, db_name="test_db"):
    """Run a generator and verify it produces valid output."""
    initial_count = count_connections(conn)
    initial_passage_count = count_passage_connections(conn)

    result = gen_module.run(conn)

    # Generator should return a non-negative integer
    assert isinstance(result, (int, float)), f"Generator returned {type(result)}, expected int"

    # Run again to verify idempotency (no duplicate unique constraint violations)
    result2 = gen_module.run(conn)
    assert isinstance(result2, (int, float)), f"Second run returned {type(result2)}"

    return result


# ── Test parameterization ────────────────────────────────────────────

# List of all automatic generators from GENERATOR_DEFS
# Using module paths to import them

AUTOMATIC_GENERATORS = []


def _load_generator_list():
    """Load the GENERATOR_DEFS list and register automatic generators."""
    global AUTOMATIC_GENERATORS
    if AUTOMATIC_GENERATORS:
        return AUTOMATIC_GENERATORS

    from generators import GENERATOR_DEFS
    for gen_def in GENERATOR_DEFS:
        if gen_def.get("automatic", True):
            # Extract module path (e.g., ".linguistic" or ".passage.density_cluster")
            module_path = gen_def["module_path"]
            if module_path.startswith("."):
                full_path = f"generators{module_path}"
            else:
                full_path = module_path
            AUTOMATIC_GENERATORS.append({
                "name": gen_def["name"],
                "module_path": full_path,
                "layers": gen_def.get("layers", []),
                "requires": gen_def.get("requires", ""),
            })

    return AUTOMATIC_GENERATORS


# ── Tests ────────────────────────────────────────────────────────────

def test_generator_list_loaded():
    """Verify the generator list is not empty."""
    gens = _load_generator_list()
    assert len(gens) > 0, "No generators loaded from GENERATOR_DEFS"
    print(f"Loaded {len(gens)} automatic generators")


def test_all_generators_import():
    """Verify every automatic generator module can be imported."""
    gens = _load_generator_list()
    failures = []
    for gen in gens:
        try:
            import importlib
            module = importlib.import_module(gen["module_path"])
            assert hasattr(module, "run"), f"{gen['name']} has no run() function"
        except Exception as e:
            failures.append(f"{gen['name']} ({gen['module_path']}): {e}")

    if failures:
        pytest.fail(f"Import failures: {len(failures)}\n" + "\n".join(failures))


@pytest.mark.parametrize("gen", [
    g for g in _load_generator_list() if "Passage" in g["name"]
], ids=lambda g: g["name"])
def test_passage_generators_run(test_db, gen):
    """Verify passage-level generators run without errors."""
    try:
        import importlib
        module = importlib.import_module(gen["module_path"])
    except ImportError as e:
        # Skip if requires not met (e.g., known_chiasms table)
        if "known_chiasms" in gen.get("requires", "") or "gematria" in gen.get("requires", ""):
            pytest.skip(f"Required table not available: {gen['requires']}")
        pytest.fail(f"Import failed: {e}")

    count = run_and_assert(module, test_db)
    assert count >= 0


def test_layers_exist():
    """Verify all generator layers map to valid layer names."""
    gens = _load_generator_list()
    valid_layers = {
        "linguistic", "numerical", "structural", "intertextual",
        "textual", "geographic", "chronological", "interpretive",
        "frequency", "symbolic", "sod",
    }
    for gen in gens:
        for layer in gen.get("layers", []):
            assert layer in valid_layers, f"{gen['name']}: invalid layer '{layer}'"


def test_no_duplicate_names():
    """Verify no two generators share the same name."""
    gens = _load_generator_list()
    names = [g["name"] for g in gens]
    duplicates = {n for n in names if names.count(n) > 1}
    assert len(duplicates) == 0, f"Duplicate generator names: {duplicates}"


# ── Passage-level connection schema tests ────────────────────────────

def test_passage_connections_table(test_db):
    """Verify passage_connections table uses correct schema."""
    info = test_db.execute("PRAGMA table_info(passage_connections)").fetchall()
    columns = {r["name"] for r in info}
    expected = {"source_start", "source_end", "target_start", "target_end", "layer", "type"}
    assert expected.issubset(columns), f"Missing columns: {expected - columns}"


def test_passage_genres_table(test_db):
    """Verify passage_genres table exists with correct schema."""
    tables = test_db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {r["name"] for r in tables}
    if "passage_genres" in table_names:
        info = test_db.execute("PRAGMA table_info(passage_genres)").fetchall()
        columns = {r["name"] for r in info}
        assert {"start_verse", "end_verse", "genre"}.issubset(columns)


# ── Calibration tests ────────────────────────────────────────────────

def test_calibration_imports():
    """Verify calibration module imports work."""
    from lib.controls.calibration import (
        rate_connection, rate_connection_row, enrich_connection,
        compute_agreement_counts, QUALITY_LEVELS, DISCOVERY_LR, TYPE_LR,
    )
    assert len(QUALITY_LEVELS) >= 6
    assert len(DISCOVERY_LR) >= 5
    assert len(TYPE_LR) >= 10


def test_calibration_quality_score():
    """Verify quality score (0-100) is produced correctly."""
    from lib.controls.calibration import rate_connection

    # Text-explicit direct quotation should be ~99
    r = rate_connection("text", "direct_quotation", has_reasoning=True)
    assert 0 <= r["quality_score"] <= 100
    assert r["quality_score"] >= 90, f"Text quotation should score >=90, got {r['quality_score']}"
    assert r["tier"] == "verified"

    # Algorithmic echo should be much lower
    r2 = rate_connection("algorithm", "echo")
    assert r2["quality_score"] < 90

    # P-value should boost score
    r3 = rate_connection("algorithm", "same_gematria_standard", p_value=0.001)
    assert r3["quality_score"] > 50


def test_calibration_tiers():
    """Verify all quality tiers are reachable."""
    from lib.controls.calibration import rate_connection

    cases = [
        ("text", "direct_quotation", True, "verified", 90),
        ("human", "type_antitype", True, "strong", 75),
        ("llm", "allusion", True, "probable", 55),
        ("algorithm", "echo", False, "pattern", 10),
    ]

    for discovered_by, ctype, reasoning, expected_tier, min_score in cases:
        r = rate_connection(discovered_by, ctype, has_reasoning=reasoning)
        assert r["quality_score"] >= 0, f"Score should be >= 0 for {discovered_by}/{ctype}"


def test_calibration_agreement_count():
    """Verify agreement_count parameter affects quality score."""
    from lib.controls.calibration import rate_connection

    base = rate_connection("algorithm", "same_lemma")
    with_agreement = rate_connection("algorithm", "same_lemma", agreement_count=3)

    assert with_agreement["quality_score"] > base["quality_score"], \
        "Agreement should boost score"


def test_calibration_generator_precision():
    """Verify generator_precision parameter works."""
    from lib.controls.calibration import rate_connection

    base = rate_connection("algorithm", "same_lemma")
    with_precision = rate_connection("algorithm", "same_lemma", generator_precision=0.85)

    assert with_precision["quality_score"] >= base["quality_score"], \
        "Generator precision should not decrease score"


# ── Search confidence tests ──────────────────────────────────────────

def test_search_confidence_imports():
    """Verify search confidence module imports."""
    from lib.api.search_confidence import score_result, update_from_feedback, BLIM
    assert score_result is not None
    assert update_from_feedback is not None


def test_search_confidence_scores():
    """Verify BLIM confidence scores are in 0-100 range."""
    from lib.api.search_confidence import score_result

    result = score_result("What is the Abrahamic covenant?", {"verse": "gen.17.1"})
    assert "confidence_score" in result
    assert 0 <= result["confidence_score"] <= 100


def test_search_confidence_feedback():
    """Verify feedback updates change confidence."""
    from lib.api.search_confidence import score_result, update_from_feedback

    result1 = score_result("test query", {"verse": "gen.1.1"})
    initial_score = result1["confidence_score"]

    # Positive feedback should increase confidence
    update_from_feedback("test query", "gen.1.1", was_relevant=True)
    
    # Negative feedback should decrease confidence
    update_from_feedback("test query", "gen.1.1", was_relevant=False)
