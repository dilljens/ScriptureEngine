---
status: active
kind: plan
area: hebrew-tutor/memorization/provider/truth
author: opencode
created: 2026-08-24
parent: ai-truth-gematria-hebrew-tutor
---

# Phase 2 — Hebrew Tutor Depth, Memorization Modes, Provider Hardening

Successor to `ai-truth-gematria-hebrew-tutor.md`. That plan's Tracks A/B/D/G1–G2
and the C1/C2/E1 cores are implemented and verified; the items below are what
remained after the 2026-08-24 verification pass, split out so the parent plan
closes with a true ledger. Nothing here blocks anything already shipped.

## Track P2-A: Tutor memory and evaluation (parent C3) — SHIPPED 2026-09-21

- [x] Layered tutor memory: recent working turns, session summary, durable
  learner preferences/goals, pedagogical state, raw transcript archive.
  (`lib/api/tutor_memory.py`: working = live message list (no storage);
  transcript archive auto-written at the pipeline `done` point for Hebrew
  mode (all paths: stream + jobs); session summaries via explicit-write
  endpoint + hydration; durable key/value store with source + evidence +
  date. Hydration appended to the Hebrew system prompt server-side,
  identity-bound.)
- [x] Stage candidate tutor notes; dedupe/conflict-resolve before durable
  storage; latest explicit learner correction wins.
  (Two-step stage→promote; learner source auto-promotes; staged tutor
  notes conflicting with durable learner rows reject as superseded;
  same-source latest wins. Routes: stage/staged/promote/memory.)
- [x] Long-context tests: recall a prior correction, respect a changed goal,
  reject stale memory, cite evidence/date. (tests/test_tutor_memory.py:
  10 tests incl. correction recall, goal change, stale rejection,
  evidence+date citation, forget scopes, transcript round-trip,
  Hebrew-only hydration + smuggled-state probe.)
- [ ] "Forget this" / stale-memory correction surface in the Hebrew UI.
  (Backend DONE: POST /api/v1/hebrew/tutor/forget key|all. UI button is a
  frontend follow-up — another track owns frontend right now.)
- Checkpoint: multi-session resume with bounded context; zero leakage into general chat.
  (Resume via transcript+summary endpoints; hydration bounded at 12 items;
  general-chat probe extended to the TUTOR MEMORY marker + tested.)

## Track P2-B: Remaining memorization modes (parent E2/E3 tails)

Registered as `planned` in `/api/v1/memorize/modes`; each needs route + queue
source + rating flow on the unified FSRS path before flipping to `available`.

- [x] Progressive hints beyond first-letter (P7): hint-level recorded for
  analytics and rating policy. (Pre-existing: preview_mode/level in
  memorize submit + memorize_reviews; per-mode analytics now reads it.)
- [x] Audio review mode (P8) submitting ratings to the same FSRS path.
  SHIPPED 2026-09-21: GET /api/v1/memorize/audio/next (due queue filtered
  to verses with read-along alignment audio + player URLs), rated via
  unified submit with {"source": "audio_mode"}. No new enqueue (shared
  queue); tests in tests/test_memorize_audio.py.
- [x] Analytics/polish (P9): retention, due workload, per-mode performance.
  SHIPPED 2026-09-21: GET /api/v1/memorize/analytics (overall + last-30d
  retention, due workload, per-mode GROUP BY per-attempt rating_source
  with queue-source fallback). Submit accepts an optional source override
  so the surface that produced the rating is what gets audited.
- [ ] PWA/push notifications (P10) only after permission/privacy review.
- [x] Hebrew cloze deletion cards with deterministic target/answer metadata.
  SHIPPED 2026-09-21: GET /api/v1/hebrew/cloze/next (same day+node →
  same question; blank geometry returned, answer stays server-side),
  rated via existing POST /api/v1/hebrew/progress (question_id+answer →
  FSRS '' row + attempt event). Due-ness keys off the '' schedule the
  mode itself writes. Tests in tests/test_hebrew_modes.py.
- [x] Two-way translation cards scheduled as distinct items.
  SHIPPED 2026-09-21: GET /api/v1/hebrew/translation/next serves due
  forward/reverse card_mode rows (pre-existing distinct FSRS schedules)
  + new-node fallback; rated via fsrs/review with card_mode.
- [x] Daily maintenance / verse-of-day mode with grammar+vocab breakdown.
      SHIPPED 2026-09-21 as `daily_maintenance`: GET /api/v1/memorize/daily
      (deterministic date-seeded pick from Hebrew-text verses, enqueued with
      source tag) rated through the unified POST /api/v1/memorize/review
      submit — no second scheduler. Review items + submit responses now
      carry `source`; modes matrix fixed to count the real queue table
      (was reading the wrong DB, totals always null). Registry → available.
      5 tests in tests/test_memorize_daily.py. Follow-ups (not this slice):
      vocab/grammar breakdown on the daily payload, due-aware daily pick.
- [x] Audio-first commute mode reusing review events.
  SHIPPED 2026-09-21: GET /api/v1/memorize/commute (due-with-audio stops
  in review order + today's daily as final stop, every stop queue-backed
  and rateable); each rating lands as a review event, no commute scheduler.
