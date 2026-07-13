"""Migration: add truth alignment v2 schema changes.

Adds:
1. disagreements table (contradiction tracking)
2. last_validated + revalidation_due columns to connections
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    
    changes = []
    
    # 1. Create disagreements table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS disagreements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_a_id INTEGER NOT NULL REFERENCES connections(id),
            connection_b_id INTEGER NOT NULL REFERENCES connections(id),
            verse_pair TEXT NOT NULL,
            conflict_score REAL DEFAULT 0.5,
            conflict_type TEXT DEFAULT 'contradictory',
            resolution TEXT DEFAULT 'unresolved',
            resolved_by TEXT DEFAULT '',
            resolved_at TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    changes.append("Created disagreements table")
    
    # 2. Add revalidation columns to connections
    existing = [r[1] for r in conn.execute("PRAGMA table_info(connections)").fetchall()]
    if "last_validated" not in existing:
        conn.execute("ALTER TABLE connections ADD COLUMN last_validated TEXT DEFAULT NULL")
        changes.append("Added connections.last_validated")
    if "revalidation_due" not in existing:
        conn.execute("ALTER TABLE connections ADD COLUMN revalidation_due INTEGER DEFAULT 0")
        changes.append("Added connections.revalidation_due")
    
    # 3. Add dispute status column (for disputed quality level)
    if "dispute_status" not in existing:
        conn.execute("ALTER TABLE connections ADD COLUMN dispute_status TEXT DEFAULT ''")
        conn.execute("ALTER TABLE connections ADD COLUMN disputed_by TEXT DEFAULT ''")
        changes.append("Added connections.dispute_status")
    
    conn.commit()
    conn.close()
    
    for c in changes:
        print(f"  ✓ {c}")
    print(f"\nMigration complete — {len(changes)} changes applied.")


if __name__ == "__main__":
    migrate()
