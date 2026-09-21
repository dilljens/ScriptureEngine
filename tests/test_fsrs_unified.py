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


def test_humanize_labels():
    assert fsrs.humanize_interval(1) == "1d"
    assert fsrs.humanize_interval(13) == "13d"
    assert fsrs.humanize_interval(14) == "2w"
    assert fsrs.humanize_interval(90) == "3mo"
    assert fsrs.humanize_interval(400) == "1.1y"
