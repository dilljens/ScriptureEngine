#!/usr/bin/env python3
"""Seed the symbolic layer — populate symbol reference table and generate connections."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.symbols.reference import seed_symbol_tables
from lib.symbols.apocalyptic import generate_apocalyptic_connections
from lib.symbols.shared_symbols import generate_shared_symbol_connections
from lib.symbols.typology import generate_typology_connections


def main():
    print("=" * 60)
    print("Symbolic Layer — Seed & Generate")
    print("=" * 60)

    conn = get_db()

    # Ensure new tables exist
    for table in ["symbols", "symbol_occurrences", "typology"]:
        conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
    print("\n✅ Tables exist")

    # Step 1: Seed reference data
    print("\n--- Step 1: Seed Reference Data ---")
    result = seed_symbol_tables(conn)
    print(f"  Symbols: {result['symbols']} added")
    print(f"  Occurrences: {result['occurrences']} added")
    print(f"  Typology pairs: {result['typology']} added")

    # Step 2: Generate apocalyptic connections
    print("\n--- Step 2: Apocalyptic Vocabulary (Dan/Ezek/Isa/Rev) ---")
    apoc_count = generate_apocalyptic_connections(conn)
    print(f"  {apoc_count} apocalyptic connections generated")

    # Step 3: Generate shared symbol connections
    print("\n--- Step 3: Shared Symbols ---")
    shared_count = generate_shared_symbol_connections(conn)
    print(f"  {shared_count} shared symbol connections generated")

    # Step 4: Generate typology connections
    print("\n--- Step 4: Typology ---")
    typo_count = generate_typology_connections(conn)
    print(f"  {typo_count} typology connections generated")

    # Summary
    print("\n" + "=" * 60)
    sym_count = conn.execute("SELECT COUNT(*) as c FROM symbols").fetchone()["c"]
    occ_count = conn.execute("SELECT COUNT(*) as c FROM symbol_occurrences").fetchone()["c"]
    typ_count = conn.execute("SELECT COUNT(*) as c FROM typology").fetchone()["c"]
    conn_count = conn.execute("""
        SELECT COUNT(*) as c FROM connections WHERE layer = 'symbolic'
    """).fetchone()["c"]
    total_conn = conn.execute("SELECT COUNT(*) as c FROM connections").fetchone()["c"]

    print(f"Symbols defined:        {sym_count}")
    print(f"Symbol occurrences:      {occ_count}")
    print(f"Typology pairs:          {typ_count}")
    print(f"Symbolic connections:    {conn_count}")
    print(f"Total connections (all): {total_conn}")
    print(f"Populated layers:       ", end="")
    layers = conn.execute("SELECT DISTINCT layer FROM connections").fetchall()
    print(", ".join(sorted(r["layer"] for r in layers)))
    print("=" * 60)

    conn.close()


if __name__ == "__main__":
    main()
