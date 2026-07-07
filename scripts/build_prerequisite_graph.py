#!/usr/bin/env python3
"""Build the prerequisite graph for adaptive assessment.

Connects knowledge items that share the same verse-pair (verse_id → target_verse)
with prerequisite edges based on type chains and PaRDeS level hierarchy.

This produces a sparse, meaningful DAG — not a dense cross-product mesh.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.db import get_db

# ── Type chain definitions (matched to actual knowledge_items types) ──
# Within each layer, some connection types are prerequisites for others.
# Items share the same verse-pair to be connected.

PSHAT_CHAINS = [
    ["same_lemma", "same_morphology"],
    ["same_lemma", "keyword_linking"],
    ["same_morphology", "keyword_linking"],
]

# ── Cross-layer pairs (PaRDeS depth order) ──
CROSS_LAYER_PAIRS = [
    ("p'shat", "remez"),
    ("remez", "drash"),
    ("drash", "sod"),
    ("p'shat", "sod"),       # direct skip for layers with gaps
    ("p'shat", "drash"),
    ("remez", "sod"),
]


def build_graph():
    conn = get_db()
    conn.execute("DELETE FROM knowledge_prerequisites")
    total_edges = 0
    edge_sources = {"within": 0, "cross": 0}

    # ── Part A: Within-layer chains (same verse-pair) ──
    for layer_name, chains in [("p'shat", PSHAT_CHAINS)]:
        for chain in chains:
            for i in range(len(chain) - 1):
                prereq_type = chain[i]      # simpler
                dep_type = chain[i + 1]     # builds on it

                rows = conn.execute("""
                    SELECT a.id as prereq_id, b.id as dep_id
                    FROM knowledge_items a
                    JOIN knowledge_items b
                      ON a.verse_id = b.verse_id
                     AND a.target_verse = b.target_verse
                    WHERE a.connection_type = ?
                      AND b.connection_type = ?
                      AND a.id != b.id
                """, (prereq_type, dep_type)).fetchall()

                for r in rows:
                    conn.execute(
                        "INSERT OR IGNORE INTO knowledge_prerequisites (item_id, prerequisite_item_id, confidence, source) VALUES (?, ?, 0.9, 'within')",
                        (r["dep_id"], r["prereq_id"])
                    )
                    total_edges += 1
                    edge_sources["within"] += 1

                print(f"  within {layer_name}: {prereq_type} → {dep_type}: {len(rows)} edges")

    # ── Part B: Cross-layer prerequisites (same verse-pair) ──
    for shallow_layer, deep_layer in CROSS_LAYER_PAIRS:
        rows = conn.execute("""
            SELECT a.id as shallow_id, b.id as deep_id
            FROM knowledge_items a
            JOIN knowledge_items b
              ON a.verse_id = b.verse_id
             AND a.target_verse = b.target_verse
            WHERE a.pa_r_de_s_level = ?
              AND b.pa_r_de_s_level = ?
              AND a.id != b.id
        """, (shallow_layer, deep_layer)).fetchall()

        for r in rows:
            conn.execute(
                "INSERT OR IGNORE INTO knowledge_prerequisites (item_id, prerequisite_item_id, confidence, source) VALUES (?, ?, 0.8, 'cross')",
                (r["deep_id"], r["shallow_id"])
            )
            total_edges += 1
            edge_sources["cross"] += 1

        print(f"  cross-layer {shallow_layer}→{deep_layer}: {len(rows)} edges")

    # ── Part C: Validate DAG ──
    print("\nValidating DAG...")
    edges = conn.execute("SELECT item_id, prerequisite_item_id FROM knowledge_prerequisites").fetchall()

    adj = {}
    for e in edges:
        kid = e["item_id"]
        prereq = e["prerequisite_item_id"]
        if kid not in adj:
            adj[kid] = []
        adj[kid].append(prereq)

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

    if not has_cycle:
        print("  \u2713 DAG validation passed — no cycles")
    else:
        print("  \u2717 Cycle detected — check chains")

    conn.commit()
    conn.close()

    return {"total_edges": total_edges, "edge_sources": edge_sources}


if __name__ == "__main__":
    print("Building prerequisite graph...")
    result = build_graph()
    print(f"\nDone: {result['total_edges']} prerequisite edges")
    for src, count in result["edge_sources"].items():
        print(f"  {src}: {count}")
