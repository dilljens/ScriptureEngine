"""One scheduler: memorize + Hebrew import the identical FSRS core.

lib/api/fsrs.py is the single canonical implementation. Both routes alias
its names, so this file pins (a) object identity and (b) the canonical
behaviors both surfaces depend on — especially that Hard(2) is a
successful recall with a multiplier, not a lapse.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.api import fsrs
from web.routes import hebrew as H
from web.routes import memorize as M


def test_single_implementation_by_identity():
    assert M._fsrs_schedule is H.fsrs_schedule is fsrs.schedule
    assert M._fsrs_initial_stability is H.fsrs_initial_stability is fsrs.initial_stability
    assert M._fsrs_next_interval is H.fsrs_next_interval is fsrs.next_interval
    assert M._fsrs_next_difficulty is H.fsrs_next_difficulty is fsrs.next_difficulty
    assert M._fsrs_stability_after_success is H.fsrs_stability_after_success
    assert M._fsrs_stability_after_success is fsrs.stability_after_success
    assert M._fsrs_stability_after_failure is H.fsrs_stability_after_failure
    assert M._fsrs_stability_after_failure is fsrs.stability_after_failure
    assert M.FSRS_W is H.FSRS_W is fsrs.FSRS_W
    assert M._humanize_interval is H.fsrs_humanize_interval is fsrs.humanize_interval


def test_hard_is_success_not_lapse():
    # Canonical FSRS: Again(1) fails; Hard(2) succeeds with a multiplier.
    # From a healthy state, Hard must GROW stability, Again must shrink it.
    s, d = 10.0, 5.0
    s_hard, _, _ = fsrs.schedule(s, d, 2)
    s_again, _, _ = fsrs.schedule(s, d, 1)
    assert s_hard > s, "Hard(2) must grow stability (successful recall)"
    assert s_again < s, "Again(1) must shrink stability (lapse)"
    # Ordering across grades is monotonic for a fresh card.
    ivs = [fsrs.schedule(s, d, r)[2] for r in (1, 2, 3, 4)]
    assert ivs == sorted(ivs)


def test_canonical_vectors_against_reference():
    # Hardcoded from py-fsrs 6.x (Scheduler defaults): state S=5, D=4.5,
    # reviewed 6 days later. Any drift from the reference fails here.
    expected = {
        1: (0.980488, 8.177416, 1),
        2: (14.149185, 6.334072, 14),
        3: (20.213145, 4.490728, 20),
        4: (33.492698, 2.647385, 33),
    }
    for grade, (ns, nd, iv) in expected.items():
        got = fsrs.schedule(5.0, 4.5, grade, 6.0)
        assert abs(got[0] - ns) < 1e-5, (grade, got)
        assert abs(got[1] - nd) < 1e-5, (grade, got)
        assert got[2] == iv, (grade, got)


def test_short_term_branch_vectors():
    # Same-day re-review of existing memory (S=5): Again may drop,
    # Hard/Good floor at no-change, Easy grows. Values from py-fsrs.
    expected = {1: 1.596818, 2: 5.0, 3: 5.0, 4: 8.129610}
    for grade, ns in expected.items():
        got = fsrs.schedule(5.0, 4.5, grade, 0.0)[0]
        assert abs(got - ns) < 1e-5, (grade, got)


def test_initial_difficulty_is_canonical():
    # D0(G) = w4 − e^(w5·(G−1)) + 1, clamped — not flat 5.0.
    assert fsrs.initial_difficulty(1) == 6.4133
    assert abs(fsrs.initial_difficulty(2) - 5.1122) < 1e-3
    assert abs(fsrs.initial_difficulty(3) - 2.1181) < 1e-3
    assert fsrs.initial_difficulty(4) == 1.0


def test_retrievability_defining_property():
    # R(S) == 0.9 by construction, at any stability.
    for s in (0.5, 2.0, 10.0, 100.0):
        assert abs(fsrs.retrievability(s, s) - 0.9) < 1e-12, s
    assert fsrs.retrievability(0, 5) == 0.0
    assert fsrs.retrievability(10.0, 0) > 0.9


def test_humanize_labels():
    assert fsrs.humanize_interval(1) == "1d"
    assert fsrs.humanize_interval(13) == "13d"
    assert fsrs.humanize_interval(14) == "2w"
    assert fsrs.humanize_interval(90) == "3mo"
    assert fsrs.humanize_interval(400) == "1.1y"
