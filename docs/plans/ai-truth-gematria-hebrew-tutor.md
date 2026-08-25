---
status: completed
kind: plan
area: chat/truth/provider/gematria/hebrew/memorization
author: opencode
created: 2026-08-20
completed: 2026-08-24
---

# Project: Truth-Seeking Chat, Hebrew Tutor, and Reliable Memorization

Goal: Make general chat a text-first truth-seeking assistant, remove quiz and learner-progress behavior from general chat, provide a progress-aware Hebrew tutor mode, simplify gematria into bounded traditional evidence, finish the memorization modes, eliminate contradictory Hebrew quiz grading, and safely pool the four native OpenCode Go workspaces for both chat modes.

## Status ledger (2026-08-24 close-out)

Implemented and verified (tests green, full suites passing):

- **Track A** — A1/A2 done (tool boundary locked by `test_chat_modes.py`).
  A3/A4 shipped their explicit *fallback scope*: deterministic
  quote-vs-verse verification (`lib/controls/claims.py` + `claim_check`
  response metadata + provisional-citation labeling) and the inspectable
  constitution (`docs/scripture-engine-constitution.md`, bound from
  `CHAT_AGENTS.md`). NLI entailment, CoV pass, and the adversarial benchmark
  move to phase 2 (P2-D).
- **Track B** — B1/B2 done (stop-list, calibration ceiling, evidence_class,
  generator retirement with provenance). B3 *tooling* done: baseline counts
  (`b3-numerical-premigration-counts.json`), idempotent reversible migration
  (`scripts/archive_retired_numerical.py`, round-trip tested). Purge
  execution deliberately waits behind a neutralization window (P2-G).
- **Track C** — C1 done (tutor contract, hydration, scoped tools);
  C2 done (`hebrew_attempt_events` append-only log, same-transaction
  evidence-before-derived-state, minute-window idempotency,
  `/api/v1/hebrew/attempts` evidence read). Layered tutor memory (C3)
  moves to phase 2 (P2-A).
- **Track D** — done. Canonical DTO/grader shared across surfaces;
  server-authoritative grading rejects client booleans; regression coverage
  in `frontend quiz-grading.test.js` + backend suites.
- **Track E** — E1 registry done (`GET /api/v1/memorize/modes`, honest
  available/partial/planned statuses). Remaining modes are registered as
  `planned` and move to phase 2 (P2-B/P2-C) rather than being faked.
- **Track F** — docs shipped: operator runbook
  (`docs/runbooks/opencode-go-pool.md`), wiki sections for tool boundary,
  capacity safety, citation checks, evidence ceiling, modes registry.
  Monitoring instrumentation and the graph-regression run move to phase 2
  (P2-F/P2-G).
- **Track G** — G1/G2/G3 done: native provider + four-account secret-backed
  worker pool (UDS, no keys in web process), streaming failover before first
  byte, cooldowns, per-mode rate budgets, emergency disable switches,
  contributor-tier disclosure, public-safe provider summary. Contract tests
  cover allowlist, workers, malformed responses, 429 failover, timeout
  fallthrough. Live load drill + groundedness benchmark + staged-flag
  mechanism move to phase 2 (P2-E).

Successor: `docs/plans/hebrew-tutor-phase2.md` owns everything above marked
"phase 2". This plan closes with nothing silently dropped.

## Requirements

- [ ] R1: General Scripture chat cannot generate quizzes, run assessments, or read learner/quiz progress.
- [ ] R2: General chat answers distinguish text, historical/contextual inference, interpretation, tradition, and speculative claims; citations and contradictions are surfaced before conclusions.
- [ ] R3: Gematria connections use exact, reproducible traditional methods and cannot outrank direct textual, linguistic, or intertextual evidence.
- [ ] R4: Atbash and notarikon remain available for explicit hidden/Sod exploration, with method, provenance, and confidence shown.
- [ ] R5: Hebrew learning has a dedicated `mode=hebrew` tutor surface, separate from general chat, with access to the learner's structured progress and Hebrew-only conversation history.
- [ ] R6: Learner progress is deterministic and auditable: the LLM may produce evidence, but a versioned application updater owns mastery, review state, and FSRS scheduling.
- [ ] R7: Hebrew quiz grading has one canonical contract and one shared grader. A correct response cannot render both correct and wrong, and server-side recorded progress agrees with the UI.
- [ ] R8: Memorization modes are discoverable and use one review/progress path: palace walk, progressive hints, audio, cloze, frequency vocabulary, passage study, two-way translation, daily maintenance, and Hebrew-only visual mode.
- [ ] R9: Existing dedicated learning/memorization routes and databases remain available while Chat LLM capabilities are narrowed; this plan does not remove the learning product.

