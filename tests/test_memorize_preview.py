"""Preview-aware review + scripture-mastery import (memorize route)."""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.memorize import (
    auto_preview_level,
    effective_rating,
    expand_mastery_entry,
    load_mastery_list,
    next_preview_level,
    parse_verse_spec,
)

BASE = Path(__file__).resolve().parent.parent


def test_parse_verse_spec_ranges_lists_combos():
    assert parse_verse_spec("5") == [5]
    assert parse_verse_spec("26-27") == [26, 27]
    assert parse_verse_spec("3-17") == list(range(3, 18))
    assert parse_verse_spec("23,26") == [23, 26]
    assert parse_verse_spec("15,20-21") == [15, 20, 21]
    assert parse_verse_spec("45,47-48") == [45, 47, 48]
    assert parse_verse_spec("36,41-42") == [36, 41, 42]
    assert parse_verse_spec("") == []
    assert parse_verse_spec("abc") == []


def test_expand_mastery_entry_builds_ids():
    assert expand_mastery_entry({"book": "gen", "chapter": 1, "verses": "26-27"}) == [
        "gen.1.26", "gen.1.27",
    ]
    assert expand_mastery_entry({"book": "dc76", "chapter": 76, "verses": "22-24"}) == [
        "dc76.76.22", "dc76.76.23", "dc76.76.24",
    ]


def test_auto_preview_level_less_help_as_mastery_grows():
    assert auto_preview_level(0.0, 0) == 100  # new card: max hints
    assert auto_preview_level(0.1, 3) == 100
    assert auto_preview_level(0.4, 3) == 75
    assert auto_preview_level(0.6, 3) == 50
    assert auto_preview_level(0.8, 3) == 25
    assert auto_preview_level(0.95, 10) == 0  # mastered: pure recall


def test_next_preview_level_steps_with_confidence():
    assert next_preview_level(100, 4) == 75  # recalled well → less help
    assert next_preview_level(50, 3) == 25
    assert next_preview_level(25, 1) == 50  # struggled → more help
    assert next_preview_level(0, 1) == 25
    assert next_preview_level(25, 4) == 0
    assert next_preview_level(0, 4) == 0  # floor
    assert next_preview_level(100, 1) == 100  # ceiling


def test_effective_rating_weights_confidence_by_help():
    # Pure recall or light hints: full credit
    assert effective_rating(4, "none", 0) == 4
    assert effective_rating(4, "first_letters", 25) == 4
    assert effective_rating(4, "first_letters", 50) == 4
    # Heavy first-letter hints: Easy counts as Good
    assert effective_rating(4, "first_letters", 75) == 3
    assert effective_rating(4, "first_letters", 100) == 3
    assert effective_rating(3, "first_letters", 100) == 3
    assert effective_rating(1, "first_letters", 100) == 1
    # Full text: seeing the answer caps at Hard
    assert effective_rating(4, "full_text", 0) == 2
    assert effective_rating(3, "full_text", 0) == 2
    assert effective_rating(1, "full_text", 0) == 1
    # Unknown mode defaults to no penalty
    assert effective_rating(4, "bogus", 0) == 4


def test_mastery_list_has_100_passages_25_per_group():
    passages = load_mastery_list()
    assert len(passages) == 100
    assert sorted(p["n"] for p in passages) == list(range(1, 101))
    groups = {}
    for p in passages:
        assert {"n", "group", "reference", "book", "chapter", "verses"} <= set(p)
        assert expand_mastery_entry(p), f"no verses parsed: {p['reference']}"
        groups.setdefault(p["group"], 0)
        groups[p["group"]] += 1
    assert groups == {
        "Old Testament": 25,
        "New Testament": 25,
        "Book of Mormon": 25,
        "Doctrine and Covenants": 25,
    }


def test_mastery_verse_ids_all_exist_in_library():
    """Read-only check against the real canon DB — all 100 import cleanly."""
    db = BASE / "data" / "processed" / "scripture.db"
    if not db.exists():
        return  # library not built here — skip, JSON shape is covered above
    passages = load_mastery_list()
    wanted = [vid for p in passages for vid in expand_mastery_entry(p)]
    conn = sqlite3.connect(str(db))
    try:
        rows = conn.execute(
            f"SELECT id FROM verses WHERE id IN ({','.join('?' * len(wanted))})",
            wanted,
        ).fetchall()
    finally:
        conn.close()
    missing = sorted(set(wanted) - {r[0] for r in rows})
    assert not missing, f"mastery verses missing from library: {missing}"


def test_mastery_json_file_is_valid():
    raw = json.loads((BASE / "data" / "scripture_mastery.json").read_text())
    assert len(raw["passages"]) == 100
