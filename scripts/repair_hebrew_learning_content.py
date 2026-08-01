#!/usr/bin/env python3
"""Remove unsafe generated Hebrew practice and quarantine non-OT examples."""

import argparse
import json
import re
import sqlite3
from pathlib import Path

try:
    from scripts.validate_hebrew_learning_content import valid_ot_ref
except ModuleNotFoundError:  # Direct execution sets scripts/ as sys.path[0].
    from validate_hebrew_learning_content import valid_ot_ref

TAUTOLOGY = re.compile(r"^Is '.+' a .+ in Biblical Hebrew\?$")


def repair(db_path: Path) -> dict[str, int]:
    counts = {
        "examples_quarantined": 0,
        "practice_removed": 0,
        "practice_duplicates_removed": 0,
        "edges_removed": 0,
        "graph_edges_reoriented": 0,
    }
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    for row in conn.execute("SELECT node_id, content_json FROM hebrew_lessons"):
        try:
            lesson = json.loads(row["content_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        ref = lesson.get("verse_example")
        if not ref or valid_ot_ref(ref):
            continue
        lesson["example_status"] = "quarantined_non_ot"
        lesson["example_note"] = "Removed from the learner view: the example was not from the Hebrew Bible."
        for key in ("verse_example", "verse_hebrew", "verse_english"):
            lesson.pop(key, None)
        conn.execute(
            "UPDATE hebrew_lessons SET content_json=?, version=version+1, updated_at=datetime('now') WHERE node_id=?",
            (json.dumps(lesson, ensure_ascii=False), row["node_id"]),
        )
        counts["examples_quarantined"] += 1

    remove_ids = []
    for row in conn.execute(
        "SELECT id,question_type,question_text,options_json,correct_answer,explanation FROM hebrew_practice_items"
    ):
        try:
            options = json.loads(row["options_json"] or "[]")
        except json.JSONDecodeError:
            options = []
        answer_missing = (
            row["question_type"] in {"multiple_choice", "true_false", "classification", "contrast"}
            and options
            and row["correct_answer"] not in options
        )
        duplicate_options = len({str(option) for option in options}) != len(options)
        non_ot_practice = "dss." in f"{row['question_text']} {row['explanation'] or ''}".casefold()
        if TAUTOLOGY.match(row["question_text"]) or any(option == "—" for option in options) or answer_missing or duplicate_options or non_ot_practice:
            remove_ids.append((row["id"],))
    conn.executemany("DELETE FROM hebrew_practice_items WHERE id=?", remove_ids)
    counts["practice_removed"] = len(remove_ids)

    before = conn.total_changes
    conn.execute("""
        DELETE FROM hebrew_practice_items
        WHERE id NOT IN (
            SELECT MIN(id) FROM hebrew_practice_items
            GROUP BY node_id,question_type,question_text,correct_answer
        )
    """)
    counts["practice_duplicates_removed"] = conn.total_changes - before
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_hebrew_practice_unique
        ON hebrew_practice_items(node_id,question_type,question_text,correct_answer)
    """)

    before = conn.total_changes
    conn.execute("""
        DELETE FROM hebrew_edges
        WHERE source_id NOT IN (SELECT id FROM hebrew_nodes)
           OR target_id NOT IN (SELECT id FROM hebrew_nodes)
    """)
    counts["edges_removed"] = conn.total_changes - before

    # Standardize base curriculum edges on prerequisite -> dependent, matching the API.
    try:
        from scripts.build_hebrew_graph import build_edges
    except ModuleNotFoundError:
        from build_hebrew_graph import build_edges
    node_ids = {row[0] for row in conn.execute("SELECT id FROM hebrew_nodes")}
    for prerequisite, dependent, edge_type, weight in build_edges():
        if prerequisite not in node_ids or dependent not in node_ids:
            continue
        removed = conn.execute(
            "DELETE FROM hebrew_edges WHERE source_id=? AND target_id=? AND edge_type=?",
            (dependent, prerequisite, edge_type),
        ).rowcount
        inserted = conn.execute(
            "INSERT OR IGNORE INTO hebrew_edges (source_id,target_id,edge_type,weight) VALUES (?,?,?,?)",
            (prerequisite, dependent, edge_type, weight),
        ).rowcount
        counts["graph_edges_reoriented"] += removed + inserted

    conn.commit()
    conn.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/memorize.db"))
    args = parser.parse_args()
    counts = repair(args.db)
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
