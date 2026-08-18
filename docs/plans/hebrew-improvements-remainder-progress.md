---
status: completed
kind: progress
area: hebrew-learning
plan: hebrew-improvements-remainder
created: 2026-08-05
completed: 2026-08-15
---

# Hebrew Improvements Remainder — Progress Log

## Session started (2026-08-05)

Resuming the plan. Prior agent left only `scripts/seed_hebrew_confusability.py`
(Track B, unverified). Tracks remaining: B (confusability), C (learning speeds),
A (3-KP micro-scaffolding), D (rollup).

### Initial findings (audit before code)

- **Table name discrepancy**: plan doc says `hebrew_nility`; the real table in
  `data/memorize.db` and read by `web/routes/hebrew.py` (curriculum reorder +
  review-queue non-interference + quiz distractors) is **`hebrew_confusability`**
  with columns `node_a, node_b, reason, strength`. `hebrew_nility` is a typo in
  the plan. The seed script already targets `hebrew_confusability` (correct).
- **Real DB path**: `data/memorize.db` (7.4 MB, populated). `data/processed/memorize.db`
  is a 0-byte stub. Convention (hebrew.py:174, lib/config.py): default
  `data/memorize.db`, overridable via `MEMORIZE_DB_PATH`. The seed script
  hardcodes `data/memorize.db` and ignores the env override — needs fixing.
- **Production DB already has 28 confusability rows** (all 6 letter pairs +
  finals + vowels + grammar). A prior seed run populated it. Script is not
  idempotent-safe (DELETE-all-then-insert; no UNIQUE(node_a,node_b)).
- **Node ids in the seed list**: 44/46 exist. Missing: `perfect_3ms`,
  `imperfect_3ms` (script correctly skips them — keep that).
- **Practice item types** (hebrew_practice_items.question_type): classification,
  multiple_choice, recall, contrast, transliteration, typing, cloze. All covered
  by a recognition/recall/production stage map. No `sentence`/`true_false`
  rows in data, but map handles them.
- **Phase 7 learning-speed model** (audit result, see Track C): already ~80%
  shipped in `web/routes/hebrew.py` — ability/difficulty helpers,
  `compute_learning_speed`, interval modulation in `process_hebrew_review`,
  and the `learning_speed < 0.5 → no FIRe` gate. Gaps: no per-user per-topic
  (category-level) accuracy rollup (ability is a single global scalar), and
  caps are [0.2, 5.0] not the plan's [0.25, 4.0].

## Track B — Confusability ✅ (done)

- **Seed script fixed + verified** (`scripts/seed_hebrew_confusability.py`):
  - Now honors `MEMORIZE_DB_PATH` env var (then argv[1], then default
    `data/memorize.db`) — matches hebrew.py:174 / lib/config.py convention.
  - Idempotent: added `UNIQUE(node_a,node_b)` index + `INSERT OR IGNORE`;
    removed the destructive DELETE-all. Re-runs insert 0, never duplicate,
    never clobber manually-added pairs.
  - Still skips missing nodes (`perfect_3ms`/`imperfect_3ms`) with a notice.
  - Verified against temp DBs: fresh insert = 28 pairs (29 defined, 1 skipped);
    re-run = 0; env override works.
- **Non-interference made unit-testable**: extracted the review-queue
  round-robin interleave into a pure `_interleave_due_items(by_cat,
  confusable_pairs)` in `web/routes/hebrew.py`; endpoint now calls it. The
  ≥3-item-spacing contract is now directly testable without a DB. (Note: the
  extraction drains the full pool — the old loop bounded at `len(due)`, which
  could silently drop merged-in new cards. The returned `interleaved[:limit]`
  ordering is identical; the change only lets new cards surface when the queue
  is under `limit` — a latent-bug fix.)
- **Tests** (`tests/test_hebrew_confusability.py`, 8 tests):
  - seed inserts all six letter pairs + idempotency + env override + missing-node skip
  - `_interleave_due_items` keeps a confusable pair ≥3 items apart (pure)
  - review-queue endpoint separates shin/sin when both due (integration,
    isolated DB), plus confusability_warning surfacing
