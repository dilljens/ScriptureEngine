"""Tests for the 5-stage consolidation pipeline (Track B).

Covers: merge-candidate detection (trigram), dry-run purity, contradiction
resolution (explicit beats algorithmic), entity merging (aliases + re-pointed
verse_entities), the forget/stale archive boundary, and idempotency
(re-running --apply reports 0 new actions).
"""
import sqlite3

import pytest

from lib.controls.consolidation import (
    consolidate,
    find_merge_candidates,
    trigram_similarity,
)


def _seed(conn):
    conn.executescript("""
        INSERT INTO works (id, title) VALUES ('ot', 'Old Testament');
        INSERT INTO books (id, work_id, title, position) VALUES ('gen', 'ot', 'Genesis', 1);
        INSERT INTO verses (id, book_id, chapter, verse, text_english)
            VALUES ('gen.1.1','gen',1,1,'text one'),
                   ('gen.12.1','gen',12,1,'text two');
        ALTER TABLE connections ADD COLUMN created_at TEXT;
        ALTER TABLE connections ADD COLUMN quality_level TEXT;
        ALTER TABLE connections ADD COLUMN deprecated INTEGER DEFAULT 0;
    """)
    conn.executemany(
        "INSERT INTO entity_links (entity_id, entity_type, english_name, aliases) VALUES (?,?,?,?)",
        [
            ("person.abraham", "person", "Abraham", "[]"),
            # Duplicate: same surface via alias → merge candidate
            ("person.abraham2", "person", "Abram", '["Abraham"]'),
            ("person.moses", "person", "Moses", "[]"),
        ],
    )
    conn.executemany(
        "INSERT INTO verse_entities (verse_id, entity_id, relationship_type, confidence) "
        "VALUES (?,?, 'mentions', ?)",
        [
            ("gen.1.1", "person.abraham", 0.9),
            ("gen.12.1", "person.abraham2", 0.9),
            ("gen.1.1", "person.moses", 0.5),
        ],
    )
    conn.executemany(
        "INSERT INTO connections (source_verse, target_verse, layer, type, discovered_by, "
        "confidence, created_at, quality_level) VALUES (?,?,?,?,?,?,?,?)",
        [
            # Contradictory pair: direct_quotation (text) vs echo (llm) → score 0.6
            ("gen.1.1", "gen.12.1", "intertextual", "direct_quotation", "text", 0.9, "2024-01-01", "verified"),
            ("gen.1.1", "gen.12.1", "intertextual", "echo", "llm", 0.9, "2024-01-01", "probable"),
            # Archive target: low confidence + old (> 180d)
            ("gen.1.1", "gen.12.1", "linguistic", "same_root", "algorithm", 0.05, "2020-01-01", "pattern"),
            # Boundary 1: low confidence but recent → NOT archived
            ("gen.12.1", "gen.1.1", "linguistic", "same_lemma", "algorithm", 0.05, "2026-08-01", "pattern"),
            # Boundary 2: high confidence but old → NOT archived
            ("gen.12.1", "gen.1.1", "symbolic", "temple_symbol", "human", 0.9, "2019-01-01", "verified"),
        ],
    )
    conn.commit()


@pytest.fixture
def con_db(tmp_path):
    db_path = tmp_path / "consolidate.db"
    from lib.db import init_db

    conn = init_db(db_path)
    _seed(conn)
    return conn


def _fresh(path):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


class TestTrigram:
    def test_similarity_basics(self):
        assert trigram_similarity("Abraham", "Abraham") == 1.0
        assert trigram_similarity("Abraham", "Abram") < 0.5
        assert trigram_similarity("", "Abraham") == 0.0

    def test_normalization(self):
        # Punctuation/case-insensitive: "Israel" ~ "Isra'el"
        assert trigram_similarity("Israel", "Isra'el") > 0.9


class TestMergeCandidates:
    def test_finds_duplicate_via_alias(self, con_db):
        cands = find_merge_candidates(con_db)
        pair = [c for c in cands if c["duplicate"] == "person.abraham2"]
        assert len(pair) == 1
        assert pair[0]["canonical"] == "person.abraham"

    def test_no_false_candidates_between_distinct_personas(self, con_db):
        # Moses vs Abraham / Abram vs Abraham must NOT merge (precision over recall)
        for c in find_merge_candidates(con_db):
            assert "moses" not in c["duplicate"] and "moses" not in c["canonical"]


