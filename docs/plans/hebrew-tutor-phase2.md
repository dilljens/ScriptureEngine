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

## Track P2-A: Tutor memory and evaluation (parent C3)

- [ ] Layered tutor memory: recent working turns, session summary, durable
  learner preferences/goals, pedagogical state, raw transcript archive.
- [ ] Stage candidate tutor notes; dedupe/conflict-resolve before durable
  storage; latest explicit learner correction wins.
- [ ] Long-context tests: recall a prior correction, respect a changed goal,
  reject stale memory, cite evidence/date.
- [ ] "Forget this" / stale-memory correction surface in the Hebrew UI.
- Checkpoint: multi-session resume with bounded context; zero leakage into general chat.

## Track P2-B: Remaining memorization modes (parent E2/E3 tails)

Registered as `planned` in `/api/v1/memorize/modes`; each needs route + queue
source + rating flow on the unified FSRS path before flipping to `available`.

- [ ] Progressive hints beyond first-letter (P7): hint-level recorded for
  analytics and rating policy.
- [ ] Audio review mode (P8) submitting ratings to the same FSRS path.
- [ ] Analytics/polish (P9): retention, due workload, per-mode performance.
- [ ] PWA/push notifications (P10) only after permission/privacy review.
- [ ] Hebrew cloze deletion cards with deterministic target/answer metadata.
- [ ] Two-way translation cards scheduled as distinct items.
- [ ] Daily maintenance / verse-of-day mode with grammar+vocab breakdown.
- [ ] Audio-first commute mode reusing review events.
- [ ] Hebrew-only visual mode with explicit reveal and a11y fallback.
- Checkpoint: every mode auditable via attempt events; no second scheduler.

## Track P2-C: Scheduler reconciliation (parent E1 tail)

- [ ] Decide Python vs Go ownership for scripture-memorize FSRS state;
  implement compatibility adapters; document the decision.
- Checkpoint: one authoritative scheduler; the other proxied or retired.

## Track P2-D: Truth pipeline stages 2+ (parent A3/A4 tails)

- [ ] NLI/LLM entailment verifier behind the deterministic checker
      (`claims.py` stage 1 already gates misattributed quotes).
- [ ] Chain-of-Verification pass for contested doctrinal/historical answers.
- [ ] `TruthfulScriptureQA` adversarial benchmark (~100 cases first):
      misattributed verses, popular sayings presented as Scripture,
      tradition-as-text conflations, false gematria claims.
- [ ] Regression gate on claim-support/citation-precision/abention metrics
      before any provider change.
- Checkpoint: benchmark shows fewer unsupported claims without refusing answerable questions.

## Track P2-E: Provider hardening (parent G4 tails)

- [ ] Live load/429 drill across all four workspaces (manual runbook step:
      `docs/runbooks/opencode-go-pool.md`).
- [ ] DeepSeek-vs-OpenCode-Go groundedness comparison using the P2-D
      benchmark under identical prompts/retrieval.
- [ ] Staged feature-flag rollout mechanism beyond env selection if usage grows.
- Checkpoint: provider changes cannot bypass verifier/allowlists/quotas.

## Track P2-F: Monitoring instrumentation (parent F tail)

- [ ] Counters for quiz grading disagreement, progress-event idempotency
      hits, tutor-memory leakage probes, numerical citation rate.
- [ ] Surface counters through operator health only (not public).
- Checkpoint: plan monitoring targets observable in production.

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
