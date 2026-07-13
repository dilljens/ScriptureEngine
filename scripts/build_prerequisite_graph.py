#!/usr/bin/env python3
"""Build the prerequisite graph for adaptive assessment.

Connects knowledge items sharing the same verse-pair (verse_id → target_verse)
with prerequisite edges based on PaRDeS level hierarchy.

Uses Python dicts for the cross-layer join — avoids heavy SQL JOINs.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import defaultdict

from lib.db import get_db


def build_graph():
    conn = get_db()
    conn.execute("DELETE FROM knowledge_prerequisites")

    # Load all items into memory: {(verse_id, target_verse): [(id, level), ...]}
    rows = conn.execute("""
        SELECT id, verse_id, target_verse, pa_r_de_s_level
        FROM knowledge_items
    """).fetchall()

    # Group by verse-pair
    pair_to_items = defaultdict(list)
    for r in rows:
        pair_to_items[(r["verse_id"], r["target_verse"])].append(
            (r["id"], r["pa_r_de_s_level"])
        )

    # PaRDeS depth order
    LEVEL_DEPTH = {"p'shat": 0, "remez": 1, "drash": 2, "sod": 3}

    total_edges = 0
    edge_sources = {"cross": 0}

    # For each verse-pair, connect shallower → deeper levels
    for _pair, items in pair_to_items.items():
        if len(items) < 2:
            continue

        # Group by level
        by_level = defaultdict(list)
        for item_id, level in items:
            by_level[level].append(item_id)

        levels = list(by_level.keys())
        if len(levels) < 2:
            continue

        # Create edges: every shallower item → every deeper item
        for shallow_level in levels:
            for deep_level in levels:
                if LEVEL_DEPTH.get(shallow_level, -1) >= LEVEL_DEPTH.get(deep_level, -1):
                    continue
                for shallow_id in by_level[shallow_level]:
                    for deep_id in by_level[deep_level]:
                        conn.execute(
                            "INSERT OR IGNORE INTO knowledge_prerequisites (item_id, prerequisite_item_id, confidence, source) VALUES (?, ?, 0.8, 'cross')",
                            (deep_id, shallow_id)
                        )
                        total_edges += 1
                        edge_sources["cross"] += 1

    # Validate DAG
    edges = conn.execute("SELECT item_id, prerequisite_item_id FROM knowledge_prerequisites").fetchall()
    adj = defaultdict(list)
    for e in edges:
        adj[e["item_id"]].append(e["prerequisite_item_id"])

    has_cycle = False
    visited = set()
    in_stack = set()

    def dfs(node):
        nonlocal has_cycle
        if node in in_stack:
            has_cycle = True
            return
        if node in visited:
            return
        visited.add(node)
        in_stack.add(node)
        for prereq in adj.get(node, []):
            dfs(prereq)
        in_stack.discard(node)

    for node in list(adj.keys()):
        if node not in visited:
            dfs(node)

    conn.commit()
    conn.close()

    print(f"Done: {total_edges:,} prerequisite edges")
    if has_cycle:
        print("  \u2717 Cycle detected!")
    else:
        print("  \u2713 DAG validation passed")
    print(f"  cross-layer: {edge_sources['cross']:,}")


if __name__ == "__main__":
    print("Building prerequisite graph...")
    build_graph()