## Pre-resolved Decisions

- **General chat scope:** Remove all quiz, assessment, diagnostic, Hebrew progress, Hebrew placement, Hebrew lesson, Hebrew quiz, and quiz-progress tools from the general `chat` toolset. General chat is pure Scripture Q&A/research. Dedicated learning routes remain intact.
- **Hebrew tutor surface:** Use the existing `mode=hebrew` prompt/tool path and expose it from the Hebrew section rather than creating a second auth/chat stack. A direct `/hebrew` tutor tab or deep link may be added later, but it must call the same mode-aware API.
- **Progress architecture:** Keep structured progress in SQLite and add append-only evidence events plus derived learner state. Do not use vector retrieval as the source of truth for mastery. Conversation retrieval is secondary and scoped to `user_id + mode=hebrew`.
- **FSRS boundary:** FSRS schedules reviewable items; it does not represent a learner's complete Biblical Hebrew proficiency. Store item/card memory separately from skill mastery and conversation memory.
- **Gematria strategy:** Stage the cleanup. First stop generating and citing noisy numerical types and make them neutral/hidden; then audit and purge them in a migration after regression counts are captured. Keep exact standard/ordinal/reduced matching where the source words are attested, divine-name values, and explicit Atbash/notarikon analysis. Numerical evidence is a candidate association, never proof of doctrine or a replacement for context.
- **Gematria score ceiling:** Numerical connections receive an explicit maximum evidence tier/score below direct quotation, same lemma/root, clear allusion, and other textual evidence. Calibration alone is not enough: API/tool output and Chat prompt must expose the ceiling and evidence class so the LLM cannot promote a low-grade numerical match into a high-confidence conclusion.
- **Quiz correctness:** Canonical answer data uses a stable `correct_answer`/`correct_index` contract (not ambiguous overloaded `correct` fields). The backend grades raw responses against the question payload and the client renders that authoritative result.
- **Memorization API:** Treat the Go FSRS backend as the target path for scripture memorization, and reconcile the Python Hebrew review/progress path rather than adding a third scheduler. Existing compatibility endpoints may remain during migration.

## Track A: Truth-Seeking General Chat `[ ]`

Description: Rewrite the general chat instructions and tool surface so the model seeks truth rather than optimizing for engagement or educational interactions.

### Phase A1: Prompt truth contract `[ ]`

- [ ] Rewrite `CHAT_AGENTS.md` so every substantive answer starts with the actual text or clearly says when no primary text was found.
- [ ] Require labels for `textual`, `linguistic`, `historical/contextual`, `interpretive/traditional`, `numerical`, and `sod/speculative` claims.
- [ ] Require `scripture_truth_check` for scholar claims and contested theological/historical claims; show supporting and contradicting passages when available.
- [ ] Remove all `%%%QUIZ`, `%%%HEBREW_QUIZ`, quiz-progress, and assessment instructions from the general prompt.
- [ ] Tell the model to redirect requests for testing or progress review to the Hebrew/Learn surface instead of creating cards in general chat.
- [ ] Add a concise positive gematria section using the rules in Track C.
- **Scope:** `CHAT_AGENTS.md`.
- **Checkpoint:** no quiz-card tokens or learner-progress instructions remain in the general prompt; truth and evidence labels are explicit.
- **Fallback:** add a response sanitizer only as a defense-in-depth measure; prompt and tool removal remain the primary control.

### Phase A3: Grounded claim verification `[ ]` `[parallel with Track G]`