- Checkpoint `pytest tests/ -k hebrew`: **62 passed** (54 baseline + 8 new).

## Track C — Per-Topic Learning Speeds ✅ (done)

### Audit finding (Phase 7 model)
Most of Phase 7 was **already shipped** in `web/routes/hebrew.py`:
- ability/difficulty helpers: `_get_all_user_accuracy`, `_get_topic_difficulty` ✅
- `learning_speed = ability / difficulty` (`compute_learning_speed`) ✅
- interval modulation in `process_hebrew_review` (`adjusted_interval = interval × learning_speed`) ✅
- `learning_speed < 0.5 → no FIRe credit` gate ✅

**Genuinely missing** (implemented here):
1. **Per-user per-topic accuracy rollup** — ability was a single global scalar.
   Added `_get_user_category_accuracy(user_id)` aggregating hebrew_progress
   attempts/correct up to the node category; `compute_learning_speed` now uses
   per-category ability (falling back to overall) so a learner's speed differs
   between alphabet vs verbs.
2. **Caps** — interval multiplier was clamped to [0.2, 5.0]; now the plan's
   [0.25×, 4×] via `LEARNING_SPEED_MIN/MAX` + `clamp_learning_speed`, applied
   in `process_hebrew_review`.

**Direction note (decision):** the parent plan writes `interval *= 1/learning_speed`,
but the shipped/coherent semantic here is `interval *= learning_speed` ("higher
speed → longer intervals", documented in the learning-speeds endpoint docstring
and the review docstring). Flipping it would regress all existing users, so I
kept the shipped direction and implemented the missing rollup + caps. Flagged
for the plan author in the rollup.

### Code
- `web/routes/hebrew.py`: `LEARNING_SPEED_MIN/MAX`, `clamp_learning_speed`,
  `_get_user_category_accuracy`, per-topic ability in `compute_learning_speed`,
  caps applied in `process_hebrew_review`.

### Tests (`tests/test_hebrew_learning_speed.py`, 10 tests)
- category accuracy rollup (consonant 1.0 / verb 0.0 / vowel 0.25)
- per-topic ability drives different speeds for hi-vs-lo users on same topic
- `clamp_learning_speed` exact caps (10→4.0, 0→0.25, 1.5→1.5)
- caps respected in review intervals (both users within [0.25,4]× base)
- **two users on the same topic get different intervals** (hi > lo) — the plan
  checkpoint
- slow user (<0.5 speed) gets floor interval + no FIRe credit
- fsrs/review endpoint returns learning_speed/user_ability for 4 node types
- Checkpoint `pytest tests/ -k hebrew`: **72 passed** (62 + 10 new);
  `test_openapi_snapshot` still green (no new endpoints added).

## Track A — 3-KP Micro-Scaffolding ✅ (done)

### A1 audit: practice item types
`hebrew_practice_items.question_type` already has a reliable type column (7
values in data: multiple_choice, classification, recall, contrast,
transliteration, cloze, typing). No schema change needed — classification is
driven by the type column per the pre-resolved decision.

### A1 code (`web/routes/hebrew.py`)
- Stage map constants: `KP_STAGE_RECOGNITION = {multiple_choice, true_false,
  letter_recognition, classification}`, `KP_STAGE_RECALL = {cloze,
  transliteration, contrast, recall}`, `KP_STAGE_PRODUCTION = {typing,
  sentence}`; `practice_stage(qtype)` and `build_kp_stages(practice_items)`
  (pure, deterministic: stage order recognition→recall→production, items sorted
  by (difficulty, id), empty stages omitted).
- `get_hebrew_lesson` now annotates every practice item with `kp_stage` and
  returns a `kp_stages` array in the payload. Lessons with only MC items
  return only the recognition stage → KP2/KP3 skip, never block.
- No new endpoint added → OpenAPI snapshot unchanged.

