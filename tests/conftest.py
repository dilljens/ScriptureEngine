"""Test configuration and shared fixtures for Scripture Engine API tests.

Uses a minimal test database when available, falls back to production DB.
Set SCRIPTURE_DB_PATH env var to override, or create data/test/test.db.
"""
import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is in path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Determine database path
TEST_DB = ROOT / "data" / "test" / "test.db"
PROD_DB = ROOT / "data" / "processed" / "scripture.db"

if "SCRIPTURE_DB_PATH" in os.environ:
    DB_PATH = Path(os.environ["SCRIPTURE_DB_PATH"])
elif TEST_DB.exists():
    DB_PATH = TEST_DB
else:
    DB_PATH = PROD_DB

# Override the default DB path BEFORE server imports
import lib.db
lib.db.DEFAULT_DB_PATH = DB_PATH

from web.server import app


@pytest.fixture(scope="session")
def memorize_db_template(tmp_path_factory):
    """Stable SQLite snapshot used as the source for isolated Hebrew tests."""
    source = ROOT / "data" / "memorize.db"
    if not source.exists():
        pytest.skip(f"Hebrew database not found: {source}")
    template = tmp_path_factory.mktemp("hebrew-template") / "memorize.db"
    source_conn = sqlite3.connect(source)
    template_conn = sqlite3.connect(template)
    source_conn.backup(template_conn)
    template_conn.close()
    source_conn.close()
    return template


@pytest.fixture(scope="session")
def prod_db():
    """Read-only connection to test/production database."""
    if not DB_PATH.exists():
        pytest.skip(f"Test database not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def client(request, monkeypatch, tmp_path, memorize_db_template):
    """FastAPI TestClient for in-process endpoint testing."""
    touches_hebrew = (
        "hebrew" in request.node.nodeid.casefold()
        or (request.cls and "hebrew" in request.cls.__name__.casefold())
    )
    if touches_hebrew:
        isolated = tmp_path / "memorize.db"
        shutil.copy2(memorize_db_template, isolated)
        import web.routes.hebrew as hebrew_routes
        monkeypatch.setattr(hebrew_routes, "MEM_DB", isolated)
        monkeypatch.setattr(hebrew_routes, "_HEBREW_GRAPH_CACHE", None)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def verse_refs():
    """Well-known verse references used across tests."""
    return {
        "gen1_1": "gen.1.1",
        "john1_1": "john.1.1",
        "isa6_1": "isa.6.1",
        "psa23_1": "psa.23.1",
        "matt5_3": "matt.5.3",
    }