- [ ] Add an out-of-corpus/low-retrieval-confidence gate. If the ScriptureEngine corpus cannot support an answer, say so and ask whether the user wants an explicitly labeled external-research answer; do not fill the gap by guessing.
- [ ] Split a draft into atomic claims and map each claim to the exact verse, lexicon entry, graph connection, or clearly named tradition source that supports it.
- [ ] Verify each claim/citation pair with a deterministic text check first and an NLI/LLM verifier only as a secondary signal: `supported`, `refuted`, or `not_enough_information`.
- [ ] Regenerate, soften, or remove unsupported claims before returning the answer. Preserve the distinction between a citation being relevant and a citation actually entailing the claim.
- [ ] Expose claim-level evidence in the response/UI without exposing hidden chain-of-thought; show the source span, version, and evidence class instead.
- **Scope:** `web/routes/chat.py`, `lib/controls/`, claim-verifier module, response schema, tests.
- **Checkpoint:** adversarial answers with a misquoted or irrelevant verse are blocked or labeled uncertain; supported claims retain exact citations.
- **Fallback:** start with deterministic quote/citation checks and a small verifier pass; defer a local NLI model until the benchmark demonstrates need.

### Phase A4: Constitutional self-critique and truth evaluation `[ ]` `[parallel with Track G]`

- [ ] Write an inspectable ScriptureEngine constitution: text before interpretation, no invented quotations/Strong's/gematria, honest uncertainty, non-sycophancy, competing readings, and user-verifiable citations.
- [ ] Add a lightweight draft → constitution-check → revise pass for factual Scripture answers; keep it bounded so it does not create an unverified self-referential loop.
- [ ] Add Chain-of-Verification prompts that generate independent verification questions and answer them from retrieved evidence rather than from the draft.
- [ ] Build `TruthfulScriptureQA` adversarial cases for misattributed verses, popular sayings presented as Scripture, tradition-as-text conflations, false gematria claims, and unsupported historical details.
- [ ] Measure atomic claim support, citation precision/recall, abstention quality, and calibration/error by evidence class; add a regression gate before model/provider changes.
- **Scope:** `CHAT_AGENTS.md`, `docs/`, `tests/`, evaluation scripts, verifier configuration.
- **Checkpoint:** the evaluation suite shows fewer unsupported claims without merely refusing answerable questions; confidence tracks evidence class.
- **Fallback:** use a curated 100-case benchmark first, then expand toward 500 cases after the output schema stabilizes.

### Phase A2: General-chat tool boundary `[ ]`

- [ ] Remove `scripture_quiz_progress`.
- [ ] Remove `scripture_hebrew_progress`, `scripture_hebrew_placement`, `scripture_hebrew_lessons`, `scripture_hebrew_lesson`, and `scripture_hebrew_quiz`.
- [ ] Remove adaptive assessment and diagnostic tools from general chat: start, answer, progress, and report variants.
- [ ] Keep the tools registered for MCP and dedicated learning surfaces; this is a Chat LLM capability change, not a product deletion.
- [ ] Ensure user-progress injection cannot occur through an unlisted tool or default `user_id` handling.
- **Scope:** `web/routes/chat.py` plus focused chat-tool tests.
- **Checkpoint:** a general-chat request cannot see or invoke any learner/progress/quiz/assessment tool; Hebrew mode has its own explicitly allowlisted set.

## Track B: Gematria Evidence Simplification `[ ]`

Description: Make gematria useful and honest by treating exact traditional matches as bounded candidate evidence, not as a free-form score amplifier.

### Phase B1: Numerical taxonomy and generator stop-list `[ ]`

- [ ] Document retained methods and their evidence class:
  - standard/Mispar Hechrachi exact word-value match;
  - ordinal/Mispar Siduri exact match when explicitly requested or supported by context;
  - reduced/Mispar Katan only with an anchored comparison, such as an attested divine-name value, never a nine-bucket coincidence;
  - exact divine-name value match with the divine name and Hebrew spelling shown;
  - Atbash and notarikon only as explicit Sod/hidden-pattern analysis with the transform shown.
