"""Cross-granularity connection tests (verse↔chapter, chapter↔chapter,
chunk↔chapter, chapter↔book): passage type registration, granularity
derivation, the '--' embedded-range data fix, and passage edges in graph
traversal (reachable + path bridging).

Run: pytest tests/passage_granularity_test.py -q
"""
import sqlite3
from pathlib import Path

import pytest

from lib.api import graph as graph_api
from lib.api.passage import (
    derive_granularity,
    get_passage_connections,
    split_embedded_range,
)
from lib.connections.types import ALL_TYPES

PROD_DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"


@pytest.fixture(scope="module")
def prod_conn():
    """Read-only connection to the real scripture DB (passage_connections live
    there; the test DB has none)."""
    if not PROD_DB_PATH.exists():
        pytest.skip(f"production DB not present: {PROD_DB_PATH}")
    conn = sqlite3.connect(f"file:{PROD_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ── Unit: granularity derivation ──

def test_derive_granularity():
    assert derive_granularity("gen.1.1", "gen.1.1") == "verse"
    assert derive_granularity("gen.1.1", "gen.1.10") == "chunk"
    assert derive_granularity("gen.1.1", "gen.1.31") == "chapter"
    assert derive_granularity("gen.1.1", "gen.2.31") == "chapter"
    assert derive_granularity("gen.1.1", "exo.1.1") == "book"
    assert derive_granularity("gen", "exo") == "book"  # bare book refs


def test_split_embedded_range_fixes_chiastic_bug():
    """chiastic_promoter wrote ranges into one field: '1adae.21.5--1adae.21.9'."""
    start, end = split_embedded_range("1adae.21.5--1adae.21.9", None)
    assert start == "1adae.21.5"
    assert end == "1adae.21.9"
    # No-op on normal refs
    start, end = split_embedded_range("gen.1.1", "gen.1.31")
    assert (start, end) == ("gen.1.1", "gen.1.31")


def test_passage_types_registered_in_layers():
    """The passage-level types must appear in the type registry so validation
    and tool listing treat them as first-class."""
    registered = {t for _, t in ALL_TYPES}
    for t in ("pericope_parallel", "book_thematic", "macro_chiastic",
              "narrative_parallel", "interpretation_chain", "translation_divergence"):
        assert t in registered, f"passage type {t} not registered"


# ── Integration (live/prod DB) ──

def test_passage_connections_carry_granularity(prod_conn):
    rows = get_passage_connections(prod_conn, "gen.1.1", "gen.1.31")
    assert rows, "expected passage connections for Genesis 1"
    assert all("granularity" in r for r in rows)
    assert any(r["granularity"] in ("chapter", "chunk", "book") for r in rows)


def test_passage_neighbors_indexed_lookup(prod_conn):
    passages, by_book = graph_api._load_passages(prod_conn)
    assert len(passages) > 1000, "passage table should be populated"
    edges = graph_api._passage_neighbors(passages, by_book, "gen.1.1")
    assert edges, "gen.1.1 should sit inside passage ranges"
    for e in edges:
        assert e["passage"] is True
        assert e["granularity"] in ("verse", "chunk", "chapter", "book")
        assert e["to"], "far-side anchor missing"


def test_graph_reachable_includes_passage_edges(prod_conn):
    r = graph_api.graph_reachable(prod_conn, "isa.6.1", max_depth=2, limit=100)
    flat = [e for d in r["by_depth"].values() for e in d]
    passage_edges = [e for e in flat if e.get("passage")]
    assert passage_edges, "reachable should surface chapter/chunk/book edges"
    assert any(e["granularity"] == "chapter" for e in passage_edges)


def test_passage_bridged_path_quick_and_correct(prod_conn):
    """isa.6.1 → amos.9.15 has no verse-level path; the passage bridge finds a
    mixed chapter/book path fast."""
    import time
    t0 = time.monotonic()
    path = graph_api._passage_bridged_path(prod_conn, "isa.6.1", "amos.9.15", 3)
    elapsed = time.monotonic() - t0
    assert elapsed < 5.0, f"bridge too slow: {elapsed:.1f}s"
    assert path, "expected a passage-bridged path"
    assert path[0]["passage"] and path[-1]["passage"]
    assert path[0]["from"] == "isa.6.1"
    assert path[-1]["to"] == "amos.9.15"
    # No self-loop segments
    for seg in path:
        assert seg["from"] != seg["to"], f"self-loop segment: {seg}"
