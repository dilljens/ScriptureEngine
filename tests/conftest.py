"""Test configuration and shared fixtures for Scripture Engine API tests.

Uses a minimal test database when available, falls back to production DB.
Set SCRIPTURE_DB_PATH env var to override, or create data/test/test.db.
"""
import os
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
def prod_db():
    """Read-only connection to test/production database."""
    if not DB_PATH.exists():
        pytest.skip(f"Test database not found: {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def client():
    """FastAPI TestClient for in-process endpoint testing."""
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
