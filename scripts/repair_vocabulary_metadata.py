#!/usr/bin/env python3
"""Repair legacy vocabulary metadata corrupted by the old numeric-key lexicon.

Earlier fix scripts copied definitions from a corrupted lexicon where several
numeric-key rows held the wrong word (e.g. "Father (Aramaic). Root: אב." on the
lesson for אָבַד "to perish"). This repairs the specific corrupted lessons that
survived exact-lemma alignment, keeping the aligned lemma/gloss authoritative.
"""

import argparse
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

# node_id -> (description, root)
# Descriptions are written from the authoritative Strong's definitions.
METADATA_FIXES = {
    "vocab_מקים_89": (
        "To arise, stand up, or establish (Strong's H6965, root קום). Used of rising, "
        "standing, and God fulfilling promises.",
        "קום",
    ),
    "vocab_מלכו_187": (
        "To reign or become king (Strong's H4427, root מלך). The verb behind the noun "
        "for king.",
        "מלך",
    ),
    "vocab_יואב_251": (
        "Joab (Strong's H3097) — a personal name, borne by David's nephew and army "
        "commander.",
        "יואב",
    ),
    "vocab_אבדה_276": (
        "To perish, be lost, or wander away (Strong's H6, root אבד).",
        "אבד",
    ),
    "vocab_אביו_24": (
        "Father — the male progenitor, ancestor, or source (Strong's H1, root אב).",
        "אב",
    ),
}


def repair(mem_db: Path) -> dict:
    conn = sqlite3.connect(mem_db)
    conn.row_factory = sqlite3.Row
    fixed = 0
    for node_id, (description, root) in METADATA_FIXES.items():
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
        if not row:
            continue
        lesson = json.loads(row["content_json"])
        lesson["description"] = description
        lesson["root"] = root
        lesson["title"] = f"{lesson.get('hebrew', '')} — {lesson.get('gloss', '')}"
        encoded = json.dumps(lesson, ensure_ascii=False)
        conn.execute(
            "UPDATE hebrew_lessons SET content_json=?, version=version+1, updated_at=datetime('now') "
            "WHERE node_id=? AND content_json<>?",
            (encoded, node_id, encoded),
        )
        conn.execute(
            "UPDATE hebrew_nodes SET title=?, description=? WHERE id=?",
            (lesson["title"], description[:200], node_id),
        )
        fixed += 1
    conn.commit()
    conn.close()
    return {"fixed": fixed}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=MEM_DB)
    args = parser.parse_args()
    result = repair(args.db)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
