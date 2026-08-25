"""Track B regression tests: gematria evidence ceiling and stop-list.

An exact gematria match is bounded candidate numerical evidence. It must
never be promotable above the 'suggested' band, never outrank direct
textual evidence, and retired scan types must stay neutralized until the
archive/purge migration (plan: ai-truth-gematria-hebrew-tutor.md, Track B).
"""

import sqlite3

from lib.controls import calibration
from lib.controls.propagation import path_confidence


# ── Calibration ceilings ──────────────────────────────────────────────

MAX_BOOSTS = dict(
    discovered_by="text",       # strongest discovery LR (20x)
    has_reasoning=True,         # 2x
    confidence=0.99,
    confirmation_count={"expert_review": 10, "scholar_cite": 10},  # max feedback
    p_value=0.0001,             # 20x
    agreement_count=10,         # 4x
    generator_precision=1.0,    # 2x
)


def test_retained_exact_match_capped_below_probable():
    """Even with every boost signal maxed, an exact gematria match stays a candidate."""
    result = calibration.rate_connection(
        connection_type="same_gematria_standard", **MAX_BOOSTS
    )
    assert result["evidence_class"] == "numerical_candidate"
    assert result["quality_score"] <= calibration.NUMERICAL_MAX_QUALITY
    assert result["quality_score"] < 60  # never reaches 'probable'
    assert result["ceiling_applied"] is True


def test_divine_name_value_also_capped():
    result = calibration.rate_connection(
        connection_type="divine_name_value", **MAX_BOOSTS
    )
    assert result["evidence_class"] == "numerical_candidate"
    assert result["quality_score"] <= calibration.NUMERICAL_MAX_QUALITY


def test_retired_types_neutral_and_hard_capped():
    for conn_type in sorted(calibration.RETIRED_NUMERICAL_TYPES):
        result = calibration.rate_connection(
            connection_type=conn_type,
            discovered_by="text",
            has_reasoning=True,
            p_value=0.0001,
            agreement_count=10,
        )
        assert result["evidence_class"] == "numerical_retired", conn_type
        # Neutral LR: type contributes nothing regardless of TYPE_LR table
        assert result["signals"]["type_lr"] == 1.0, conn_type
        assert result["quality_score"] <= calibration.RETIRED_NUMERICAL_MAX_QUALITY
        assert result["tier"] == "speculative"


def test_textual_evidence_outranks_numerical_candidate():
    """Same signals: direct quotation beats an exact gematria match."""
    textual = calibration.rate_connection(
        connection_type="direct_quotation", **MAX_BOOSTS
    )
    numerical = calibration.rate_connection(
        connection_type="same_gematria_standard", **MAX_BOOSTS
    )
    assert textual["quality_score"] > numerical["quality_score"]
    assert textual["evidence_class"] is None
    assert numerical["evidence_class"] == "numerical_candidate"


def test_enrich_connection_exposes_evidence_class():
    conn = {
        "discovered_by": "algorithm",
        "type": "gematria_factor",
        "confidence": 0.9,
        "metadata": "{}",
        "agreement_count": 3,
    }
    enriched = calibration.enrich_connection(conn)
    assert enriched["evidence_class"] == "numerical_retired"
    assert enriched["quality_score"] <= calibration.RETIRED_NUMERICAL_MAX_QUALITY
    assert enriched.get("evidence_ceiling") == calibration.RETIRED_NUMERICAL_MAX_QUALITY


def test_non_numerical_types_have_no_class():
    result = calibration.rate_connection(connection_type="same_lemma")
    assert result["evidence_class"] is None
    assert result["evidence_ceiling"] is None
    assert result["ceiling_applied"] is False


# ── Propagation ceiling ───────────────────────────────────────────────

def test_all_numerical_path_capped():
    path = [
        {"confidence": 0.9, "layer": "numerical", "type": "same_gematria_standard"},
        {"confidence": 0.9, "layer": "numerical", "type": "same_gematria_standard"},
    ]
    propagated = path_confidence(path)
    assert propagated <= 0.35


def test_retired_numerical_path_capped_harder():
    path = [
        {"confidence": 0.9, "layer": "numerical", "type": "sacred_number"},
        {"confidence": 0.9, "layer": "numerical", "type": "sacred_number"},
    ]
    assert path_confidence(path) <= 0.10


def test_mixed_path_not_numerically_capped():
    # Same-layer linguistic hops keep natural compatibility (1.0) and are
    # not subject to the numerical-only ceiling.
    path = [
        {"confidence": 0.9, "layer": "linguistic", "type": "same_lemma"},
        {"confidence": 0.9, "layer": "linguistic", "type": "same_root"},
    ]
    propagated = path_confidence(path)
    assert propagated > 0.35


# ── Generator stop-list ───────────────────────────────────────────────

def _memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE gematria (
            verse_id TEXT, word_hebrew TEXT, value_standard INTEGER,
            value_ordinal INTEGER DEFAULT 0, value_reduced INTEGER DEFAULT 0
        );
        CREATE TABLE connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_verse TEXT, target_verse TEXT, layer TEXT, type TEXT,
            subtype TEXT DEFAULT '', strength REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5, discovered_by TEXT DEFAULT 'algorithm',
            metadata TEXT DEFAULT '{}',
            UNIQUE (source_verse, target_verse, layer, type, subtype)
        );
        CREATE TABLE staging_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_verse TEXT, target_verse TEXT, layer TEXT, type TEXT,
            subtype TEXT DEFAULT '', strength REAL DEFAULT 0.5,
            confidence REAL DEFAULT 0.5, discovered_by TEXT DEFAULT 'algorithm',
            metadata TEXT DEFAULT '{}', status TEXT DEFAULT 'pending'
        );
    """)
    return conn


def test_retired_generator_modules_refuse_to_generate():
    from generators import gematria_sum, gematria_factor

    conn = _memory_db()
    assert gematria_sum.run(conn) == 0
    assert gematria_factor.run(conn) == 0
    assert conn.execute("SELECT COUNT(*) c FROM connections").fetchone()["c"] == 0


def test_numerical_full_no_longer_emits_sacred_number():
    from generators import numerical_full

    conn = _memory_db()
    # Two verses each containing one word valued 100 — a shared rare value
    conn.executemany(
        "INSERT INTO gematria (verse_id, word_hebrew, value_standard) VALUES (?,?,?)",
        [("gen.1.1", "w100", 100), ("gen.1.2", "w100", 100)],
    )
    numerical_full.run(conn)

    types = {r["type"] for r in conn.execute("SELECT DISTINCT type FROM connections")}
    assert "sacred_number" not in types
    assert types == {"same_gematria_standard"}
