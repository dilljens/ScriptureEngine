"""Canonical FSRS-4.5 scheduling core, shared by every review surface.

Both the scripture-memorize scheduler (web/routes/memorize.py) and the
Hebrew scheduler (web/routes/hebrew.py) import these names — there is
exactly one implementation of the algorithm. Route-specific layers
(Math Academy learning-speed adjustment, preview-help weighting) stay in
the routes and are documented as extensions, not divergences.

Conventions (canonical FSRS):
- Rating 1 (Again) is a lapse; 2/3/4 (Hard/Good/Easy) are successful
  recalls with stability multipliers. Hard is NOT a failure.
- Intervals are whole days, minimum 1.
"""

import math

FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
          1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
          1.8729, 0.5425, 0.0912, 0.0658, 0.1542]


def initial_stability(rating):
    """Initial stability (in days) based on rating 1-4."""
    if rating < 1 or rating > 4:
        rating = 3
    return FSRS_W[rating - 1]


def next_interval(stability, request_retention=0.9):
    """Next review interval in days."""
    if stability <= 0:
        return 0
    return max(1, round(stability * (math.log(request_retention) / math.log(0.9)) ** (1.0 / FSRS_W[10])))


def stability_after_success(stability, difficulty, rating):
    """Calculate new stability after a successful recall (ratings 2-4)."""
    difficulty_weight = math.pow(FSRS_W[7], difficulty - 1)
    retrieval_strength = math.pow(stability, -FSRS_W[9])
    # Rating multiplier
    rating_mult = FSRS_W[8]
    if rating == 2:  # Hard
        rating_mult = FSRS_W[8] * FSRS_W[15]
    elif rating == 4:  # Easy
        rating_mult = FSRS_W[8] * FSRS_W[16]

    new_s = stability * (1 + rating_mult * retrieval_strength * difficulty_weight)
    return new_s


def stability_after_failure(stability, difficulty, _rating):
    """Calculate new stability after a failed recall (rating 1 only)."""
    difficulty_pow = math.pow(difficulty, FSRS_W[12])
    stability_factor = math.pow(stability, -FSRS_W[13])
    new_s = FSRS_W[11] * difficulty_pow * stability_factor * (stability + 1)
    return new_s


def next_difficulty(difficulty, rating):
    """Calculate next difficulty after a review. Clamped to [1, 10]."""
    delta = -FSRS_W[6] if rating >= 3 else FSRS_W[6]
    mean_reversion = FSRS_W[7] * (FSRS_W[4] - difficulty)
    new_d = difficulty + delta + mean_reversion
    return max(1.0, min(10.0, new_d))


def retrievability(stability, days_since):
    """Probability of recall after elapsed days."""
    if stability <= 0:
        return 0
    return math.exp(-days_since / stability * math.log(1.0 / (1.0 - FSRS_W[20])) if FSRS_W[20] > 0
                    else math.pow(1 + days_since / (stability * FSRS_W[19]), 1 - FSRS_W[18]))


def schedule(stability, difficulty, rating):
    """Full FSRS schedule: current state + rating → new state + interval days."""
    if rating == 1:  # Again fails; Hard/Good/Easy are successful recalls.
        new_s = stability_after_failure(stability, difficulty, rating)
        new_d = next_difficulty(difficulty, rating)
    else:
        new_s = stability_after_success(stability, difficulty, rating)
        new_d = next_difficulty(difficulty, rating)

    interval = next_interval(new_s)
    return new_s, new_d, interval


def humanize_interval(days):
    """Anki-style short label: 1d, 12d, 3w, 1.5mo, 2y."""
    days = max(1, int(days))
    if days < 14:
        return f"{days}d"
    if days < 60:
        return f"{round(days / 7):g}w"
    if days < 365:
        return f"{round(days / 30.44, 1):g}mo"
    return f"{round(days / 365.25, 1):g}y"
