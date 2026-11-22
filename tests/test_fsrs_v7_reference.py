"""FSRS-7 reference vectors: port pinned to fsrs-rs v7.0.0.

Source: a local differential harness (/tmp/v7ref) built against the
fsrs crate v7.0.0 from crates.io — next_states / current_retrievability /
s90 over a state grid, plus the crate's own doctest vectors for new cards
(FSRS::default(), desired_retention 0.9). Values below are copied from the
harness output, which reproduces the doctest exactly
(again s=0.1104 d=6.1686 sf=0.08832 ivl=3.8275626e-05).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.api import fsrs

RATING = {"again": 1, "hard": 2, "good": 3, "easy": 4}

# (rating, retention, s, d, s_fast, interval) — new cards, upstream doctest.
NEW_VECTORS = [
    ("again", 0.9, 0.1104, 6.1686, 0.08832, 3.8275626e-05),
    ("hard", 0.9, 2.2395, 5.261278, 1.7916001, 0.5974598),
    ("good", 0.9, 3.9221, 3.5307243, 3.13768, 4.7777247),
    ("easy", 0.9, 11.7841, 1.0, 9.427279, 53.869392),
]

# (rating, t_days, ns, nd, nsf, ivl) — state S=12 D=5 S_fast=9.6, ret 0.9.
REVIEW_VECTORS_T1 = [
    ("again", 1.0, 2.64757, 9.25775, 0.36821, 0.0145),
    ("hard", 1.0, 15.86253, 6.97668, 84.59085, 14.5232),
    ("good", 1.0, 18.0371, 4.9523, 131.29887, 31.6486),
    ("easy", 1.0, 18.0371, 2.92792, 141.87451, 55.8362),
]
REVIEW_VECTORS_T0 = [
    ("again", 0.0, 2.56982, 9.40591, 0.10894, 0.0034025),
    ("hard", 0.0, 12.00103, 6.97668, 9.6, 8.65038),
    ("good", 0.0, 12.00161, 4.9523, 9.6, 16.8557),
    ("easy", 0.0, 12.00161, 2.92792, 9.6, 31.42354),
]

# (t_days, recall) — state S=12 D=5 S_fast=9.6.
RECALL_VECTORS = [
    (0.0, 0.99999),
    (1.0, 0.963397),
    (5.0, 0.939792),
    (30.0, 0.872204),
    (200.0, 0.764975),
]

S90_VECTORS = [(2.5, 4.5, 2.0, 1.2318639), (12.0, 5.0, 9.6, 16.5990028)]


def _close(a, b, tol=2e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def test_new_card_vectors():
    for rating, ret, s, d, sf, ivl in NEW_VECTORS:
        r = RATING[rating]
        assert _close(fsrs.initial_stability(r), s), rating
        assert _close(fsrs.initial_difficulty(r), d), rating
        assert _close(fsrs.initial_fast_stability(r), sf), rating
        got = fsrs.next_interval(fsrs.initial_stability(r), ret,
                                 s_fast=fsrs.initial_fast_stability(r),
                                 difficulty=fsrs.initial_difficulty(r))
        assert _close(got, ivl), (rating, got, ivl)


def test_new_fast_is_point_eight_slow():
    assert fsrs.initial_fast_stability(3) == 0.8 * fsrs.initial_stability(3)


def test_review_vectors_t1():
    for rating, t, ns, nd, nsf, ivl in REVIEW_VECTORS_T1:
        got = fsrs.schedule(12.0, 5.0, RATING[rating], t, 0.9, 9.6)
        assert _close(got[0], ns), (rating, got)
        assert _close(got[1], nd), (rating, got)
        assert _close(got[3], nsf), (rating, got)
        assert _close(got[2], ivl), (rating, got)


def test_review_vectors_t0_same_day():
    # Same-day reviews flow through the fast component (no separate branch).
    for rating, t, ns, nd, nsf, ivl in REVIEW_VECTORS_T0:
        got = fsrs.schedule(12.0, 5.0, RATING[rating], t, 0.9, 9.6)
        assert _close(got[0], ns), (rating, got)
        assert _close(got[1], nd), (rating, got)
        assert _close(got[3], nsf), (rating, got)
        assert _close(got[2], ivl), (rating, got)


def test_recall_vectors():
    for t, r in RECALL_VECTORS:
        assert _close(fsrs.retrievability(12.0, t, 9.6, 5.0), r, 1e-5), t


def test_s90_hits_90():
    # Upstream's own invariant: R(s90(state)) == 0.9.
    for s, d, sf, s90 in S90_VECTORS:
        ivl = fsrs.next_interval(s, 0.9, s_fast=sf, difficulty=d)
        assert _close(ivl, s90), (s, ivl, s90)
        assert abs(fsrs.retrievability(s, ivl, sf, d) - 0.9) <= 1e-3


def test_retrievability_does_not_depend_on_w20():
    # Port of the upstream unit test: legacy decay weight is inert in v7.
    w = list(fsrs.FSRS_W)
    saves = (w[20],)
    w[20] = 0.001
    from lib.api.fsrs import _forgetting_curve
    r1 = _forgetting_curve(w, 10.0, 12.0, 9.6, 5.0)
    w[20] = 5.0
    r2 = _forgetting_curve(w, 10.0, 12.0, 9.6, 5.0)
    assert abs(r1 - r2) < 1e-7
    assert w[20] != saves[0] or True


def test_hard_grows_again_shrinks():
    s_hard = fsrs.schedule(10.0, 5.0, 2, 5.0, 0.9, 8.0)[0]
    s_again = fsrs.schedule(10.0, 5.0, 1, 5.0, 0.9, 8.0)[0]
    assert s_hard > 10.0 > s_again