- [x] Hebrew-only visual mode with explicit reveal and a11y fallback.
  SHIPPED 2026-09-21 (backend): 'visual_only' added to CARD_MODES +
  review allowlist (distinct FSRS rows); GET /api/v1/hebrew/visual/next
  (due rows + new fallback, a11y_name per card); rated via fsrs/review.
  Client-side reveal UI is a frontend follow-up (no frontend edits in
  this slice — another track owns frontend right now).
- Checkpoint: every mode auditable via attempt events; no second scheduler.
  (Verse attempts: memorize_reviews.rating_source. Hebrew attempts:
  hebrew_attempt_events with evaluator_version. No new scheduler built.)

## Track P2-C: Scheduler reconciliation (parent E1 tail) — DECIDED 2026-09-21

- [x] Decide Python vs Go ownership for scripture-memorize FSRS state;
  implement compatibility adapters; document the decision.
  DECISION: Python owns all FSRS state; Go demoted to dormant backend
  (no scheduling authority). No adapter: disjoint stores, divergent math,
  zero cross-consumers — verified, nothing to adapt. Full rationale,
  evidence (file:line), and rules in
  `docs/adr/0001-fsrs-scheduler-ownership.md`. Latent trap documented
  there: dev `/api/memorize/*` → Go while prod → Python-404 (orphaned
  Go-only UI); fix deferred to palace/push revival.
- Checkpoint: one authoritative scheduler; the other proxied or retired.
  (Python authoritative; Go neither proxied nor retired — dormant by
  decision, revisit triggers listed in the ADR.)

## Track P2-D: Truth pipeline stages 2+ (parent A3/A4 tails)

- [ ] NLI/LLM entailment verifier behind the deterministic checker
      (`claims.py` stage 1 already gates misattributed quotes).
- [ ] Chain-of-Verification pass for contested doctrinal/historical answers.
- [x] `TruthfulScriptureQA` adversarial benchmark (~100 cases first):
      misattributed verses, popular sayings presented as Scripture,
      tradition-as-text conflations, false gematria claims.
      COMPLETE 2026-09-21 at 100 cases: `tests/truthful_scripture_qa_seed.json`
      (26 misattributed, 25 sayings, 24 tradition, 15 gematria, 10 positive
      controls; every cited verse text pulled live from the corpus, never
      hand-typed) + `tests/test_truthful_scripture_qa.py` enforcing the
      general gap rule (zero-check non-controls must carry GAP in note).
      Stage-1 tallies: 77 flagged, 11 passed, 12 documented gaps.
      Corpus quirk found: Matt 22:21 spells `Cæsar` (ligature survives
      normalization — quote it exactly).
- [ ] Regression gate on claim-support/citation-precision/abention metrics
      before any provider change.
- Checkpoint: benchmark shows fewer unsupported claims without refusing answerable questions.

## Track P2-E: Provider hardening (parent G4 tails)

- [x] Live load/429 drill across all four workspaces (manual runbook step:
      `docs/runbooks/opencode-go-pool.md`).
      AUTOMATED 2026-09-21: `scripts/provider_429_drill.py` (--dry-run
      default, --live requires --i-understand-costs; verifies every 429
      flows through RETRYABLE_STATUS into cooldown, nonzero exit otherwise).
      Live fire still needs a human (spends API budget + needs eyes on
      billing dashboards for server-side limits).
- [x] DeepSeek-vs-OpenCode-Go groundedness comparison using the P2-D
      benchmark under identical prompts/retrieval.
      HARNESS BUILT 2026-09-21: `scripts/provider_groundedness.py`
      (injectable chat_fn, --fake offline mode verified,
      --live --provider deepseek|opencode-go requires --i-understand-costs;
      per-category unsupported_rate + clean_rate) +
      `tests/test_provider_groundedness.py` (7 scoring tests green).
      Live comparison runs need a human (model spend).
- [ ] Staged feature-flag rollout mechanism beyond env selection if usage grows.
- Checkpoint: provider changes cannot bypass verifier/allowlists/quotas.

## Track P2-F: Monitoring instrumentation (parent F tail) — DONE 2026-09-21

- [x] Counters for quiz grading disagreement, progress-event idempotency
      hits, tutor-memory leakage probes, numerical citation rate.
      (`lib/monitoring.py`: bump/snapshot; sites: learn.py rating-vs-grade
      + idempotent replay, chat.py tutor-marker probe with strip,
      calibration.py numerical ceiling clamp.)
- [x] Surface counters through operator health only (not public).
      (Exposed as `scripture_p2{counter=...}` in /metrics; deliberately
      absent from the public /api/v1/health payload.)
- Checkpoint: plan monitoring targets observable in production.
  (Verify: `curl /metrics | grep scripture_p2` post-deploy.)

## Track P2-G: B3 purge execution

Neutralization is live (calibration ceiling + generator stop-list); archive
tooling exists. Execution remains deliberately deferred:

- [ ] Run a neutralization observation window; audit ranking changes.
- [ ] Execute `scripts/archive_retired_numerical.py --apply` during a quiet
      deploy window; verify graph regression against
      `docs/plans/b3-numerical-premigration-counts.json`.
- [ ] Update wiki corpus counts post-purge.
- Checkpoint: repeatable, reversible (`--restore`), documented deltas.

## Anti-scope

Inherited from the parent plan: no product deletion, no second chat/auth
stack, no new vector DB, no treating OpenCode Go as OpenRouter, no expanding
into unrelated content generation.
