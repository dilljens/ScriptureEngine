#!/usr/bin/env python3
"""Database migration system for Scripture Engine.

Uses SQLite's PRAGMA user_version to track schema version.
Migrations are additive only — they add tables/columns/indexes.

Usage:
    python3 scripts/migrate.py                  # Apply all pending migrations
    python3 scripts/migrate.py --status          # Show current version
    python3 scripts/migrate.py --version N       # Migrate to specific version
    python3 scripts/migrate.py --dry-run         # Preview without applying
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def get_version(conn):
    """Get current schema version."""
    return conn.execute("PRAGMA user_version").fetchone()[0]


def set_version(conn, version):
    """Set schema version."""
    conn.execute(f"PRAGMA user_version = {version}")
    conn.commit()


MIGRATIONS = [
    # Version 1: Initial auth + generator_meta tables
    {
        "version": 1,
        "description": "Add auth, session, recovery_key, user_preferences, generator_meta tables",
        "sql": """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                google_id TEXT UNIQUE,
                email TEXT UNIQUE,
                name TEXT DEFAULT '',
                avatar_url TEXT DEFAULT '',
                anon_id TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                last_login TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                last_seen TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS recovery_keys (
                key_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_data TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                claimed_at TEXT,
                claimed_by TEXT
            );
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT NOT NULL,
                pref_key TEXT NOT NULL,
                pref_value TEXT NOT NULL DEFAULT '',
                updated_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, pref_key)
            );
            CREATE TABLE IF NOT EXISTS generator_meta (
                generator_name TEXT PRIMARY KEY,
                last_run_at TEXT NOT NULL,
                source_hash TEXT,
                connection_count INTEGER,
                duration_ms INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_users_anon ON users(anon_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_recovery_user ON recovery_keys(user_id);
        """,
    },
    # Version 2: Performance indexes for review queries and filtering
    {
        "version": 2,
        "description": "Add performance indexes for FSRS review, quality filtering",
        "sql": """
            CREATE INDEX IF NOT EXISTS idx_connections_quality ON connections(quality_level);
            CREATE INDEX IF NOT EXISTS idx_connections_deprecated ON connections(deprecated);
            CREATE INDEX IF NOT EXISTS idx_mp_user_review ON memorize_progress(user_id, next_review);
            CREATE INDEX IF NOT EXISTS idx_fire_credits_user ON fi_re_credits(user_id, item_type, item_id);
        """,
    },
]


def apply_migration(conn, migration, dry_run=False):
    """Apply a single migration."""
    print(f"  v{migration['version']}: {migration['description']}...", end=" ")
    if dry_run:
        print("(dry run — skipped)")
        return True
    try:
        conn.executescript(migration["sql"])
        set_version(conn, migration["version"])
        print("OK")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Schema migration tool")
    parser.add_argument("--status", action="store_true", help="Show current version")
    parser.add_argument("--version", type=int, default=0, help="Target version (default: latest)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    from lib.db import get_db
    conn = get_db()

    current = get_version(conn)
    target = args.version if args.version > 0 else MIGRATIONS[-1]["version"]

    print(f"Schema version: {current} → target: {target}")
    print()

    if args.status:
        print(f"Current version: {current}")
        print(f"Available migrations: {len(MIGRATIONS)}")
        for m in MIGRATIONS:
            status = "✅" if m["version"] <= current else "⬜"
            print(f"  {status} v{m['version']}: {m['description']}")
        conn.close()
        return

    if current >= target:
        print("Already at target version. Nothing to do.")
        conn.close()
        return

    pending = [m for m in MIGRATIONS if m["version"] > current and m["version"] <= target]

    if not pending:
        print("No pending migrations.")
        conn.close()
        return

    print(f"Running {len(pending)} migration(s):")
    t0 = time.time()
    success = 0
    for migration in pending:
        if apply_migration(conn, migration, dry_run=args.dry_run):
            success += 1
        else:
            print("  Stopping due to error.")
            break

    elapsed = time.time() - t0
    print(f"\n{success}/{len(pending)} migrations applied in {elapsed:.1f}s")
    conn.close()


if __name__ == "__main__":
    main()
