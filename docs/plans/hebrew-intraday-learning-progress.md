# Progress: Intraday learning (Anki parity)

## Session 2026-11-22 — L1 + L2 + L3 DONE
- L1 DONE (`web/routes/hebrew.py`): `RELEARN_DELAY_MIN=10`, `LEARN_AHEAD_MIN=20`
  next to `LEECH_LAPSE_THRESHOLD`. Again on any card → stability via normal
  FSRS failure/short-term path, lapses +1, `due = now + 10min`
  (`adjusted_interval = 0`); Good/Hard/Easy byte-identical (≥1d). Review
  response carries `is_relearn` + `relearn_in_min`. Queue + `_due_mode_rows`
  + leech share the +20m learn-ahead window; due items gain `is_learning`
  (future-due within window); `learning_count` in queue response. Preview
  endpoint: Again → `{days: 0, label: "<10m"}`. Stats day-0 docstring updated
  (same-window definition).
- L2 DONE (frontend): `RatingButtons` renders `<10m` with zero changes
  (label-driven). LearnView strip: `🔴 N learning` counter. AnkiReview:
  after an Again submit, status line reads "Back in ~10 min — finish this
  set, then hit Review due to meet it again" (fixed decks don't re-deal, so
  the card resurfaces through Review due — stated in the message, not hidden).
  `relearnLabel()` pure helper + 3 vitest (Anki-style `<10m`/`<1h`).
- L3 DONE (sim): `scripts/simulate_hebrew_learner.py --intraday` (same-day
  retry at recall ~0.8 through the real short-term branch). Base: 22.7
  reviews/day, retention 0.88, 427/500 matured @ 10 new/day, 0.9. Intraday:
  151 retries, 25.1 reviews/day (+10%), retention 0.884 (+0.4pt). In-spec
  shape (+1–3 pts, +5–15%): the win is pedagogical (closes the feedback
  loop same-session), not scheduler efficiency.
- Tests: `tests/test_hebrew_intraday.py` 5 passed (Again window 9–11m,
  graduate ≥1d, learn-ahead flag, `<10m` preview, undo restores pre-relearn
  due); `test_review_intervals.py` contract updated for intraday Again
  (was asserting all ≥1d); 30 green across intraday+stats+undo+parse files;
  `vite build` ✓ 3.9s; 7 vitest green. Only fail in scope is the
  pre-existing unrelated `memorize_preview` jsh gap (fails on clean tree).
- Anki reference: `/tmp/anki-upstream` (AGPL, read-only reference).
- Open follow-ups: second learning step (1m→10m needs per-card step state —
  schema change, deliberately deferred); live-session re-deal of relearn
  cards inside AnkiReview (currently resurface via Review due); FSRS-7
  evaluation (upstream v7.0.0, 2026-11-10 — see plan notes, supersedes B4).

## Session 2026-11-22 (continued) — level gate + step 2 + live re-deal
- Level gate DONE (`_max_frontier_level`): L(n+1) frontier opens at
  practiced-average mastery ≥ 0.5 on L(n); never locks below the deepest
  touched level (legacy grandfathered — live default user keeps gate 5,
  fresh users start at 1). Query-time, no migration; applied to review-queue
  and grammar-focus frontiers. Tests: `test_hebrew_frontier_gate.py` 4 passed.
- Two-step machine DONE: `learn_step` column on review_state (0 = scheduled,
  1 = +1m, 2 = +10m) with migration + undo snapshot/restore; shared
  `_learn_step_after` keeps submit and Again-preview in sync (new-card Again
  → 1m, lapse → 10m, Good advances, Easy/2nd-Good graduates). Fixed the
  index-short-circuit migration trap: `ensure_hebrew_schema_once` now also
  checks evolving columns, not just indexes. Preview `<1m`/`<10m` follows
  the step; `relearn_in_min` is the real value. Tests updated + extended.
- Live re-deal DONE (`AnkiReview`): is_relearn responses re-insert a clone
  +3 cards later (`relearnInsertAt`, cap 2/card via ref counter) — the
  learn-ahead collapse, live in-session. Status line updated (no longer
  claims Review-due-only). Vitest: 3 new cases.
- Verification: 504 pytest green (1 skipped, 30 slow deselected; only
  excluded file is the pre-existing unrelated memorize_preview jsh gap),
  `vite build` ✓, 10 vitest green.
