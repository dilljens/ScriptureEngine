"""Canonical FSRS-7 scheduling core, shared by every review surface.

Both the scripture-memorize scheduler (web/routes/memorize.py) and the
Hebrew scheduler (web/routes/hebrew.py) import these names — there is
exactly one implementation of the algorithm, verified element-wise
against the reference implementation (fsrs-rs v7.0.0 model_v7, via a
local differential harness dumping reference vectors).

FSRS-7 vs FSRS-6: dual stability (slow + fast). Recall is a weighted mix
of a fast-decaying and a slow-decaying power-law component, so same-day
reviews flow through the same next-state path (no separate short-term
branch). Intervals come from Newton iterations on the log timescale with
a bisection fallback.

Conventions (canonical FSRS-7):
- Rating 1 (Again) is the only lapse; 2/3/4 (Hard/Good/Easy) are
  successful recalls. Hard is NOT a failure.
- New cards use initial stability/difficulty/fast-stability
  (fast = 0.8 * slow, the upstream SM2-conversion ratio); reviews use
  the full (S, S_fast, D) state and fractional elapsed days.
- days_elapsed=None (unknown last review) behaves as a same-day review
  (delta_t = 0): no spurious inflation, matching upstream's nth==0 path.
- Intervals are float days; callers round and clamp (minimum 1 day is a
  route policy for graduated cards, not a core property — intraday steps
  schedule sub-day due times directly).

Route-specific layers stay in the routes and are documented as
extensions, not divergences:
- memorize: Math Academy learning-speed adjustment + preview-help
  weighting (effective rating). No per-card fast-stability column yet,
  so it uses the 0.8 default (upstream's own scalar convention).
- hebrew: per-node learning speed + persisted fast stability.
"""

import datetime
import math

# FSRS-7 default parameters (fsrs-rs inference_v7 DEFAULT_PARAMETERS).
FSRS_W = [0.1104, 2.2395, 3.9221, 11.7841, 6.1686, 0.6457, 3.6807, 1.9795,
          0.0, 1.3826, 0.7024, 0.5999, 0.8146, 0.6398, 1.0, 1.3207,
          0.6707, 3.8668, 0.4416, 0.0934, 1.8631, 0.6162, 1.0869, 0.1567,
          0.0801, 0.2421, 0.9464, 0.1433, 0.7145, 0.0, 0.5667, 0.3734,
          0.5333, 0.3048]
FSRS_VERSION = 7

STABILITY_MIN = 0.0001
STABILITY_MAX = 36500.0
DIFFICULTY_MIN = 1.0
DIFFICULTY_MAX = 10.0
DR_MIN = 0.0001
DR_MAX = 0.9999
MIN_T = 1.0 / 86400.0
_NEWTON_ITERS = 7
_BISECTION_ITERS = 50

# New-card fast stability ratio (upstream SM2-conversion + init convention).
FAST_RATIO = 0.8


def _clamp(x, lo, hi):
    return min(max(x, lo), hi)


def initial_stability(rating):
    """Initial slow stability (in days): S0(G) = W[G-1]."""
    rating = max(1, min(4, int(rating)))
    return max(FSRS_W[rating - 1], STABILITY_MIN)


def initial_fast_stability(rating):
    """Initial fast stability: 0.8 * S0 (upstream init convention)."""
    return _clamp(FAST_RATIO * initial_stability(rating), STABILITY_MIN, STABILITY_MAX)


def initial_difficulty(rating):
    """Initial difficulty: D0(G) = w4 − e^(w5·(G−1)) + 1, clamped [1, 10]."""
    rating = max(1, min(4, int(rating)))
    return _clamp(FSRS_W[4] - math.exp(FSRS_W[5] * (rating - 1)) + 1,
                  DIFFICULTY_MIN, DIFFICULTY_MAX)


def _fast_recall(w, t, s_fast):
    t = max(0.0, t)
    s_fast = _clamp(s_fast, STABILITY_MIN, STABILITY_MAX)
    decay1_mag = _clamp(w[23] * s_fast ** (w[33] - 0.3), 0.01, 0.95)
    decay1 = -decay1_mag
    factor1 = math.exp(min(math.log(w[25]) / decay1, 60.0)) - 1.0
    return (1.0 + factor1 * (t / s_fast)) ** decay1