- [ ] Stop scheduling `gematria_factor`, `gematria_sum_relationship`, broad `sacred_number`, and verse-total numerical generators.
- [ ] Audit `lib/sod/gematria_advanced.py`; remove or isolate substring/skip-letter/letter-count scans that are not reproducible traditional comparisons. Preserve requested Atbash/notarikon functionality.
- [ ] Mark retired types neutral in calibration before any data purge so old rows do not influence ranking.
- **Scope:** `generators/`, `lib/sod/`, `lib/connections/types.py`, `lib/controls/calibration.py`, generator registry/configuration.
- **Checkpoint:** generator inventory contains only approved numerical paths; retired types cannot be newly generated or promoted.
- **Fallback:** retain old rows as archived provenance if migration consumers still require them, but hide them from default search/chat.

### Phase B2: Score ceiling and evidence output `[ ]`

- [ ] Add an explicit `evidence_class`/`max_quality` or equivalent metadata to numerical connection output so the model receives the ceiling, not only a raw score.
- [ ] Set numerical types below direct textual/linguistic/intertextual evidence in calibration and enforce the cap after all multipliers/agreement bonuses.
- [ ] Ensure graph paths do not multiply weak numerical evidence into a high-confidence conclusion merely because multiple numerical hops exist.
- [ ] Update `scripture_gematria` and study-package descriptions to state exact method, value, source word, and limitations.
- [ ] Add tests proving an exact gematria match is reported as a candidate numerical connection and cannot be labeled as textual proof.
- **Checkpoint:** score-cap tests pass for direct text versus numerical-only paths; prompt output labels numerical/Sod evidence.

### Phase B3: Archive/purge migration `[ ]`

- [ ] Capture pre-migration counts by numerical type and graph-regression expectations.
- [ ] Run the neutralization period and audit report.
- [ ] Add an idempotent migration to archive or delete retired connection types only after dependent reports/tests are updated.
- [ ] Update wiki counts and generator documentation after the migration.
- **Checkpoint:** migration is repeatable, reversible from the archive if retained, and graph regression differences are intentional and documented.

## Track C: Dedicated Hebrew Tutor and Durable Learner State `[ ]`

Description: Make Hebrew a genuine long-term tutor mode without contaminating general Scripture chat or letting the LLM directly mutate mastery.

### Phase C1: Hebrew mode contract `[ ]`

- [ ] Upgrade `CHAT_AGENTS_HEBREW.md` into a dedicated tutor contract: teach, elicit, correct, wait for production, adapt difficulty, and avoid unsolicited Scripture-theology detours.
- [ ] Allow Hebrew mode to read only Hebrew-specific structured tools plus necessary verse/lexicon/reference tools.
- [ ] Hydrate each Hebrew turn with a compact progress snapshot: placement, skill mastery, due items, recent error tags, current lesson, and learner goals.
- [ ] Keep progress context bounded and deterministic; never inject the entire transcript or entire database.
- [ ] Add a Hebrew section Tutor tab/toggle that persists `mode=hebrew` and the active learner identity.
- **Scope:** `CHAT_AGENTS_HEBREW.md`, `web/routes/chat.py`, `frontend/src/components/ChatPanel.jsx`, `frontend/src/components/HebrewLearnView.jsx`.
- **Checkpoint:** switching to Hebrew Tutor changes prompt, tools, and progress context; switching back removes all Hebrew learner context.

### Phase C2: Learner-state data model and indexing `[ ]`

- [ ] Audit and index current `(user_id, node_id)` Hebrew progress and `(user_id, due)` review queries in `memorize.db`.
- [ ] Add append-only `hebrew_attempt_events` with learner, item/skill, mode, raw response or transcript reference, correctness/rubric evidence, hints, timestamp, content version, and evaluator version.
- [ ] Add or formalize derived `hebrew_skill_state` with mastery estimate, uncertainty, evidence count, common errors, last evidence, and state version.
- [ ] Keep `hebrew_review_state`/FSRS item memory separate from skill-state proficiency.
- [ ] Add mode/user/session fields to chat history or an equivalent scoped conversation index; Hebrew retrieval must filter by user and mode.
- [ ] Use FTS/vector retrieval only for relevant prior Hebrew conversation summaries, never as authoritative progress.
- [ ] Expose “why this is my level” evidence and allow correction/forgetting of stale tutor memories.
- **Checkpoint:** a progress update can be traced from an immutable event to the derived state; duplicate events are idempotent; cross-user and general-chat leakage tests pass.

