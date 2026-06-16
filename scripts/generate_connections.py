#!/usr/bin/env python3
"""Run all connection generators to populate the connection layers.

Usage:
  python3 scripts/generate_connections.py              # Run all automatic generators
  python3 scripts/generate_connections.py --all         # Run all (including manual)
  python3 scripts/generate_connections.py --list        # List available generators
  python3 scripts/generate_connections.py --name "Linguistic"  # Run specific generator
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db
from lib.connections.types import LAYERS


def print_header(text):
    print()
    print("=" * 60)
    print(f"  {text}")
    print("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run connection generators")
    parser.add_argument("--all", action="store_true", help="Run all generators including non-automatic")
    parser.add_argument("--list", action="store_true", help="List available generators")
    parser.add_argument("--name", type=str, help="Run a specific generator by name")
    parser.add_argument("--books", type=str, help="Comma-separated list of book IDs to process")
    args = parser.parse_args()

    conn = get_db()

    if args.list:
        from generators import list_generators
        gens = list_generators()
        print_header("Available Generators")
        for gen in gens:
            status = "✅ loaded" if gen["loaded"] else "❌ failed"
            auto = "🤖 auto" if gen["automatic"] else "👤 needs AI"
            print(f"  {gen['name']}")
            print(f"    Layers: {', '.join(gen['layers'])}  [{auto}] [{status}]")
            print(f"    {gen['description']}")
            print()
        conn.close()
        return

    book_ids = args.books.split(",") if args.books else None

    if args.name:
        # Run specific generator
        from generators import run_generator
        print_header(f"Running: {args.name}")
        t0 = time.time()
        result = run_generator(conn, args.name, book_ids)
        elapsed = time.time() - t0
        if "error" in result:
            print(f"  ❌ {result['error']}")
        else:
            print(f"  ✅ {result['connections']} connections in {elapsed:.1f}s")
    else:
        # Run all automatic generators
        from generators import run_all

        print_header("Before")
        _print_layer_stats(conn)

        print_header("Running All Automatic Generators")
        t0 = time.time()
        results = run_all(conn, book_ids, automatic_only=not args.all)
        elapsed = time.time() - t0

        print()
        total = 0
        for r in results:
            if r["status"] == "ok":
                print(f"  ✅ {r['generator']}: {r['connections']} connections")
                total += r["connections"]
            elif r["status"] == "error":
                print(f"  ❌ {r['generator']}: {r['error'][:100]}")
            else:
                print(f"  ⏭️  {r['generator']}: {r.get('error', 'skipped')}")

        print_header("After")
        _print_layer_stats(conn)
        print(f"\n  Total: {total} connections created in {elapsed:.1f}s")

    conn.close()


def _print_layer_stats(conn):
    """Print connection count per layer."""
    layers = conn.execute("""
        SELECT layer, COUNT(*) as c FROM connections GROUP BY layer ORDER BY layer
    """).fetchall()

    all_layers = list(LAYERS.keys())
    layer_counts = {r["layer"]: r["c"] for r in layers}

    for layer in all_layers:
        count = layer_counts.get(layer, 0)
        status = "✅" if count > 0 else "⬜"
        info = LAYERS[layer]
        print(f"  {status} {layer:15s} {count:>8,}  ({info['name']})")

    total = sum(layer_counts.values())
    print(f"  {'':15s} {'──'}> {'─'*6}  ")
    print(f"  {'TOTAL':15s} {total:>8,}")


if __name__ == "__main__":
    main()
