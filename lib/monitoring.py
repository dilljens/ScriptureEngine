"""P2-F monitoring counters (plan: hebrew-tutor-phase2, Track P2-F).

In-process integer counters for quiz grading disagreement, progress-event
idempotency hits, tutor-memory leakage probes, and numerical citation rate.
No dependencies — safe to import from lib/, web/routes/, and web/server.py
without creating import cycles.

Surfacing: exposed through the operator /metrics endpoint only, never in
the public /api/v1/health payload.
"""

# Counter names are part of the /metrics exposition; rename with care.
QUIZ_GRADING_DISAGREEMENT = "quiz_grading_disagreement"
PROGRESS_IDEMPOTENCY_HIT = "progress_idempotency_hit"
TUTOR_MEMORY_LEAK_PROBE = "tutor_memory_leak_probe"
NUMERICAL_CITATION = "numerical_citation"

P2_COUNTER_NAMES = (
    QUIZ_GRADING_DISAGREEMENT,
    PROGRESS_IDEMPOTENCY_HIT,
    TUTOR_MEMORY_LEAK_PROBE,
    NUMERICAL_CITATION,
)

_P2_COUNTERS = {name: 0 for name in P2_COUNTER_NAMES}

# Marker heading every server-derived Hebrew Tutor learner snapshot. The
# general-chat path probes inbound messages for this marker: its presence
# there means tutor state leaked (or was smuggled) across the mode boundary.
TUTOR_SNAPSHOT_MARKER = "[LEARNER PROGRESS SNAPSHOT"


def bump_p2_counter(name: str) -> int:
    """Increment a P2 counter; returns the new value. Unknown names ignored."""
    if name not in _P2_COUNTERS:
        return 0
    _P2_COUNTERS[name] += 1
    return _P2_COUNTERS[name]


def p2_counter_snapshot() -> dict:
    """Copy of current counter values for exposition."""
    return dict(_P2_COUNTERS)


def reset_p2_counters() -> None:
    """Zero all counters. Tests only — never call in production paths."""
    for name in _P2_COUNTERS:
        _P2_COUNTERS[name] = 0


def contains_tutor_marker(messages) -> bool:
    """True if any message's content carries the tutor snapshot marker."""
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        content = m.get("content", "")
        if isinstance(content, str) and TUTOR_SNAPSHOT_MARKER in content:
            return True
    return False