def _forgetting_curve(w, t, s, s_fast, d):
    """Weighted fast+slow recall probability at elapsed days t."""
    t = max(0.0, t)
    s = max(s, STABILITY_MIN)
    s_fast = max(s_fast, STABILITY_MIN)
    d = _clamp(d, DIFFICULTY_MIN, DIFFICULTY_MAX)
    r1 = _fast_recall(w, t, s_fast)
    decay2 = -_clamp(w[24], 0.01, 0.95)
    factor2 = w[26] ** (1.0 / decay2) - 1.0
    d_timescale = math.exp((d - 5.0) * (w[32] - 0.3))
    r2 = (1.0 + factor2 * d_timescale * (t / s)) ** decay2
    weight1 = w[27] * s_fast ** (-w[29])
    weight2 = w[28] * s ** w[30] * math.exp((d - 5.0) * (w[31] - 0.5))
    retention = (weight1 * r1 + weight2 * r2) / (weight1 + weight2)
    return retention * (1.0 - 2e-5) + 1e-5


def retrievability(stability, days_since, s_fast=None, difficulty=5.0):
    """Recall probability R(t, S, S_fast, D); R(0) ≈ 1 by construction."""
    if stability is None or stability <= 0:
        return 0.0
    t = max(0.0, float(days_since or 0.0))
    sf = s_fast if s_fast else FAST_RATIO * max(stability, STABILITY_MIN)
    return _forgetting_curve(FSRS_W, t, stability, sf, difficulty)


def _set_math(w, last_s, last_d, r, rating, start):
    """One stability update (slow start=7, fast start=15)."""
    rating = _clamp(int(rating), 1, 4)
    hard = w[start + 6] if rating == 2 else 1.0
    easy = w[start + 7] if rating == 4 else 1.0
    new_s_fail = (w[start + 3]
                  * ((last_s + 1.0) ** w[start + 4] - 1.0)
                  * math.exp((1.0 - r) * w[start + 5]))
    pls = min(last_s, new_s_fail)
    sinc = ((math.exp(w[start] - 1.5)
             * (11.0 - last_d)
             * last_s ** (-w[start + 1])
             * (math.exp((1.0 - r) * w[start + 2]) - 1.0)
             * hard * easy)
            + 1.0)
    new_s_success = max(pls, last_s * sinc)
    out = new_s_success if rating > 1 else pls
    return _clamp(out, STABILITY_MIN, STABILITY_MAX)


def next_difficulty(difficulty, rating, r=1.0):
    """D update; lapse deltas scale with (R + 0.1). r defaults to 1.0
    (recall assumed) when the retrieval probability is unknown."""
    rating = _clamp(int(rating), 1, 4)
    delta_d = -FSRS_W[6] * (rating - 3)
    if rating == 1:
        delta_d = delta_d * (r + 0.1)
    damped = difficulty + (10.0 - difficulty) * delta_d / 9.0
    init = FSRS_W[4] - math.exp(FSRS_W[5] * 3) + 1.0  # D0(Easy)
    return _clamp(0.01 * init + 0.99 * damped, DIFFICULTY_MIN, DIFFICULTY_MAX)


def stability_after_success(stability, difficulty, retrievability_value, rating):
    """Slow-stability update for ratings 2-4 (canonical set branch)."""
    return _set_math(FSRS_W, stability, difficulty, retrievability_value,
                     max(2, rating), 7)


def stability_after_failure(stability, difficulty, retrievability_value):
    """Slow-stability update for rating 1 (canonical set branch)."""
    return _set_math(FSRS_W, stability, difficulty, retrievability_value, 1, 7)


def _curve_and_derivative(w, t, s, s_fast, d):
    t = max(0.0, t)
    s = max(s, STABILITY_MIN)
    s_fast = max(s_fast, STABILITY_MIN)
    d = _clamp(d, DIFFICULTY_MIN, DIFFICULTY_MAX)
    decay1_mag = _clamp(w[23] * s_fast ** (w[33] - 0.3), 0.01, 0.95)
    decay1 = -decay1_mag
    factor1 = math.exp(min(math.log(w[25]) / decay1, 60.0)) - 1.0
    b1 = 1.0 + factor1 * (t / s_fast)
    r1 = b1 ** decay1
    dr1 = decay1 * b1 ** (decay1 - 1.0) * factor1 / s_fast
    decay2 = -_clamp(w[24], 0.01, 0.95)
    factor2 = w[26] ** (1.0 / decay2) - 1.0
    d_timescale = math.exp((d - 5.0) * (w[32] - 0.3))
    b2 = 1.0 + factor2 * d_timescale * (t / s)
    r2 = b2 ** decay2
    dr2 = decay2 * b2 ** (decay2 - 1.0) * factor2 * d_timescale / s
    weight1 = w[27] * s_fast ** (-w[29])
    weight2 = w[28] * s ** w[30] * math.exp((d - 5.0) * (w[31] - 0.5))
    wsum = max(weight1 + weight2, 1e-9)
    retention = (weight1 * r1 + weight2 * r2) / wsum
    derivative = (weight1 * dr1 + weight2 * dr2) / wsum
    return retention * (1.0 - 2e-5) + 1e-5, derivative * (1.0 - 2e-5)


