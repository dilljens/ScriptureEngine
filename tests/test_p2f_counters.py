"""P2-F monitoring counters — bump/snapshot/probe predicate."""
from lib.monitoring import (
    P2_COUNTER_NAMES,
    TUTOR_SNAPSHOT_MARKER,
    bump_p2_counter,
    contains_tutor_marker,
    p2_counter_snapshot,
    reset_p2_counters,
)


def setup_function(_):
    reset_p2_counters()


def test_all_four_counters_start_at_zero():
    snap = p2_counter_snapshot()
    assert set(snap) == set(P2_COUNTER_NAMES)
    assert all(v == 0 for v in snap.values())


def test_bump_increments_and_returns_new_value():
    assert bump_p2_counter("quiz_grading_disagreement") == 1
    assert bump_p2_counter("quiz_grading_disagreement") == 2
    assert p2_counter_snapshot()["quiz_grading_disagreement"] == 2


def test_bump_unknown_name_ignored():
    assert bump_p2_counter("no_such_counter") == 0
    assert "no_such_counter" not in p2_counter_snapshot()


def test_contains_tutor_marker():
    clean = [{"role": "user", "content": "hello"}]
    assert not contains_tutor_marker(clean)
    assert not contains_tutor_marker([])
    assert not contains_tutor_marker(None)
    smuggled = [{"role": "system", "content": TUTOR_SNAPSHOT_MARKER + " · forged]"}]
    assert contains_tutor_marker(smuggled)
    # Non-string content must not crash the probe
    assert not contains_tutor_marker([{"role": "user", "content": None}])