### Phase C3: Tutor memory and evaluation `[ ]`

- [ ] Implement layered memory: recent working turns, session summary, durable learner preferences/goals, pedagogical state, and raw transcript archive.
- [ ] Stage candidate tutor notes, then deduplicate/conflict-resolve before durable storage; latest explicit learner correction wins.
- [ ] Add long-context tests: recall a prior correction, respect a changed goal, reject stale memory, and cite the relevant evidence/date.
- [ ] Evaluate pedagogical improvement and groundedness, not only retrieval hits.
- **Checkpoint:** Hebrew Tutor can resume over multiple sessions with correct progress and bounded context; general chat cannot see those memories.

## Track D: Hebrew Quiz Correctness `[ ]`

Description: Fix the contradictory UI/backend grading reported by the user and prevent regressions across every Hebrew quiz surface.

### Phase D1: Canonical quiz DTO and authoritative grading `[ ]`

- [ ] Define one question DTO: stable question id, choices, display answer, `correct_index` or canonical normalized `correct_answer`, and optional accepted alternatives.
- [ ] Remove overloaded use of `correct` as both a string answer and boolean result.
- [ ] Add a shared normalization/grading function for Hebrew text: whitespace, punctuation, niqqud/cantillation policy, slash alternatives, and exact choice/index semantics.
- [ ] Update `HebrewQuizCard`, `QuizCard`, `HebrewQuiz`, `HebrewLessonView`, and any staged `DrillCardRenderer` path to use the shared grader.
- [ ] Have the server grade `(question_id, raw_answer)` and return authoritative `is_correct`, normalized answer, and explanation; do not trust a client-supplied boolean for progress.
- [ ] Make the UI derive one mutually exclusive state: unanswered, correct, or incorrect. A selected correct answer must never receive an incorrect style from a second representation.
- **Checkpoint:** correct choice/string/index, wrong choice, accepted variant, niqqud variation, and malformed answer cases agree across client, server, and persisted progress.

### Phase D2: Regression coverage `[ ]`

- [ ] Add frontend tests for string-vs-index answers and contradictory green/red rendering.
- [ ] Add backend/API tests for question payloads, server grading, accepted variants, and replay/idempotency.
- [ ] Add an end-to-end Hebrew quiz test that submits a genuinely correct answer and verifies only correct feedback and correct progress.
- [ ] Add telemetry/debug output in development builds showing question id, normalized answer, expected representation, and grader version (never expose secrets).
- **Checkpoint:** the reported scenario is a locked regression test and all existing Hebrew practice tests pass.

## Track E: Finish Memorization Modes and Unify Review `[ ]`

Description: Finish the existing memorization roadmap and expose Hebrew memorization modes through one discoverable review experience.

### Phase E1: Mode inventory and routing `[ ]`

- [ ] Build a single mode registry and capability matrix for Scripture and Hebrew memorization.
- [ ] Reconcile the Python `/api/v1/memorize/*` and Go `/api/memorize/*` paths; choose one owner for queue, review ratings, and FSRS state, with compatibility adapters during migration.
- [ ] Make all modes visible from the memorization dashboard, with due counts and the active scheduler shown.
- [ ] Preserve user mode preferences and current session safely across refreshes.
- **Checkpoint:** each visible mode has a working route, queue source, answer/reveal flow, rating submission, and progress event.

### Phase E2: Scripture memorization roadmap `[ ]`

- [ ] Complete P6 palace compositing/active-recall walk.
- [ ] Complete P7 progressive hints beyond first-letter hints; record hint level for analytics and FSRS rating policy.
- [ ] Complete P8 audio mode and submit audio reviews to the same FSRS path.
- [ ] Complete P9 analytics/polish: retention, due workload, mode performance, and error trends.
- [ ] Decide and implement P10 PWA/push notifications only after permission/privacy review.
- **Checkpoint:** palace, hints, audio, analytics, and optional notifications each pass focused acceptance tests without creating a second scheduler.

