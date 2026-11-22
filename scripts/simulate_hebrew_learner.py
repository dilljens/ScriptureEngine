#!/usr/bin/env python3
"""Simulate a bot learner on the real FSRS core (Anki-simulator style).

Mirrors Anki's `fsrs/simulator.rs` approach (simulate_review/simulate_workload):
each day the bot takes its due queue + N new cards, recalls each card with
probability = our own retrievability() plus per-card latent difficulty and
noise, rates Good (3) on recall / Again (1) on lapse, and reschedules through
lib.api.fsrs. Reports workload, retention, stability growth, backlog.

Usage:
    python3 scripts/simulate_hebrew_learner.py [--days 60] [--new-per-day 10]
        [--retention 0.9] [--cards 500] [--seed 7]
"""

import argparse
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.api.fsrs import (
    initial_difficulty,
    initial_stability,
    next_interval,
    retrievability,
    schedule,
)


def simulate(days=60, new_per_day=10, retention=0.9, cards=500, seed=7):
    rng = random.Random(seed)
    # Latent difficulty per card: 0.7 (easy) .. 1.3 (hard) multiplier on decay.
    latent = {i: rng.uniform(0.7, 1.3) for i in range(cards)}
    state = {}  # card -> (stability, difficulty, due_day, reps, lapses, last_day)
    introduced = 0
    reviews_per_day, retention_per_day, backlog = [], [], []
    lapses_total = recalls_total = 0

    for day in range(days):
        # Introduce new cards.
        for _ in range(new_per_day):
            if introduced >= cards:
                break
            state[introduced] = (None, None, day, 0, 0, day)
            introduced += 1
        # Due queue (Anki-style: everything due today, no cap here — we
        # measure the natural workload so caps can be sized from data).
        due = [c for c, s in state.items() if s[2] <= day]
        backlog.append(len(due))
        day_recalls = day_reviews = 0
        for c in due:
            stab, diff, _, reps, lapses, last = state[c]
            if stab is None:
                rating = 3  # first sight: guided lesson, assume pass
                new_s = initial_stability(rating)
                new_d = initial_difficulty(rating)
                ivl = next_interval(new_s, retention)
            else:
                days_elapsed = max(1, day - last)
                # True recall prob: retrievability warped by latent difficulty.
                r = retrievability(max(stab, 0.25) / latent[c], days_elapsed)
                recall = rng.random() < r
                rating = 3 if recall else 1
                day_reviews += 1
                day_recalls += 1 if recall else 0
                if recall:
                    recalls_total += 1
                else:
                    lapses_total += 1
                new_s, new_d, ivl = schedule(
                    max(stab, 0.25), diff, rating, max(days_elapsed, 1), retention)
            state[c] = (new_s, new_d, day + max(1, round(ivl)), reps + 1,
                        lapses + (1 if stab is not None and rating == 1 else 0), day)
        reviews_per_day.append(day_reviews)
        retention_per_day.append(day_recalls / day_reviews if day_reviews else 1.0)

    matured = sum(1 for s in state.values()
                  if s[0] is not None and s[0] >= 21.0)
    return {
        "days": days, "introduced": introduced,
        "avg_reviews_day_last_2w": round(sum(reviews_per_day[-14:]) / 14, 1),
        "max_reviews_day": max(reviews_per_day),
        "retention_last_2w": round(sum(retention_per_day[-14:]) / 14, 3),
        "overall_retention": round(recalls_total / max(recalls_total + lapses_total, 1), 3),
        "backlog_final": backlog[-1],
        "matured_21d_stability": matured,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--new-per-day", type=int, default=10)
    ap.add_argument("--retention", type=float, default=0.9)
    ap.add_argument("--cards", type=int, default=500)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    r = simulate(args.days, args.new_per_day, args.retention, args.cards, args.seed)
    print(f"days={r['days']} introduced={r['introduced']}")
    print(f"avg reviews/day (last 2w): {r['avg_reviews_day_last_2w']}")
    print(f"max reviews/day: {r['max_reviews_day']}")
    print(f"retention (last 2w): {r['retention_last_2w']}  overall: {r['overall_retention']}")
    print(f"final backlog: {r['backlog_final']}  matured (S>=21d): {r['matured_21d_stability']}")
    # Sanity bounds for a healthy scheduler at 90% desired retention.
    ok = (0.75 <= r["retention_last_2w"] <= 0.98
          and r["avg_reviews_day_last_2w"] < 300
          and r["matured_21d_stability"] > 0)
    print("SIM", "PASS" if ok else "REVIEW")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
