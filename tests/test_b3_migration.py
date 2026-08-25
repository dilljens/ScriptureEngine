"""Track B3: retired-numerical archive migration is idempotent and reversible.

Runs the real apply/restore functions against a throwaway database with the
production schema, so no live data is touched.
"""

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.controls.calibration import RETIRED_NUMERICAL_TYPES  # noqa: E402
from scripts.archive_retired_numerical import (  # noqa: E402
    ARCHIVE_REASON,
    apply_archive,
    count_pending,
    restore,
)

CONNECTIONS_DDL = """
CREATE TABLE connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL,
    target_verse TEXT NOT NULL,
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}',
    hermeneutic TEXT DEFAULT NULL,
    UNIQUE(source_verse, target_verse, layer, type, subtype)
);
CREATE TABLE archived_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL,
    target_verse TEXT NOT NULL,
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}',
    archived_at TEXT DEFAULT (datetime('now')),
    archive_reason TEXT DEFAULT 'stale_low_confidence'
);
"""


def _temp_db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "t.db"))
    conn.row_factory = sqlite3.Row
    conn.executescript(CONNECTIONS_DDL)
    return conn


def _insert(conn, i, ctype, hermeneutic=None):
    conn.execute(
        "INSERT INTO connections (source_verse, target_verse, layer, type, "
        "subtype, strength, confidence, discovered_by, metadata, hermeneutic) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (f"gen.{i}.1", f"exo.{i}.1", "numerical", ctype, "", 0.4, 0.4,
         "algorithm", "{}", hermeneutic),
    )


def _counts(conn, table):
    rows = conn.execute(f"SELECT type, COUNT(*) FROM {table} GROUP BY type").fetchall()
    return {r[0]: r[1] for r in rows}


def test_archive_round_trip_is_idempotent_and_reversible(tmp_path):
    conn = _temp_db(tmp_path)
    retired = sorted(RETIRED_NUMERICAL_TYPES)[:2]
    for i, t in enumerate(retired):
        _insert(conn, i, t, hermeneutic="note-" + t if i == 0 else None)
    _insert(conn, 90, "same_gematria_standard")  # retained — must survive

    before = _counts(conn, "connections")
    assert sum(before[t] for t in retired) == 2

    # Apply: retired rows leave `connections`, land in archive with reason.
    assert count_pending(conn) == 2
    apply_archive(conn)
    after = _counts(conn, "connections")
    assert all(t not in after for t in retired)
    assert after.get("same_gematria_standard") == 1
    archived = conn.execute(
        "SELECT COUNT(*) FROM archived_connections WHERE archive_reason = ?",
        (ARCHIVE_REASON,),
    ).fetchone()[0]
    assert archived == 2

    # Idempotent: second apply is a no-op.
    assert count_pending(conn) == 0
    apply_archive(conn)
    assert conn.execute(
        "SELECT COUNT(*) FROM archived_connections WHERE archive_reason = ?",
        (ARCHIVE_REASON,),
    ).fetchone()[0] == 2

    # Hermeneutic survived via metadata fold-in.
    meta = conn.execute(
        "SELECT metadata FROM archived_connections WHERE type = ?",
        (retired[0],),
    ).fetchone()[0]
    assert "note-" + retired[0] in meta

    # Restore: rows come back intact; archive bucket empties.
    restore(conn)
    restored = _counts(conn, "connections")
    for t in retired:
        assert restored[t] == before[t]
    herm = conn.execute(
        "SELECT hermeneutic FROM connections WHERE type = ?", (retired[0],)
    ).fetchone()[0]
    assert herm == "note-" + retired[0]
    assert conn.execute(
        "SELECT COUNT(*) FROM archived_connections WHERE archive_reason = ?",
        (ARCHIVE_REASON,),
    ).fetchone()[0] == 0