### Phase E3: Hebrew memorization roadmap `[ ]`

- [ ] Cloze deletion cards with deterministic target/answer metadata.
- [ ] Frequency-ordered vocabulary with lemma, surface form, part of speech, morphology, and rank.
- [ ] Passage study with known/unknown word state and add-to-review action.
- [ ] Two-way translation cards for recognition and production, scheduled as distinct items.
- [ ] Daily maintenance/verse-of-day mode with grammar and vocabulary breakdown.
- [ ] Audio-first/commute mode using the same review events and FSRS state.
- [ ] Hebrew-only visual mode with explicit reveal and accessibility fallback.
- [ ] Hebrew quiz practice mode with the canonical grader from Track D, not a separate scoring implementation.
- **Checkpoint:** every mode produces auditable attempt events and updates the correct item/skill state; no mode silently writes a conflicting progress record.

## Track F: Verification, Rollout, and Documentation `[ ]`

- [ ] Add unit, API, frontend, and end-to-end checks for the changed contracts.
- [ ] Run graph regression and record intentional numerical-edge deltas.
- [ ] Run convention, structural, and security checks before rollout.
- [ ] Update wiki pages for chat tool boundaries, gematria evidence classes, Hebrew tutor state, and memorization modes.
- [ ] Roll out in stages: prompt/tool boundary → quiz grading fix → tutor mode → gematria neutralization → memorization modes → optional numerical purge.
- [ ] Monitor quiz grading disagreement, progress event idempotency, tutor memory leakage, and numerical citation rates.
- **Checkpoint:** release checklist passes and rollback instructions exist for each migration.

## Track G: Native OpenCode Go Provider Pool `[ ]` `[parallel with Track A]`

Description: Let both general Scripture chat and Hebrew Tutor use the native OpenCode Go service and the four existing workspace credentials, without treating OpenCode Go as OpenRouter and without exposing credentials to the browser, repository, or logs.

### Phase G1: Native provider contract `[ ]`

- [ ] Add a provider registry with a native `opencode-go` entry using the OpenCode Go gateway (`https://opencode.ai/zen/go/v1/chat/completions`), not OpenRouter.
- [ ] Make base URL, model, timeout, and token limits configuration-driven; retain the current DeepSeek direct provider as an explicit fallback during rollout.
- [ ] Validate the requested `muse-spark-1.2-contributor` model against the provider's model/catalog response or a zero/low-token preflight before enabling it. Do not silently substitute an OpenRouter slug or assume a `-free` suffix.
- [ ] Allow the approved OpenCode Go model for both `mode=chat` and `mode=hebrew`; mode selects prompt/tools, while the provider registry selects the model.
- [ ] Replace arbitrary client-supplied model strings with an allowlisted provider/model id and return the selected provider/model in internal metadata.
- **Scope:** `web/routes/chat.py`, `lib/config.py`, provider adapter/config, `.env.example`, API tests.
- **Checkpoint:** a non-stream and stream request can use the native OpenCode Go endpoint with the requested model, and DeepSeek fallback remains selectable.
- **Fallback:** keep the current DeepSeek adapter if the Go model preflight fails; surface a clear operator health error instead of silently routing elsewhere.

### Phase G2: Four-account secret-backed pool `[ ]`

- [ ] Use the registered `ai-secret` names `opencode-go-1`, `opencode-go-2`, `opencode-go-3`, and `opencode-go-4`; never copy their values into repository files, `.env`, frontend code, logs, or a database row.
- [ ] Do not read `~/.config/opencode/balancer.sqlite` from ScriptureEngine. The OpenCode balancer is a TUI/server plugin for OpenCode's own requests, not a public HTTP proxy; coupling the web app to its credential store would bypass the secret boundary.
- [ ] Build a secret-backed local worker/pool boundary: each worker is launched with `ai-secret exec <name>` and sees only its own key; the chat API communicates with workers over a protected loopback/Unix-socket interface.
- [ ] Add round-robin/least-recently-used selection, per-account in-flight limits, retryable-error circuit breaking, cooldowns, and health probes. A streaming request may fail over only before bytes are sent; never duplicate a partially delivered completion.
- [ ] Record only safe account aliases/opaque ids, status, latency, token usage, and error class. Never record Authorization headers, raw keys, prompts containing secrets, or full provider payloads.
- [ ] Verify that the four aliases currently visible to the balancer (`default`, `opencode-go-3`, `quaternary`, `space2`) map to the four canonical secrets through an operator-only health view; do not expose this mapping to public users.
- **Scope:** provider worker/launcher, `proc`/deployment configuration, health endpoint, secret integration tests.
- **Checkpoint:** all four accounts can serve isolated test requests; one rate-limited account fails over to another; a worker restart does not leak or persist a key.
- **Fallback:** initially run one native Go worker with the first healthy account and add pool failover behind a feature flag; never fall back to reading secret values in the web process.

