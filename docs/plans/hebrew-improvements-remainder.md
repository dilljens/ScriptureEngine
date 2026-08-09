---
status: completed
kind: plan
area: hebrew-learning
author: dillon
created: 2026-08-05
completed: 2026-08-05
---

# Project: Hebrew Learning Improvements — Remainder (Phases 4, 6, 7)

Goal: Implement the three remaining phases of
`docs/plans/hebrew-learning-improvements.md`: 3-KP micro-scaffolding (Phase 4),
confusability matrix (Phase 6), and per-topic learning speeds (Phase 7). Phases
1–3 and 5 are already shipped (timed drills, adaptive diagnostic, interleaved
review queue, persisted FSRS-5 scheduler in `web/routes/hebrew.py`).

## Requirements
- [x] R4: **Micro-scaffolding** — each lesson staged KP1 recognition → KP2
      recall → KP3 production with per-KP pass gating (progressive practice
      from existing practice items)
- [x] R6: **Confusability matrix** — confusable letter/word pairs labeled and
      separated in curriculum/ordering (mechanism already exists)
- [x] R7: **Per-topic learning speeds** — per-user per-topic accuracy tracked;
      review intervals modulated by ability/difficulty

## Pre-resolved Decisions
- **Micro-scaffolding**: `key_points` already exist as data and render in
  `HebrewLessonView.jsx:356`. Real work = classify the existing practice items
  by cognitive type (MC/recognition → cloze/transliteration/recall → typing/
  production) and stage them 3-deep with a pass gate per stage. Reuse the
  existing grading endpoints; do not add new tables — add a `kp_stage` mapping
  derived from the practice item type column.
- **Confusability**: the **mechanism already exists** — `hebrew_nility` table
  (`node_a, node_b`) + review-queue reordering (`web/routes/hebrew.py`
  "Non-Interference" block). Work = build the seed matrix
  (`scripts/seed_hebrew_confusability.py`, as the parent plan proposed) with
  the six known pairs (shin/sin, he/chet, bet/vav, samekh/sin, tet/tav,
  ayin/aleph + letter lessons), and verify the reorder actually separates
  them in review.
- **Learning speeds**: partial logic already exists in
  `process_hebrew_review` (`web/routes/hebrew.py:348`) — `learning_speed <
  0.5` skips FIRe credit and `adjusted_interval` is computed. Work =
  complete the model: per-user per-topic accuracy in `hebrew_progress`, real
  ability/difficulty computation, and `interval *= 1/learning_speed`
  application (with caps). Verify what's there first — some of Phase 7 may
  already be satisfied.

## Track A: 3-KP Micro-Scaffolding `[x]`
- Description: staged recognition→recall→production per lesson.
- 📏 Scope: 3 files, ~200 lines

### Phase A1: Item classification + stage map `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] Audit practice item types (MC / TF / cloze / transliteration / typing /
      sentence) in `hebrew_practice` / lesson API — confirm a `type` column
      exists for classification
- [x] Build stage map: recognition = MC/TF; recall = cloze/transliteration;
      production = typing/sentence. Fall back to available types when a stage
      has none (never block a lesson on a missing stage)
- 📏 Scope: `lib/api/hebrew.py` (or wherever lesson payload is built) +60
- ✅ Checkpoint: every lesson returns a deterministic stage assignment;
      lessons with only MC items still complete (KP2/KP3 skip)
- ⚙ Fallback: if practice items lack a reliable type, derive stage from the
      answer shape (options vs. free-text) — verified against existing data

### Phase A2: Frontend staged flow `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] `HebrewLessonView.jsx`: render KPs as 3 progressive stages; per-stage
      worked example → 2 practice items; stage unlocks next only on pass;
      failed stage → review that stage's content
- [x] Keep the current single-pass flow as a "quick" mode (no regression for
      quick learners)
