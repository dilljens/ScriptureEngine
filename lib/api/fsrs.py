"""Canonical FSRS-6 scheduling core, shared by every review surface.

Both the scripture-memorize scheduler (web/routes/memorize.py) and the
Hebrew scheduler (web/routes/hebrew.py) import these names — there is
exactly one implementation of the algorithm, verified element-wise
against the reference implementation (py-fsrs 6.x / fsrs-rs model_v6).

Conventions (canonical FSRS-6):
- Rating 1 (Again) is the only lapse; 2/3/4 (Hard/Good/Easy) are
  successful recalls with stability multipliers. Hard is NOT a failure.
- New cards use initial stability/difficulty; same-day reviews of
  existing memory use the short-term branch; otherwise retrievability
  comes from the power forgetting curve at whole elapsed days.
- Intervals are whole days, minimum 1 (no fuzz here — display only).

Route-specific layers stay in the routes and are documented as
extensions, not divergences:
- memorize: Math Academy learning-speed adjustment + preview-help
  weighting (effective rating).
- hebrew: per-node learning speed on its own tables.
"""

import datetime
import math

FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
          1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014,
          1.8729, 0.5425, 0.0912, 0.0658, 0.1542]

STABILITY_MIN = 0.001
MAX_INTERVAL = 36500


def initial_stability(rating):
    """Initial stability (in days): S0(G) = W[G-1]."""
    rating = max(1, min(4, int(rating)))
    return max(FSRS_W[rating - 1], STABILITY_MIN)


def initial_difficulty(rating):
    """Initial difficulty: D0(G) = w4 − e^(w5·(G−1)) + 1, clamped [1, 10]."""
    rating = max(1, min(4, int(rating)))
    return min(max(FSRS_W[4] - math.exp(FSRS_W[5] * (rating - 1)) + 1, 1.0), 10.0)


def retrievability(stability, days_since):
    """Power forgetting curve R(t, S); R(S) == 0.9 by construction."""
    if stability is None or stability <= 0:
        return 0.0
    days_since = max(0.0, float(days_since or 0.0))
    decay = -FSRS_W[20]
    factor = 0.9 ** (1.0 / decay) - 1
    return (1 + factor * days_since / stability) ** -FSRS_W[20]


def next_interval(stability, request_retention=0.9, maximum_interval=36500):
    """Next review interval in whole days for stability S at retention R."""
    decay = -FSRS_W[20]
    factor = 0.9 ** (1.0 / decay) - 1
    ivl = round(stability / factor * (request_retention ** (1.0 / decay) - 1))
    return min(max(ivl, 1), maximum_interval)


def stability_after_success(stability, difficulty, retrievability_value, rating):
    """Successful recall (ratings 2-4): linear (11−D) difficulty factor,
    exponential retrievability gating, Hard/Easy multipliers."""
    rating = max(2, min(4, int(rating)))
    hard = FSRS_W[15] if rating == 2 else 1
    easy = FSRS_W[16] if rating == 4 else 1
    return stability * (
        1
        + math.exp(FSRS_W[8])
        * (11 - difficulty)
        * (stability ** -FSRS_W[9])
        * (math.exp((1 - retrievability_value) * FSRS_W[10]) - 1)
        * hard
        * easy
    )


def stability_after_failure(stability, difficulty, retrievability_value):
    """Lapse (rating 1): capped at the short-term ceiling."""
    long_term = (
        FSRS_W[11]
        * (difficulty ** -FSRS_W[12])
        * (((stability + 1) ** FSRS_W[13]) - 1)
        * math.exp((1 - retrievability_value) * FSRS_W[14])
    )
    short_cap = stability / math.exp(FSRS_W[17] * FSRS_W[18])
    return min(long_term, short_cap)


def short_term_stability(stability, rating):
    """Same-day review of existing memory (FSRS-5/6 short-term branch).
    Floored at no-change for Hard/Good/Easy; Again may decrease."""
    rating = max(1, min(4, int(rating)))
    inc = math.exp(FSRS_W[17] * (rating - 3 + FSRS_W[18])) * (stability ** -FSRS_W[19])
    if rating in (2, 3, 4):
        inc = max(inc, 1.0)
    return max(stability * inc, STABILITY_MIN)


def next_difficulty(difficulty, rating):
    """Linear damping toward (10−D)/9 with mean reversion to D0(4)."""
    rating = max(1, min(4, int(rating)))
    delta = -(FSRS_W[6] * (rating - 3))
    damped = difficulty + (10.0 - difficulty) * delta / 9.0
    arg_1 = FSRS_W[4] - math.exp(FSRS_W[5] * 3) + 1  # D0(Easy)
    reverted = FSRS_W[7] * arg_1 + (1 - FSRS_W[7]) * damped
    return min(max(reverted, 1.0), 10.0)


def schedule(stability, difficulty, rating, days_elapsed=None):
    """Full FSRS-6 step for EXISTING memory (new cards use the initials).

    days_elapsed: whole days since last review (None = assume at-design
    retention 0.9). Same-day re-reviews take the short-term branch.
    Returns (new_stability, new_difficulty, interval_days).
    """
    rating = max(1, min(4, int(rating)))
    if days_elapsed is not None and days_elapsed < 1:
        new_s = short_term_stability(stability, rating)
        new_d = next_difficulty(difficulty, rating)
    else:
        r = retrievability(stability, days_elapsed) if days_elapsed else 0.9
        if rating == 1:
            new_s = stability_after_failure(stability, difficulty, r)
        else:
            new_s = stability_after_success(stability, difficulty, r, rating)
        new_d = next_difficulty(difficulty, rating)
    new_s = max(new_s, STABILITY_MIN)
    return new_s, new_d, next_interval(new_s)


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


def days_since(timestamp_str, now=None):
    """Whole elapsed days since a '%Y-%m-%d %H:%M:%S' (or date-only) stamp.

    Returns None when unparseable — callers treat that as 'assume design
    retention' rather than guessing.
    """
    if not timestamp_str:
        return None
    try:
        if isinstance(timestamp_str, (datetime.datetime, datetime.date)):
            past = timestamp_str
        else:
            s = str(timestamp_str).strip()
            fmt = "%Y-%m-%d %H:%M:%S" if len(s) > 10 else "%Y-%m-%d"
            past = datetime.datetime.strptime(s, fmt)
        now = now or datetime.datetime.now()
        return max(0.0, (now - past).total_seconds() / 86400.0)
    except (ValueError, TypeError, OverflowError):
        return None
