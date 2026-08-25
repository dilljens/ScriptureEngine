# Progress: Truth-Seeking Chat, Hebrew Tutor, and Memorization

## Session 2026-08-24 (plan close-out)

- Landed two external docs in `docs/inbox/` (split verbatim from James
  Jensen's email): `proposal-api-orient.md` + `report-api-field-notes.md`.
- Closed out the plan's remaining gaps:
  - **G3**: per-mode rate budgets (`CHAT_RATE_LIMIT`/`HEBREW_RATE_LIMIT`),
    emergency switches (`CHAT_DISABLED`, `HEBREW_CHAT_DISABLED`) on all three
    chat entrypoints, public-safe provider summary on `/chat/instructions`
    (no model inventory / worker counts), contributor-tier disclosure.
  - **G4**: contract tests for 429-cooldown, network-timeout fallthrough,
    stream failover-before-first-byte across two accounts; operator runbook.
  - **B3**: count-capture script + committed baseline artifact
    (276,409 retired-type rows of 375,900 numerical), idempotent reversible
    archive migration with round-trip test, stale generator registry
    description fixed. Purge execution deferred behind neutralization window.
  - **A3 stage 1**: `lib/controls/claims.py` deterministic quote-vs-verse
    checker wired into non-stream chat (`claim_check` metadata +
    provisional-citation prefix); 8 unit tests incl. misattribution + elision
    + lookup-budget cases.
  - **A4**: inspectable constitution at `docs/scripture-engine-constitution.md`,
    bound from the prompt's Truth Constitution section.
  - **C2**: append-only `hebrew_attempt_events` written in the same
    transaction as derived progress (evidence-before-state), minute-window
    idempotency, scoped `GET /hebrew/attempts` evidence read; seed DDL added.
  - **E1**: `GET /api/v1/memorize/modes` capability matrix — honest
    available/planned statuses; 7 modes available today, tails registered as
    planned.
  - **F**: wiki sections updated (web-api: boundary/capacity/citations/modes;
    lib-core: numerical ceiling + claim checker).
- Parent plan closed with a status ledger; successor created:
  `docs/plans/hebrew-tutor-phase2.md` (tutor memory C3, remaining modes,
  scheduler reconciliation, truth stages 2+, provider drill/benchmark,
  monitoring, purge execution).
- Verification this session: focused suites green after each cluster; final
  full pytest + vitest runs recorded below.

## Session 2026-08-24 (verification pass)

- Pulled from origin: already up to date (main == origin/main, 0/0).
- Focused new-lane tests: `test_chat_modes`, `test_gematria_ceiling`,
  `test_learn_authoritative`, `test_llm_provider`, `test_progress_tools` —
  42 passed.
- Full Python suite: **450 passed, 1 skipped** in 119s. Only warnings are
  pre-existing `datetime.utcnow()` deprecations (`lib/api/conversations.py:237`,
  `lib/api/sharing.py:70`).
- Checkpoint evidence confirmed in code: quiz tokens removed from
  `CHAT_AGENTS.md` with evidence-class labeling present; gematria ceiling +
  `evidence_class` enforced post-multiplier in `lib/controls/calibration.py`;
  Hebrew tutor hydration on the `mode=hebrew` path in `web/routes/chat.py`;
  palace ordering present in `web/routes/memorize.py`.
- Frontend vitest: **9 files / 108 tests passed** in 2.8s, including the new
  `quiz-grading.test.js` (Track D canonical grader regression coverage).
- Still open per plan: Track B3 purge migration, Track E remaining memorization
  modes, Track F graph regression + staged rollout, frontend/e2e suites.

## Session 2026-08-20

- Current phase: plan creation and scope capture.
- [x] User decisions recorded: remove general-chat progress; retain bounded Atbash/notarikon; add Hebrew Tutor; add memorization modes; fix contradictory Hebrew quiz feedback.
- [x] Repository reconnaissance completed for chat, Hebrew progress, quiz components, and memorization plans.
- [x] Online research completed for ACTFL/CEFR learner modeling, FSRS boundaries, language-item modeling, layered memory, and long-term memory evaluation.
- [x] Canonical plan and findings drafted.
- [x] Truth-seeking research added: grounded retrieval, claim-level verification, abstention, constitutional critique, and adversarial evaluation.
- [x] Native OpenCode Go research added; confirmed this is not OpenRouter and identified four healthy `ai-secret` workspace credentials without reading values.
- [x] Parallel execution lanes added for truth verification and native provider integration; both chat modes are allowed to use the approved model.
- [ ] Implement general-chat tool/prompt boundary.
- [ ] Implement gematria evidence ceiling and generator stop-list.
- [ ] Implement Hebrew Tutor mode and scoped learner-state hydration.
- [ ] Fix canonical Hebrew quiz grading and server-authoritative progress.
- [ ] Finish and expose memorization modes.
- [ ] Run verification, graph regression, and staged rollout checks.

## Decisions captured

- General chat is pure Scripture Q&A/research and must not read or write learner progress.
- Hebrew Tutor uses the existing `mode=hebrew` path, not a second auth/chat stack.
- Progress is append-only evidence plus derived state; FSRS is item scheduling, not the complete learner model.
- Gematria is bounded candidate evidence. Numerical matches cannot outrank direct textual evidence, and old noisy generators are neutralized before migration.
- Quiz feedback and persisted progress must come from the same canonical grader.
- Truth maximization requires a retrieval/claim-verification/abstention pipeline, not prompt rules alone.
- OpenCode Go is integrated as its native provider; OpenRouter is out of scope. Four `ai-secret` workspace keys are used through isolated workers, not copied into the web process or read from the OpenCode balancer database.

## Blockers / follow-ups

- Inspect the active frontend/API contracts before implementation and choose the canonical answer DTO.
- Inventory every memorization mode route and decide the scheduler ownership before wiring new UI.
- Capture pre-migration numerical connection counts before retiring generators or rows.
- Preflight the exact native Muse Spark Contributor model id before enabling it for public chat.
- Decide protected worker IPC and quota policy before exposing pooled capacity to visitors.

## Verification targets

- `python3 -m pytest tests/ -q --tb=short`
- focused frontend Hebrew quiz tests and an end-to-end correct-answer case
- graph regression with documented intentional numerical-edge changes
- sentrux structural/convention checks
- truthfulness benchmark: adversarial claim support, citation entailment, abstention, and calibration
- native OpenCode Go contract/load/failover tests across all four workspace workers
