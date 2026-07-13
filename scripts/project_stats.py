#!/usr/bin/env python3
"""
Scripture Knowledge Engine — Project Stats Verifier.

Queries the live SQLite database and prints comprehensive project statistics.
Used as the single source of truth for documentation updates.

Usage:
    python3 scripts/project_stats.py            # Query live DB
    python3 scripts/project_stats.py --json     # JSON output
    python3 scripts/project_stats.py --check    # Check if DB is available
"""

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "scripture.db"
MEMORIZE_DB_PATH = PROJECT_ROOT / "data" / "memorize.db"


def db_available():
    """Check if the scripture database is available."""
    return DEFAULT_DB_PATH.exists()


def get_conn():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(str(DEFAULT_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -8000")
    return conn


def count_tools():
    """Count registered MCP tools from lib/api/__init__.py."""
    import re
    init_path = PROJECT_ROOT / "lib" / "api" / "__init__.py"
    content = init_path.read_text()
    registers = re.findall(r'register\(', content)
    tool_names = re.findall(r'"(?:scripture|conversation)_([a-z_]+)"', content)
    return len(registers), sorted(set(tool_names))


def count_http_endpoints():
    """Count HTTP API endpoints from web/server.py and web/routes/."""
    import re
    server_path = PROJECT_ROOT / "web" / "server.py"
    content = server_path.read_text()
    # Count app-level endpoints
    app_routes = re.findall(r'@app\.(?:get|post|put|delete|patch)\(', content)

    # Count router-level endpoints
    routes_dir = PROJECT_ROOT / "web" / "routes"
    router_routes = 0
    if routes_dir.exists():
        for rf in sorted(routes_dir.glob("*.py")):
            rc = rf.read_text()
            router_routes += len(re.findall(r'@router\.(?:get|post|put|delete|patch)\(', rc))

    return len(app_routes) + router_routes, len(app_routes), router_routes


def query_db(conn):
    """Query all statistics from the live database."""
    stats = {}

    # Total connections
    row = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()
    stats["total_connections"] = row["c"]

    # Unique source verses
    row = conn.execute("SELECT COUNT(DISTINCT source_verse) as c FROM connections").fetchone()
    stats["unique_source_verses"] = row["c"]

    # Unique target verses
    row = conn.execute("SELECT COUNT(DISTINCT target_verse) as c FROM connections").fetchone()
    stats["unique_target_verses"] = row["c"]

    # Layers + counts
    layers = conn.execute(
        "SELECT layer, COUNT(*) as c FROM connections GROUP BY layer ORDER BY c DESC"
    ).fetchall()
    stats["layers"] = {r["layer"]: r["c"] for r in layers}
    stats["layer_count"] = len(layers)

    # Connection types
    types = conn.execute(
        "SELECT type, COUNT(*) as c FROM connections GROUP BY type ORDER BY c DESC"
    ).fetchall()
    stats["connection_types"] = {r["type"]: r["c"] for r in types}
    stats["type_count"] = len(types)

    # Subtypes
    subtypes = conn.execute(
        "SELECT subtype, COUNT(*) as c FROM connections WHERE subtype IS NOT NULL AND subtype != '' GROUP BY subtype ORDER BY c DESC"
    ).fetchall()
    stats["subtype_count"] = len(subtypes)
    stats["subtypes"] = {r["subtype"]: r["c"] for r in subtypes[:20]}  # top 20

    # Quality distribution
    quality = conn.execute(
        "SELECT quality_level, COUNT(*) as c FROM connections GROUP BY quality_level ORDER BY quality_level"
    ).fetchall()
    stats["quality_distribution"] = {str(r["quality_level"]): r["c"] for r in quality}

    # Total verses
    row = conn.execute("SELECT COUNT(*) as c FROM verses").fetchone()
    stats["total_verses"] = row["c"]

    # Verses by work
    works = conn.execute("""
        SELECT w.id, w.title, COUNT(*) as c
        FROM verses v
        JOIN books b ON b.id = v.book_id
        JOIN works w ON w.id = b.work_id
        GROUP BY w.id
        ORDER BY w.id
    """).fetchall()
    stats["verses_by_work"] = {r["title"]: r["c"] for r in works}
    stats["work_count"] = len(works)

    # Books
    row = conn.execute("SELECT COUNT(*) as c FROM books").fetchone()
    stats["total_books"] = row["c"]

    # Entities
    row = conn.execute("SELECT COUNT(*) as c FROM entity_links").fetchone()
    stats["total_entities"] = row["c"]

    # Verse-entity links
    try:
        row = conn.execute("SELECT COUNT(*) as c FROM verse_entities").fetchone()
        stats["verse_entity_links"] = row["c"]
    except sqlite3.OperationalError:
        stats["verse_entity_links"] = 0

    # Gematria
    row = conn.execute("SELECT COUNT(*) as c FROM gematria").fetchone()
    stats["hebrew_gematria_entries"] = row["c"]

    row = conn.execute("SELECT COUNT(*) as c FROM gematria_greek").fetchone()
    stats["greek_isopsephy_entries"] = row["c"]

    # Passage guides
    row = conn.execute("SELECT COUNT(*) as c FROM passage_guides").fetchone()
    stats["passage_guides"] = row["c"]

    # Study guides
    row = conn.execute("SELECT COUNT(*) as c FROM study_guides").fetchone()
    stats["study_guides"] = row["c"]

    # Published studies
    row = conn.execute("SELECT COUNT(*) as c FROM published_studies").fetchone()
    stats["published_studies"] = row["c"]

    return stats


def print_report(stats):
    """Print a human-readable report."""
    print("=" * 60)
    print("  SCRIPTURE KNOWLEDGE ENGINE — Project Statistics")
    print("=" * 60)
    print()

    # Connection graph
    print("── Connection Graph ──")
    print(f"  Total connections:    {stats['total_connections']:,}")
    print(f"  Unique source verses: {stats['unique_source_verses']:,}")
    print(f"  Unique target verses: {stats['unique_target_verses']:,}")
    print(f"  Layers:               {stats['layer_count']}")
    print(f"  Connection types:     {stats['type_count']}")
    print(f"  Subtypes:             {stats['subtype_count']}")
    print()

    print("  Connections by layer:")
    for layer, count in sorted(stats['layers'].items(), key=lambda x: -x[1]):
        print(f"    {layer:20s}  {count:>10,}")
    print()

    print("  Quality distribution:")
    for level, count in stats['quality_distribution'].items():
        print(f"    Level {level:12s}  {count:>10,}")
    print()

    # Verses
    print("── Verses ──")
    print(f"  Total verses: {stats['total_verses']:,}")
    print(f"  Total books:  {stats['total_books']}")
    print(f"  Works:        {stats['work_count']}")
    print()
    for work, count in stats['verses_by_work'].items():
        print(f"    {work:30s}  {count:>6,}")
    print()

    # Entities
    print("── Entities ──")
    print(f"  Entity definitions: {stats['total_entities']}")
    print(f"  Verse-entity links: {stats['verse_entity_links']:,}")
    print()

    # Gematria
    print("── Gematria ──")
    print(f"  Hebrew gematria entries:   {stats['hebrew_gematria_entries']:,}")
    print(f"  Greek isopsephy entries:   {stats['greek_isopsephy_entries']:,}")
    print()

    # Guides
    print("── Study Guides ──")
    print(f"  Passage guides:  {stats['passage_guides']:,}")
    print(f"  Study guides:    {stats['study_guides']:,}")
    print(f"  Published:       {stats['published_studies']:,}")
    print()

    # Tools
    print("── MCP / HTTP Tools ──")
    print(f"  Registered MCP tools:     {stats['tool_count']}")
    print(f"  HTTP API endpoints:       {stats['http_endpoints']} ({stats['http_app']} app + {stats['http_routes']} routes)")
    print()


def get_fallback_stats():
    """Return stats from the project AGENTS.md when DB is unavailable."""
    return {
        "total_connections": 1028083,
        "unique_source_verses": "~42K",
        "unique_target_verses": "~42K",
        "layers": {
            "linguistic": "~200K",
            "numerical": "~300K",
            "structural": "~100K",
            "intertextual": "~150K",
            "textual": "~50K",
            "geographic": "~30K",
            "chronological": "~30K",
            "interpretive": "~50K",
            "frequency": "~30K",
            "symbolic": "~40K",
            "sod": "~50K",
        },
        "layer_count": 11,
        "type_count": 131,
        "subtype_count": "varies",
        "quality_distribution": {"N/A": 0},
        "total_verses": 42054,
        "total_books": 224,
        "work_count": 8,
        "verses_by_work": {
            "Old Testament": "~23K",
            "New Testament": "~8K",
            "Book of Mormon": "~6.6K",
            "Doctrine & Covenants": "~3.6K",
            "Pearl of Great Price": "~500",
            "Dead Sea Scrolls": "~8K",
            "Apocrypha": "~5.5K",
            "Pseudepigrapha": "~15K",
        },
        "total_entities": "~87",
        "verse_entity_links": "varies",
        "hebrew_gematria_entries": "~305K",
        "greek_isopsephy_entries": "~137K",
        "passage_guides": "~41K",
        "study_guides": "varies",
        "published_studies": "varies",
    }


if __name__ == "__main__":
    # Always count tools and endpoints (no DB needed)
    tool_count, tool_names = count_tools()
    http_total, http_app, http_routes = count_http_endpoints()

    if "--check" in sys.argv:
        print(json.dumps({"available": db_available(), "db_path": str(DEFAULT_DB_PATH)}))
        sys.exit(0)

    if db_available():
        conn = get_conn()
        stats = query_db(conn)
        conn.close()
        stats["source"] = "live_db"
    else:
        print(f"NOTE: Database not found at {DEFAULT_DB_PATH}", file=sys.stderr)
        print("Using fallback stats from AGENTS.md (approximate)\n", file=sys.stderr)
        stats = get_fallback_stats()
        stats["source"] = "fallback_agents_md"

    stats["tool_count"] = tool_count
    stats["tool_names"] = tool_names
    stats["http_endpoints"] = http_total
    stats["http_app"] = http_app
    stats["http_routes"] = http_routes
    stats["generator_count"] = len(list(PROJECT_ROOT.glob("generators/*.py"))) - 1  # exclude __init__
    stats["cli_tool_count"] = len(list(PROJECT_ROOT.glob("tools/*.py"))) - 1
    stats["script_count"] = len(list(PROJECT_ROOT.glob("scripts/*.py")))

    if "--json" in sys.argv:
        print(json.dumps(stats, indent=2, default=str))
    else:
        print_report(stats)

    # Summary line for easy parsing
    print(f"SUMMARY: {stats['total_connections']:,} connections · {stats['layer_count']} layers · {stats['type_count']} types · "
          f"{stats['total_verses']:,} verses · {stats['work_count']} works · "
          f"{stats['tool_count']} tools · {stats['http_endpoints']} endpoints")