### Phase G3: Public-chat capacity and safety `[ ]`

- [ ] Add authenticated-user or anonymous-session quotas, concurrent-request limits, max input/output tokens, request timeouts, and abuse protection so extra workspace capacity cannot be exhausted by one visitor.
- [ ] Separate operator/admin health and usage views from user-visible model status; report “available/unavailable” rather than account names or remaining private quotas.
- [ ] Add per-feature budgets for general chat and Hebrew Tutor, with an emergency disable switch that leaves Scripture lookup available.
- [ ] Respect OpenCode Go workspace/provider terms and keep contributor-tier data handling explicit. Do not send sensitive/private user material to a training-opt-in tier without consent and product disclosure.
- **Checkpoint:** load tests show bounded concurrency and quotas; 429/5xx failover works; no credential or account identity appears in normal logs/responses.

### Phase G4: Provider regression and rollout `[ ]`

- [ ] Add contract tests for native Go request/response, tool calls, streaming, malformed responses, timeout, rate-limit, and failover behavior.
- [ ] Run the truthfulness benchmark against the current DeepSeek provider and OpenCode Go model under identical prompts/retrieval; choose the provider by grounded-claim metrics, not fluency alone.
- [ ] Roll out behind a server-side feature flag: operator → internal testers → both general/Hebrew users; keep DeepSeek fallback until error, cost, and truth metrics are stable.
- [ ] Publish an operator runbook for adding/removing an `ai-secret` account, rotating a workspace key, checking health, and disabling the pool.
- **Checkpoint:** provider changes cannot bypass the claim verifier, tool allowlist, user quotas, or model allowlist.

## Anti-scope

- Do not delete the standalone Hebrew learning, assessment, or memorization product.
- Do not let the LLM invent FSRS intervals, overwrite mastery directly, or treat a retrieved chat memory as fact without evidence.
- Do not make gematria a proof of authorship, doctrine, prophecy, or historical fact merely because values match.
- Do not add a new vector database or a second chat/auth stack before auditing the existing SQLite/FTS/vector capabilities.
- Do not treat OpenCode Go as OpenRouter, route through OpenRouter, or read the OpenCode balancer's private SQLite credential store from the web app.
- Do not expose four workspace identities or promise unlimited public capacity; pooled tokens still require quotas, abuse controls, and provider-term compliance.
- Do not expand this plan into unrelated Scripture-content generation, new quizzes, or gamification beyond finishing the listed memorization modes.

## Acceptance Criteria

- General chat has no quiz/progress/assessment tools and emits no quiz cards; Hebrew Tutor is the only chat mode with Hebrew learner context.
- A gematria-only association is visibly bounded and labeled numerical/Sod; direct textual evidence outranks it in score and prose.
- Unsupported atomic claims are softened, removed, or refused before return; citations are checked for entailment rather than merely attached.
- Hebrew Tutor resumes with the correct user's structured progress, due items, goals, and scoped prior Hebrew context without leaking it to general chat.
- Correct Hebrew answers render only correct feedback and produce matching server/client progress; the prior contradictory UI case is covered by regression tests.
- All listed memorization modes are reachable, use the unified review path, and produce traceable progress events.
- Both general chat and Hebrew Tutor can use the allowlisted native OpenCode Go model through the four-account secret-backed pool, with safe failover and no credential exposure.
- Existing dedicated learning and memorization functionality remains available during staged migration.