### A2 code (`frontend/src/components/HebrewLessonView.jsx`)
- New `StagedPractice` component: per-stage worked example (the existing
  explanation/key_points/worked_examples blocks render above and stay visible)
  → up to 2 practice items per attempt → strict pass gate (all correct) →
  next stage; a failed stage shows a "Review this stage" panel and retries
  with a fresh item pair (cycles the stage pool). Completion screen after all
  stages pass.
- Reuses the existing `DrillCardRenderer`/`CardRenderer` for item UI and
  `gradePracticeAnswer` for objective grading; graded answers post to
  `/api/v1/hebrew/progress` (same SRS feed as the flashcard flow).
- **Quick mode preserved**: existing CardQueue flow untouched; header toggle
  (📚 Staged / ⚡ Quick); learner choice persists in `localStorage`
  (`hebrew.practiceMode`). Default = staged when the lesson has stages.
- `vite build` ✅ clean.

### A3 tests (`tests/test_hebrew_stage_map.py`, 16 tests)
- type→stage classification for all 10 mapped types (parametrized)
- unknown type → None (never mis-classified)
- deterministic grouping + difficulty/id sort; every item annotated with
  `kp_stage`
- only-MC lesson → only recognition stage (KP2/KP3 skip); empty/unknown →
  no stages, no crash
- lesson payload integration: `shin` and `bet` expose 3-stage kp_stages with
  sorted items and annotated practice_items
- Checkpoint `pytest tests/ -k hebrew`: **88 passed** (72 + 16 new).

## Track D — Rollup ✅ (done)

- Plan file `hebrew-improvements-remainder.md`: all track/phase checkboxes `[x]`,
  `status: completed` in frontmatter, implementation-notes section added
  (hebrew_nility→hebrew_confusability naming; Phase 7 interval-direction decision;
  live DB untouched).
- Parent plan `hebrew-learning-improvements.md`: Phases 4/6/7 marked shipped
  with superseded-by pointers; Phase 5 confirmed shipped; completion-status
  block added.

## Final checkpoints (all recorded)

- `python3 -m pytest tests/ -k hebrew -q` → **88 passed, 261 deselected**
  (baseline was 54; +34 new tests across confusability 8, learning-speed 10,
  stage-map 16).
- `tests/test_openapi_snapshot.py` → pass (no new endpoints added).
- `vite build` (frontend/node_modules present) → **clean build** (8.8s),
  `HebrewLessonView` bundle rebuilt.
- Seed script verified against temp DBs (`/tmp/opencode/*.db`): fresh insert 28,
  re-run 0 (idempotent), `MEMORIZE_DB_PATH` override works.
- Live DB untouched: all tests use the isolated temp-DB fixture
  (`tests/conftest.py` `client`); the seed script ran only on temp copies.

## Net line delta

- Modified (tracked): `web/routes/hebrew.py`, `frontend/.../HebrewLessonView.jsx`,
  `scripts/seed_hebrew_confusability.py`, `docs/plans/hebrew-learning-improvements.md`
  → **+553 / −115** (net **+438**).
- New: 3 test files (**459** lines: 209 + 148 + 102) + progress log (**153**)
  + remainder plan doc (**158**).
- Grand total ≈ **+1208 / −115** (net **+1093**).

## Open items / notes for the plan author

1. **`hebrew_nility` vs `hebrew_confusability`**: plan doc typo; the real table
   name is `hebrew_confusability`. Seed script + code agree.
2. **Phase 7 interval direction**: kept the shipped `interval *= learning_speed`
   ("faster → longer intervals") instead of the parent doc's `1/learning_speed`
   to avoid regressing existing users; the missing rollup + caps were added.
3. **New-card mixing**: the review-queue "new cards" budget can inject fresh
   cards between confusable reviews — this only *increases* separation and is
   consistent with Anki-style mixed review.
4. **Frontend staged default**: `hebrew.practiceMode` defaults to `staged` for
   lessons with stages, but persists the learner's choice in localStorage, so a
   quick-mode learner stays in quick mode across sessions.
