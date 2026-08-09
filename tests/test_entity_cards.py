"""Tests for materialized entity cards (Track A).

Covers: builder (scripts/build_materialized_views.py), the reader tool
(lib/api/materialized.entity_card), TOOL_REGISTRY wiring, and the
GET /api/v1/entities/{entity_id} HTTP endpoint.
"""
import importlib.util
import sqlite3
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


def _load_builder():
    path = ROOT / "scripts" / "build_materialized_views.py"
    spec = importlib.util.spec_from_file_location("build_materialized_views", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILDER = _load_builder()


def _seed(conn):
    conn.executescript("""
        INSERT INTO works (id, title) VALUES ('ot', 'Old Testament');
        INSERT INTO books (id, work_id, title, position) VALUES ('gen', 'ot', 'Genesis', 1);
        INSERT INTO verses (id, book_id, chapter, verse, text_english)
            VALUES ('gen.1.1', 'gen', 1, 1, 'In the beginning God created the heaven and the earth.');
        INSERT INTO verses (id, book_id, chapter, verse, text_english)
            VALUES ('gen.12.1', 'gen', 12, 1, 'Now the LORD had said unto Abram, Get thee out of thy country.');
        INSERT INTO verses (id, book_id, chapter, verse, text_english)
            VALUES ('gen.22.1', 'gen', 22, 1, 'And it came to pass after these things, that God did tempt Abraham.');
    """)
    conn.executemany(
        "INSERT INTO entity_links (entity_id, entity_type, english_name, hebrew_name, greek_name, notes) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("person.abraham", "person", "Abraham", "", "", ""),
            ("person.messiah", "person", "Messiah", "\u05de\u05e9\u05d9\u05d7", "", ""),
            ("place.israel", "place", "Israel", "", "", ""),
            ("place.canaan", "place", "Canaan", "", "", ""),
            ("concept.covenant", "concept", "Covenant", "", "", ""),
            ("concept.promise", "concept", "Promise", "", "", ""),
        ],
    )
    conn.executemany(
        "INSERT INTO verse_entities (verse_id, entity_id, relationship_type, confidence) "
        "VALUES (?, ?, 'mentions', ?)",
        [
            ("gen.12.1", "person.abraham", 0.9),
            ("gen.22.1", "person.abraham", 0.9),
            ("gen.12.1", "place.israel", 0.6),
            ("gen.1.1", "place.israel", 0.6),
            ("gen.1.1", "concept.covenant", 0.6),
            ("gen.12.1", "person.messiah", 0.5),
            # Co-occurs with Abraham in 2+ verses → appears in the card's
            # co_occurring_entities (builder requires frequency >= 2)
            ("gen.12.1", "place.canaan", 0.6),
            ("gen.22.1", "place.canaan", 0.6),
            ("gen.12.1", "concept.promise", 0.6),
            ("gen.22.1", "concept.promise", 0.6),
        ],
    )
    conn.execute(
        "INSERT INTO connections (source_verse, target_verse, layer, type, subtype, strength, confidence, discovered_by) "
        "VALUES ('gen.12.1', 'gen.22.1', 'intertextual', 'parallel', '', 0.7, 0.8, 'human')"
    )
    conn.execute(
        "INSERT INTO gematria (verse_id, word_index, word_hebrew, word_english, value_standard, value_ordinal, value_reduced) "
        "VALUES ('gen.12.1', 0, '\u05de\u05e9\u05d9\u05d7', 'Messiah', 358, 49, 13)"
    )
    conn.commit()


@pytest.fixture
def cards_db(tmp_path):
    """Temp DB with schema + seeded data + materialized views built."""
    db_path = tmp_path / "cards.db"
    from lib.db import init_db

    conn = init_db(db_path)
    _seed(conn)
    BUILDER.build_entity_cooccurrence(conn)
    BUILDER.build_entity_cards(conn)
    conn.close()
    return db_path


def _db(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


class TestEntityCardReader:
    def test_card_exists_for_known_entity(self, cards_db, monkeypatch):
        import lib.db
        import lib.api.materialized as mat

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        card = mat.entity_card(entity="person.abraham")
        assert "error" not in card
        assert card["entity"]["id"] == "person.abraham"
        assert card["entity"]["english_name"] == "Abraham"
        assert card["total_verses"] == 2
        assert card["entity_connections"]["total"] == 1
        assert card["entity_connections"]["connections"][0]["source_verse"] == "gen.12.1"
        assert card["co_occurring_entities"]["total"] == 2

    def test_card_includes_gematria_for_hebrew_surface(self, cards_db, monkeypatch):
        import lib.db
        import lib.api.materialized as mat

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        card = mat.entity_card(entity="person.messiah")
        assert "error" not in card
        assert card["gematria"]["word"] == "\u05de\u05e9\u05d9\u05d7"
        assert any(v["standard"] == 358 for v in card["gematria"]["values"])

    def test_card_unknown_entity_returns_error(self, cards_db, monkeypatch):
        import lib.db
        import lib.api.materialized as mat

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        res = mat.entity_card(entity="person.zzznope")
        assert "error" in res

    def test_card_missing_view_graceful_error(self, cards_db, monkeypatch):
        import lib.db
        import lib.api.materialized as mat

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        conn = _db(cards_db)
        conn.execute("DROP TABLE entity_cards")
        conn.commit()
        conn.close()
        res = mat.entity_card(entity="person.abraham")
        assert "error" in res
        assert "build_materialized_views" in res["error"]

    def test_card_built_at_stamped(self, cards_db, monkeypatch):
        import lib.db
        import lib.api.materialized as mat

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        card = mat.entity_card(entity="person.abraham")
        assert card.get("built_at")


class TestEntityCardTool:
    def test_tool_registered(self):
        from lib.api import TOOL_REGISTRY

        assert "scripture_entity_card" in TOOL_REGISTRY
        fn, schema, desc = TOOL_REGISTRY["scripture_entity_card"]
        assert "entity" in schema.get("properties", {})
        assert schema.get("properties", {}).get("entity", {}).get("type") == "string"

    def test_tool_call(self, cards_db, monkeypatch):
        import lib.db
        from lib.api import call_tool

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        conn = _db(cards_db)
        try:
            res = call_tool("scripture_entity_card", conn, entity="person.abraham")
        finally:
            conn.close()
        assert "error" not in res
        assert res["entity"]["id"] == "person.abraham"


class TestEntityCardEndpoint:
    def test_endpoint_returns_card(self, client, cards_db, monkeypatch):
        import lib.db

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        resp = client.get("/api/v1/entities/person.abraham")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["entity"]["id"] == "person.abraham"
        assert data["total_verses"] == 2

    def test_endpoint_404_for_unknown(self, client, cards_db, monkeypatch):
        import lib.db

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        resp = client.get("/api/v1/entities/person.zzznope")
        assert resp.status_code == 404

    def test_endpoint_ok_wrapped(self, client, cards_db, monkeypatch):
        import lib.db

        monkeypatch.setattr(lib.db, "DEFAULT_DB_PATH", cards_db)
        body = client.get("/api/v1/entities/person.abraham").json()
        assert body["ok"] is True
