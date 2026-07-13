"""Test configuration and shared fixtures for Scripture Engine API tests.

Uses FastAPI TestClient for in-process testing (no real server).
Default DB connection is read-only to the production database.
"""
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure project root is in path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from web.server import app

PROD_DB = ROOT / "data" / "processed" / "scripture.db"


@pytest.fixture(scope="session")
def prod_db():
    """Read-only connection to production database for integration tests."""
    if not PROD_DB.exists():
        pytest.skip(f"Production DB not found: {PROD_DB}")
    conn = sqlite3.connect(f"file:{PROD_DB}?mode=ro", uri=True)
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