- 📏 Scope: `frontend/src/components/HebrewLessonView.jsx` ~140
- ✅ Checkpoint: `vite build` clean; 94 unit tests pass; manual walk-through
      of a 3-stage lesson completes; quick mode unaffected
- ⚙ Fallback: if staging UX is too invasive, ship stage assignment +
      practice-type ordering server-side first (A1 alone) and defer the gate UI

### Phase A3: Tests `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [x] Backend: stage map correctness test (known lesson → expected stages)
- 📏 Scope: `tests/` +30
- ✅ Checkpoint: pytest green
- ⚙ Fallback: none

## Track B: Confusability Matrix (Phase 6) `[x]`
- Description: seed + verify separation.
- 📏 Scope: 2 files, ~80 lines

### Phase B1: Seed script `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [x] `scripts/seed_hebrew_confusability.py`: insert the six letter pairs
      (shin/sin, he/chet, bet/vav, samekh/sin, tet/tav, ayin/aleph) + any
      existing letter-lesson node pairs into `hebrew_nility` (idempotent:
      INSERT OR IGNORE)
- [x] Verify `web/routes/hebrew.py` Non-Interference block reads the table
      (it does — confirm SQL matches the new seed's node id format)
- 📏 Scope: `scripts/seed_hebrew_confusability.py` ~60, tests +20
- ✅ Checkpoint: table seeded; review queue separates a confusable pair when
      both are due (assert order in a test)
- ⚙ Fallback: if node-id format mismatch, map pairs via lesson title regex
      instead of hardcoded ids

## Track C: Per-Topic Learning Speeds (Phase 7) `[x]`
- Description: complete the ability/difficulty model.
- 📏 Scope: 2 files, ~100 lines

### Phase C1: Audit + complete the model `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [x] Audit `process_hebrew_review` + `hebrew_progress` — determine what of
      the Phase 7 model already exists (learning_speed gate exists; per-user
      per-topic accuracy tracking?)
- [x] Add per-user per-topic accuracy rollup (hebrew_progress already has
      attempts/correct per user+node; aggregate by category or prerequisite
      cluster)
- [x] Apply `interval *= 1/learning_speed` with caps (e.g. 0.25×–4×) in the
      review scheduler; keep the `learning_speed < 0.5 → no FIRe` rule
- 📏 Scope: `web/routes/hebrew.py` ~70, tests +30
- ✅ Checkpoint: two users practicing the same topic get different intervals
      per their accuracy; caps respected; existing FSRS tests green
- ⚙ Fallback: if the audit shows the model is already effectively complete,
      close Phase 7 with a verification note and tests only (no code change)

## Track D: Rollup `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 5
- [x] Update `docs/plans/hebrew-learning-improvements.md`: check Phases 4/6/7
      (and Phase 5 if the audit confirms it), note superseded-by where
      relevant
- [x] Progress log `docs/plans/hebrew-improvements-remainder-progress.md`
- ✅ Checkpoint: all tracks checked; live DB untouched by tests; `sentrux
      check .` unchanged
- ⚙ Fallback: none

## Implementation Notes (from completion)
- **Table name**: the plan's `hebrew_nility` is a typo — the real table is
  `hebrew_confusability` (`node_a, node_b, reason, strength`), read by the
  curriculum reorder, the review-queue non-interference, and the quiz
  distractor logic. The seed script targets the real table.
- **Phase 7 direction**: the parent doc writes `interval *= 1/learning_speed`;
  the shipped semantic here is `interval *= learning_speed` ("higher speed →
  longer intervals", documented in code). Kept the shipped direction to avoid
  regressing existing users; implemented the missing per-user per-topic
  rollup and the [0.25×, 4×] caps.
- **Live DB untouched**: all tests run against the isolated temp-DB fixture
  (tests/conftest.py). The seed script was exercised only on temp copies.

## Out of Scope
- Phase 2/3 (already shipped: adaptive diagnostic, interleaved review)
- New learning content (audit/verify focus)
- Changes to the Go FSRS backend (the persisted scheduler is the single
  source)