class TestDryRun:
    def test_dry_run_reports_without_writing(self, con_db):
        report = consolidate(con_db, dry_run=True)
        s = report["summary"]
        assert s["merge_candidates"] == 1
        assert s["contradictions"] >= 1
        assert s["resolved"] == 1
        assert s["merged"] == 1
        assert s["archived"] == 1
        assert report["dry_run"] is True

        # Nothing written:
        assert con_db.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0] == 3
        assert con_db.execute(
            "SELECT COUNT(*) FROM entity_links WHERE entity_id='person.abraham2'"
        ).fetchone()[0] == 1
        assert con_db.execute("SELECT COUNT(*) FROM connections").fetchone()[0] == 5
        assert con_db.execute("SELECT COUNT(*) FROM archived_connections").fetchone()[0] == 0
        loser = con_db.execute(
            "SELECT metadata FROM connections WHERE type='echo'"
        ).fetchone()[0]
        assert "consolidation" not in (loser or "{}")


class TestApply:
    def test_apply_merges_resolves_archives(self, con_db):
        report = consolidate(con_db, dry_run=False)
        assert report["summary"]["merged"] == 1
        assert report["summary"]["resolved"] == 1
        assert report["summary"]["archived"] == 1

        # Merge: duplicate row gone, canonical keeps the re-pointed verse + aliases
        rows = con_db.execute(
            "SELECT entity_id FROM entity_links ORDER BY entity_id"
        ).fetchall()
        assert [r[0] for r in rows] == ["person.abraham", "person.moses"]
        abraham = con_db.execute(
            "SELECT * FROM entity_links WHERE entity_id='person.abraham'"
        ).fetchone()
        import json

        assert "Abram" in json.loads(abraham["aliases"])
        verses = con_db.execute(
            "SELECT verse_id FROM verse_entities WHERE entity_id='person.abraham' ORDER BY verse_id"
        ).fetchall()
        assert [r[0] for r in verses] == ["gen.1.1", "gen.12.1"]

        # Resolution: loser (echo) marked, winner (text) untouched
        loser = con_db.execute(
            "SELECT metadata, discovered_by FROM connections WHERE type='echo'"
        ).fetchone()
        assert json.loads(loser["metadata"])["consolidation"]["resolved"] is True
        winner = con_db.execute(
            "SELECT discovered_by FROM connections WHERE type='direct_quotation'"
        ).fetchone()
        assert winner["discovered_by"] == "text"

        # Archive: exactly the old low-confidence row moved to archived_connections
        assert con_db.execute("SELECT COUNT(*) FROM connections").fetchone()[0] == 4
        arch = con_db.execute("SELECT * FROM archived_connections").fetchall()
        assert len(arch) == 1
        assert arch[0]["type"] == "same_root"
        assert arch[0]["archive_reason"] == "stale_low_confidence"
        gone = con_db.execute(
            "SELECT COUNT(*) FROM connections WHERE type='same_root'"
        ).fetchone()[0]
        assert gone == 0

    def test_integrity_check_clean_after_apply(self, con_db):
        consolidate(con_db, dry_run=False)
        assert con_db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    def test_second_apply_is_noop(self, con_db):
        consolidate(con_db, dry_run=False)
        report2 = consolidate(con_db, dry_run=False)
        assert report2["summary"]["total_actions"] == 0
        assert report2["summary"]["merged"] == 0
        assert report2["summary"]["resolved"] == 0
        assert report2["summary"]["archived"] == 0
        # State is stable across the second run
        assert con_db.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0] == 2
        assert con_db.execute("SELECT COUNT(*) FROM connections").fetchone()[0] == 4


class TestForgetBoundary:
    def test_archive_boundary(self, con_db):
        rows = con_db.execute(
            "SELECT type, confidence, created_at FROM connections ORDER BY type"
        ).fetchall()
        by_type = {r["type"]: r for r in rows}
        from lib.controls.consolidation import _archivable

        targets = {r["type"] for r in _archivable(con_db)}
        # Only the old + low-confidence row qualifies
        assert "same_root" in targets
        assert "same_lemma" not in targets  # recent
        assert "temple_symbol" not in targets  # high confidence
        assert "echo" not in targets
        assert by_type["same_root"]["confidence"] < 0.1


class TestStaleDetection:
    def test_stale_via_needs_revalidation(self, con_db):
        from lib.controls.consolidation import find_stale_connections

        stale_ids = {s["id"] for s in find_stale_connections(con_db)}
        by_type = {
            r["type"]: r
            for r in con_db.execute(
                "SELECT id, type, discovered_by, created_at FROM connections"
            )
        }
        # same_root (algorithm, 2020) is stale; text connections never are
        assert by_type["same_root"]["id"] in stale_ids
        assert by_type["direct_quotation"]["id"] not in stale_ids
