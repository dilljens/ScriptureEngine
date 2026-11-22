---
status: proposed
kind: plan
area: hebrew-learning
author: opencode
created: 2026-11-22
---

# Intraday learning steps (Anki parity: relearn + learn-ahead)

Successor to `hebrew-packs-and-srs-parity.md` (Tracks B/C complete except
deferred B4). Closes the one structural gap the Anki reference exposed:
**Again currently means "tomorrow"** (`max(1, …)` day clamp in
`process_hebrew_review`), where Anki means **"in ~10 minutes"** with a
20-minute learn-ahead window. Without intraday steps, a miss can't be
re-asked the same session — the learning-review doc's gap #2 (no re-ask of
missed items) stays open by construction.

## Anki reference (read, not copied — AGPL)

UpstreamVII cloned to `/tmp/anki-upstream` (`github.com/ankitects/anki`,
GNU AGPL v3; reference only, nothing vendored):

| Behavior | Anki source |
|---|---|
| Review loop auto-presents next card from new/learn/review queues | `rslib/src/scheduler/queue/builder/` |
| Answer buttons show next interval (`<10m`, `1d`, …) | `answering/mod.rs` + `timespan.rs:answer_button_time_collapsible` |
| Learning steps (default new `1m → 10m`), relearn `10m` | `states/steps.rs` (tests assert `[1.0, 10.0]`), `states/learning.rs`, `states/relearning.rs` |
| Learn-ahead: intraday cards due within ~20m stay in the red counter and keep the session going | `queue/learning.rs:current_learn_ahead_cutoff()` |
| FSRS workload/retention simulator | `fsrs/simulator.rs:simulate_review/simulate_workload` |
| Per-card undo | `queue/undo.rs` (same shape as our B2) |

Our equivalents already shipped: queue + interleaving, interval preview on
rating buttons, FSRS-6 core, single-step undo, suspend. Missing: sub-day
`due`, the learn-ahead window, `<10m`-style preview labels.

## Requirements

- [ ] R1: Again (rating 1) on any card reschedules **due = now + 10 min**
      (single relearn step = Anki's relearn default); stability/difficulty
      still update through the normal FSRS short-term path; lapses +1.
- [ ] R2: Review queue serves rows due within **now + 20 min** (learn-ahead),
      flagged `is_learning: true`, sorted first by due time. Day-0 forecast
      stays consistent (forecast counts scheduled rows; document that day-0
      now includes the learn-ahead window).
- [ ] R3: Interval preview renders sub-day as `<10m` / `<1m` (Anki's
      collapsible time format); Again button shows when the card returns.
- [ ] R4: Good/Hard/Easy paths byte-identical to today (due ≥ 1d). No new
      tables; no schema migration (learn state is inferred: `last_rating == 1`
      and `due <= now + 20m`). Undo/suspend/stats interplay unchanged
      (snapshots already capture `due`; suspended rows already filtered).
- [ ] R5: Every phase green: related pytest, `vite build`, related vitest,
      zero new warnings.

## Pre-resolved decisions

- **Single 10m step, not 1m→10m.** Anki's default learning steps are two
  (`1m 10m`); v1 ships one relearn step (`10m`, = Anki's relearn default).
  Rationale: two steps need per-card step state (schema change); one step
  needs none (inference rule in R4). Second step is a documented follow-up.
- **No configurable steps UI in v1.** Fixed constants (`RELEARN_DELAY_MIN=10`,
  `LEARN_AHEAD_MIN=20`) next to `LEECH_LAPSE_THRESHOLD`. Deck-options UI
  only if learners ask.
- **No day-boundary special-casing.** Existing `localtime` due comparisons
  stand; a 23:55 Again due 00:05 shows in tomorrow's queue — correct.
- **Sim-gated.** L3 re-runs `scripts/simulate_hebrew_learner.py` extended
  with intraday re-review; expected: retention lift at small workload cost.
  If the sim shows workload explosion, cap learn-ahead before shipping.

## Track L: Intraday learning `[ ]`

### Phase L1: Scheduler + queue `[ ]`

- `process_hebrew_review`: rating 1 → `due = now + 10min` (stability via
  normal short-term update, lapses +1). Ratings 2–4 untouched.
- `get_hebrew_review_queue`: learn-ahead window (`due <= now + 20m`
  included, `is_learning` flag, learning-first sort by due). Legacy-estimate
  and new-card paths unchanged.
- Forecast/stats: day-0 definition extended (document in endpoint docstring);
  `suspended_count`/`leech_due` semantics unchanged.
- 📏 ~2 files, ~80-120 lines
- ✅ Checkpoint: pytest — Again → due within 9–11 min; Good after Again →
  due ≥ 1d; queue contains learn-ahead row with `is_learning: true`;
  stats day-0 == direct count under the same window.

### Phase L2: Preview + UI `[ ]`

- Intervals endpoint + `RatingButtons`: sub-day labels (`<10m`, `<1m`).
- LearnView queue strip: red learning counter (`🔴 N learning` next to due/new).
- AnkiReview: after rating Again, toast/line states the return time
  ("Back in ~10 min — keep going, it'll resurface this session").
- 📏 ~2-3 files, ~80-120 lines
- ✅ Checkpoint: `vite build` + vitest for the time-format helper; manual:
  Again a card → red counter increments → card resurfaces.

### Phase L3: Sim + verify `[ ]`

- Extend `scripts/simulate_hebrew_learner.py` with `--intraday` (Again cards
  re-reviewed same simulated day at recall = R(post-lapse stability)).
- Expect: retention +1–3 pts, workload +5–15% (Anki-simulator-shaped claim,
  verified not asserted).
- Full suite green; update this plan + card-rules (learning-step rule).
- 📏 ~1 file, ~60-100 lines
- ✅ Checkpoint: sim prints both regimes; numbers in the progress log.

## Anti-scope

- No per-deck configurable steps, no load balancer/fuzz (Anki has both;
  ours stays deterministic), no second scheduler, no push/PWA (still needs
  permission/privacy review per P2-B), no FSRS optimizer (still B4-deferred).