def _interval_bisection(w, s, s_fast, d, retention):
    retention = _clamp(retention, DR_MIN, DR_MAX)
    if retention >= DR_MAX:
        return 0.0
    low, high = 0.0, max(s, s_fast, 1.0)
    while _forgetting_curve(w, high, s, s_fast, d) > retention and high < STABILITY_MAX:
        high = min(high * 2.0, STABILITY_MAX)
    for _ in range(_BISECTION_ITERS):
        mid = (low + high) * 0.5
        if _forgetting_curve(w, mid, s, s_fast, d) > retention:
            low = mid
        else:
            high = mid
    return _clamp((low + high) * 0.5, 0.0, STABILITY_MAX)


def _interval_newton(w, s, s_fast, d, retention):
    retention = _clamp(retention, DR_MIN, DR_MAX)
    if retention >= DR_MAX:
        return 0.0
    s = _clamp(s, STABILITY_MIN, STABILITY_MAX)
    s_fast = _clamp(s_fast, STABILITY_MIN, STABILITY_MAX)
    d = _clamp(d, DIFFICULTY_MIN, DIFFICULTY_MAX)
    min_log_t, max_log_t = math.log(MIN_T), math.log(STABILITY_MAX)
    log_t = math.log(max(max(s, s_fast), MIN_T))
    for _ in range(_NEWTON_ITERS):
        log_t = _clamp(log_t, min_log_t, max_log_t)
        t = _clamp(math.exp(log_t), MIN_T, STABILITY_MAX)
        r, deriv = _curve_and_derivative(w, t, s, s_fast, d)
        df_du = min(deriv * t, -1e-12)
        step = (r - retention) / df_du
        log_t -= _clamp(step, -4.0, 4.0)
        if not math.isfinite(log_t):
            return _interval_bisection(w, s, s_fast, d, retention)
    ivl = _clamp(math.exp(log_t), 0.0, STABILITY_MAX)
    r = _forgetting_curve(w, ivl, s, s_fast, d)
    if math.isfinite(r) and abs(r - retention) <= 1e-3:
        return ivl
    return _interval_bisection(w, s, s_fast, d, retention)


def next_interval(stability, request_retention=0.9, maximum_interval=36500,
                  s_fast=None, difficulty=5.0):
    """Next interval in float days for the full (S, S_fast, D) state."""
    sf = s_fast if s_fast else FAST_RATIO * max(stability or 0.0, STABILITY_MIN)
    ivl = _interval_newton(FSRS_W, max(stability or 0.0, STABILITY_MIN),
                           sf, difficulty, request_retention)
    return min(max(ivl, 0.0), maximum_interval)


def next_state(stability, s_fast, difficulty, delta_t, rating,
               request_retention=0.9):
    """Full FSRS-7 step. Returns (new_s, new_d, new_s_fast, interval_days)."""
    rating = _clamp(int(rating), 1, 4)
    w = FSRS_W
    r = _forgetting_curve(w, delta_t, stability, s_fast, difficulty)
    new_s = _set_math(w, stability, difficulty, r, rating, 7)
    r_fast = _fast_recall(w, delta_t, s_fast)
    new_sf = _set_math(w, s_fast, difficulty, r_fast, rating, 15)
    if rating == 1:
        new_sf = min(new_sf, new_s * 0.8)
    new_d = next_difficulty(difficulty, rating, r)
    ivl = _interval_newton(w, new_s, new_sf, new_d, request_retention)
    return new_s, new_d, new_sf, ivl


def schedule(stability, difficulty, rating, days_elapsed=None,
             request_retention=0.9, s_fast=None):
    """Canonical step for existing memory (new cards use the initials).

    days_elapsed: fractional days since last review (None = unknown, treated
    as same-day: no spurious inflation, matching upstream's nth==0 path).
    s_fast: fast stability (None = 0.8 * slow, upstream's scalar convention).
    Returns (new_stability, new_difficulty, interval_days, new_fast_stability).
    """
    rating = max(1, min(4, int(rating)))
    s = max(stability or 0.0, STABILITY_MIN)
    sf = s_fast if s_fast else FAST_RATIO * s
    t = max(0.0, float(days_elapsed)) if days_elapsed is not None else 0.0
    new_s, new_d, new_sf, ivl = next_state(s, sf, difficulty or 5.0, t,
                                           rating, request_retention)
    return new_s, new_d, ivl, new_sf


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
    """Fractional elapsed days since a '%Y-%m-%d %H:%M:%S' (or date-only) stamp.

    Returns None when unparseable — callers treat that as same-day rather
    than guessing.
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
