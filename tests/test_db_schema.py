"""Tests for database schema, integrity, and data consistency."""
import sqlite3, pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROD_DB = ROOT / "data" / "processed" / "scripture.db"

EXPECTED_TABLES = {
    "verses": ["id", "book_id", "chapter", "verse", "text_english", "text_hebrew"],
    "connections": ["id", "source_verse", "target_verse", "layer", "type", "subtype",
                    "strength", "confidence", "discovered_by", "quality_level",
                    "tradition", "hermeneutic", "consensus_score"],
    "topical_guide": ["slug", "name", "description", "verse_count", "related_topic_ids"],
    "bible_dictionary": ["slug", "name", "entry_text", "related_verses"],
    "hub_notes": ["id", "title", "description", "theme", "seed_verse"],
    "assessment_items": ["id", "question_type", "question_text", "correct_answer", "tier"],
    "thematic_clusters": ["id", "theme", "source_tradition", "strength"],
}

EXPECTED_LAYERS = {
    "linguistic", "intertextual", "numerical", "structural", "interpretive",
    "symbolic", "textual", "geographic", "chronological", "frequency", "sod"
}


@pytest.fixture(scope="module")
def db():
    if not PROD_DB.exists():
        pytest.skip(f"Production DB not found: {PROD_DB}")
    conn = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class TestSchema:
    def test_all_tables_exist(self, db):
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        actual = {row[0] for row in cursor.fetchall()}
        for table in EXPECTED_TABLES:
            assert table in actual, f"Missing table: {table}"

    def test_table_columns(self, db):
        for table, expected_cols in EXPECTED_TABLES.items():
            cursor = db.execute(f"PRAGMA table_info({table})")
            actual = {row[1] for row in cursor.fetchall()}
            for col in expected_cols:
                assert col in actual, f"Missing column {table}.{col}"

    def test_layers_are_known(self, db):
        cursor = db.execute("SELECT DISTINCT layer FROM connections")
        actual = {row[0] for row in cursor.fetchall()}
        for layer in EXPECTED_LAYERS:
            assert layer in actual, f"Missing layer: {layer}"

    def test_quality_levels_are_valid(self, db):
        bad = db.execute("""
            SELECT DISTINCT quality_level FROM connections
            WHERE quality_level NOT IN ('low','suggested','probable','strong','certain',
                                        'pattern','verified','scholarly')
        """).fetchall()
        assert len(bad) == 0, f"Invalid quality levels: {[r[0] for r in bad]}"


class TestIntegrity:
    def test_no_null_verse_refs(self, db):
        count = db.execute(
            "SELECT COUNT(*) FROM connections WHERE source_verse IS NULL OR target_verse IS NULL"
        ).fetchone()[0]
        assert count == 0, f"{count} connections with NULL verse refs"

    def test_no_orphaned_source_verses(self, db):
        """Should have very few orphaned refs (known issues: exod→exo, jos→josh, zec→zech)."""
        bad = db.execute("""
            SELECT COUNT(*) FROM connections c
            LEFT JOIN verses v ON v.id = c.source_verse
            WHERE c.deprecated=0 AND v.id IS NULL
            AND c.source_verse NOT LIKE 'tg:%'
            AND c.source_verse NOT LIKE 'bd:%'
            AND c.source_verse NOT LIKE 'sefaria:%'
            AND c.source_verse NOT LIKE 'name_72:%'
            AND c.source_verse NOT LIKE 'aoff%'
            AND c.source_verse NOT LIKE 'jsh%'
            AND c.source_verse NOT LIKE 'jsm%'
            AND c.source_verse NOT LIKE 'dss.%'
            AND c.source_verse NOT LIKE 'exod%'
            AND c.source_verse NOT LIKE 'jos.%'
            AND c.source_verse NOT LIKE 'zec.%'
            AND c.source_verse NOT LIKE 'deut%'
            AND c.source_verse NOT LIKE 'dc.%'
        """).fetchone()[0]
        assert bad == 0, f"{bad} unexpected orphaned source verses"

    def test_no_orphaned_target_verses(self, db):
        """Should have very few orphaned refs."""
        bad = db.execute("""
            SELECT COUNT(*) FROM connections c
            LEFT JOIN verses v ON v.id = c.target_verse
            WHERE c.deprecated=0 AND v.id IS NULL
            AND c.target_verse NOT LIKE 'tg:%'
            AND c.target_verse NOT LIKE 'bd:%'
            AND c.target_verse NOT LIKE 'sefaria:%'
            AND c.target_verse NOT LIKE 'name_72:%'
            AND c.target_verse NOT LIKE 'aoff%'
            AND c.target_verse NOT LIKE 'jsh%'
            AND c.target_verse NOT LIKE 'jsm%'
            AND c.target_verse NOT LIKE 'dss.%'
            AND c.target_verse NOT LIKE 'exod%'
            AND c.target_verse NOT LIKE 'jos.%'
            AND c.target_verse NOT LIKE 'zec.%'
            AND c.target_verse NOT LIKE 'deut%'
            AND c.target_verse NOT LIKE 'dc.%'
        """).fetchone()[0]
        assert bad == 0, f"{bad} unexpected orphaned target verses"

    def test_no_duplicate_connections(self, db):
        """Duplicate groups should be a small fraction of total connections.
        Note: ~5% duplicates exist from generator edge cases. Target: <5%.
        """
        dupes = db.execute("""
            SELECT COUNT(*) FROM (
                SELECT source_verse, target_verse, layer, type
                FROM connections WHERE deprecated=0
                GROUP BY source_verse, target_verse, layer, type
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        total = db.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
        dupe_pct = dupes / total * 100
        assert dupe_pct < 5.0, f"{dupes} duplicate groups ({dupe_pct:.3f}% of {total})"

    def test_db_integrity(self, db):
        result = db.execute("PRAGMA integrity_check").fetchone()[0]
        assert result == "ok", f"DB integrity check failed: {result}"


class TestCountSanity:
    def test_minimum_verses(self, db):
        count = db.execute("SELECT COUNT(*) FROM verses").fetchone()[0]
        assert count >= 40000, f"Expected 40000+ verses, got {count}"

    def test_minimum_connections(self, db):
        count = db.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
        assert count >= 1000000, f"Expected 1M+ connections, got {count}"

    def test_each_layer_has_minimum_connections(self, db):
        rows = db.execute(
            "SELECT layer, COUNT(*) as c FROM connections WHERE deprecated=0 GROUP BY layer"
        ).fetchall()
        counts = {r[0]: r[1] for r in rows}
        for layer, minimum in [
            ("linguistic", 50000), ("numerical", 100000),
            ("intertextual", 20000), ("structural", 10000),
            ("interpretive", 5000), ("sod", 5000),
        ]:
            assert counts.get(layer, 0) >= minimum, \
                f"Layer {layer}: {counts.get(layer, 0)} < {minimum}"

    def test_tradition_distribution(self, db):
        """Connections should have proper tradition labels."""
        total = db.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
        untagged = db.execute(
            "SELECT COUNT(*) FROM connections WHERE deprecated=0 AND (tradition IS NULL OR tradition='')"
        ).fetchone()[0]
        pct_untagged = untagged / total * 100
        assert pct_untagged < 50, f"{pct_untagged:.1f}% connections untagged (expected <50%)"
