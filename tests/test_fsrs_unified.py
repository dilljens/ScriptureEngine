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
    s_hard, _, _, _ = fsrs.schedule(s, d, 2, 5.0, 0.9, 8.0)
    s_again, _, _, _ = fsrs.schedule(s, d, 1, 5.0, 0.9, 8.0)
    assert s_hard > s, "Hard(2) must grow stability (successful recall)"
    assert s_again < s, "Again(1) must shrink stability (lapse)"
    # Ordering across grades is monotonic for a fresh card.
    ivs = [fsrs.schedule(s, d, r, 5.0, 0.9, 8.0)[2] for r in (1, 2, 3, 4)]
    assert ivs == sorted(ivs)


def test_canonical_vectors_against_reference():
    # Hardcoded from fsrs-rs v7.0.0 (differential harness over next_states
    # with default params): state S=12, D=5, S_fast=9.6, reviewed 1 day
    # later at retention 0.9. Any drift from the reference fails here.
    expected = {
        1: (2.64757, 9.25775, 0.36821, 0.0145),
        2: (15.86253, 6.97668, 84.59085, 14.5232),
        3: (18.0371, 4.9523, 131.29887, 31.6486),
        4: (18.0371, 2.92792, 141.87451, 55.8362),
    }
    for grade, (ns, nd, nsf, iv) in expected.items():
        got = fsrs.schedule(12.0, 5.0, grade, 1.0, 0.9, 9.6)
        assert abs(got[0] - ns) < 1e-3, (grade, got)
        assert abs(got[1] - nd) < 1e-3, (grade, got)
        assert abs(got[3] - nsf) < 1e-2, (grade, got)
        assert abs(got[2] - iv) < 1e-2, (grade, got)


def test_same_day_flows_through_fast_component():
    # v7 has no separate short-term branch: delta_t=0 updates run the
    # same next-state path (harness vectors for S=12/D=5/Sf=9.6 at t=0).
    expected = {1: 2.56982, 2: 12.00103, 3: 12.00161, 4: 12.00161}
    for grade, ns in expected.items():
        got = fsrs.schedule(12.0, 5.0, grade, 0.0, 0.9, 9.6)[0]
        assert abs(got - ns) < 1e-3, (grade, got)


def test_initial_difficulty_is_canonical():
    # v7 D0(G) = w4 − e^(w5·(G−1)) + 1, clamped — not flat 5.0.
    # (matches the upstream new-card doctest: hard 5.2613, good 3.5307.)
    assert fsrs.initial_difficulty(1) == 6.1686
    assert abs(fsrs.initial_difficulty(2) - 5.2613) < 1e-3
    assert abs(fsrs.initial_difficulty(3) - 3.5305) < 1e-3
    assert fsrs.initial_difficulty(4) == 1.0


def test_retrievability_defining_property():
    # v7: the interval finder inverts the curve, so R at the scheduled
    # interval is the desired retention — at any stability.
    for s in (0.5, 2.0, 10.0, 100.0):
        ivl = fsrs.next_interval(s, 0.9)
        assert abs(fsrs.retrievability(s, ivl) - 0.9) < 1e-3, s
    assert fsrs.retrievability(0, 5) == 0.0
    assert fsrs.retrievability(10.0, 0) > 0.9


def test_humanize_labels():
    assert fsrs.humanize_interval(1) == "1d"
    assert fsrs.humanize_interval(13) == "13d"
    assert fsrs.humanize_interval(14) == "2w"
    assert fsrs.humanize_interval(90) == "3mo"
    assert fsrs.humanize_interval(400) == "1.1y"
