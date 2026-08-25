"""Track E1: the memorization mode registry is complete, honest, and live."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes.memorize import _MODE_STATUSES, _mode_registry, list_memorize_modes


def test_registry_lists_all_plan_modes():
    ids = {m["id"] for m in _mode_registry()}
    for required in (
        "scripture_queue", "interleaved_review", "palace_walk",
        "hebrew_review", "hebrew_quiz_practice", "progressive_hints",
        "audio_mode", "hebrew_cloze", "two_way_translation",
        "daily_maintenance", "audio_first_commute", "hebrew_visual_only",
    ):
        assert required in ids, f"missing mode: {required}"


def test_every_mode_has_honest_metadata():
    for m in _mode_registry():
        assert m["status"] in _MODE_STATUSES
        assert m["label"] and m["scheduler"].startswith("fsrs-5")
        if m["status"] == "available":
            # A visible mode must have a working route to back it.
            assert m["surface"], f"{m['id']} marked available with no route"
        else:
            assert m["surface"] is None


def test_endpoint_returns_matrix_with_totals():
    data = list_memorize_modes()["data"]
    assert data["scheduler"] == "fsrs-5"
    assert len(data["modes"]) >= 12
    assert set(data["totals"].keys()) == {"scripture_queued"}


def test_available_modes_are_exactly_the_verified_backends():
    available = {m["id"] for m in _mode_registry() if m["status"] == "available"}
    assert {
        "scripture_queue", "interleaved_review", "palace_walk",
        "weakest_first", "next_best", "hebrew_review", "hebrew_quiz_practice",
    } == available
