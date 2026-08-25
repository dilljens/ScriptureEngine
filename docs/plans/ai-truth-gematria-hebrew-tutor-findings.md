# Findings: Truth-Seeking Chat, Hebrew Tutor, and Memorization

## User decisions

- Remove all learner/quiz progress from general Scripture chat.
- Keep Atbash and notarikon, but prevent the LLM from treating gematria as stronger than the evidence supports.
- Use a dedicated Hebrew learning chat/mode, optimized as a long-term tutor with indexed progress and prior Hebrew conversations.
- Add finishing the memorization modes to the plan.
- Fix Hebrew quiz feedback: the UI can currently say both correct and wrong even when the learner answered correctly.
- Run truth-verification and native OpenCode Go provider work in parallel; both general chat and Hebrew Tutor may use the approved model.

## Existing architecture

### Chat

- `web/routes/chat.py` loads `CHAT_AGENTS.md`, `CHAT_AGENTS_HEBREW.md`, and `CHAT_AGENTS_KNOWLEDGE.md` by mode.
- `ChatRequest.mode` already supports `chat`, `hebrew`, and `knowledge`.
- General chat currently exposes quiz, assessment, diagnostic, Hebrew progress, and Hebrew lesson tools alongside Scripture tools.
- `CHAT_AGENTS.md` contains quiz-card instructions and user-progress guidance that must be removed from general chat.
- `CHAT_AGENTS_HEBREW.md` is the natural home for a dedicated tutor contract.

### Native OpenCode Go and secret pool

- `ai-secret list` confirms four healthy credentials: `opencode-go-1`, `opencode-go-2`, `opencode-go-3`, and `opencode-go-4`. Their registry scopes identify separate OpenCode Go workspaces/rate limits. Values were not read or exposed.
- The local OpenCode balancer reports four accounts and aliases (`default`, `opencode-go-3`, `quaternary`, `space2`). It is a plugin/TUI server hook that injects credentials into OpenCode's own provider requests; it is not an HTTP API that ScriptureEngine can safely call as a proxy.
- The native Go route is distinct from OpenRouter: local machine probe templates use `https://opencode.ai/zen/go/v1/chat/completions` with an OpenCode API key. The plan must not introduce an OpenRouter dependency or read `~/.config/opencode/balancer.sqlite`.
- `ai-secret exec <name>` is the safe injection primitive. A four-worker pool, with one worker launched per secret and a protected local IPC boundary, keeps raw keys out of the web process and permits rotation/failover without copying values into `.env` or code.
- Requested model name must be preflight-validated against the native provider. The implementation must not assume that a Zen/OpenRouter model suffix or catalog id is valid for OpenCode Go.

### Hebrew learning state

- `memorize.db` contains `hebrew_progress`, `hebrew_review_state`, `hebrew_gamification`, and lesson/practice data.
- Existing progress rows are user- and node-scoped (`user_id`, `node_id`) and should remain the source for current mastery compatibility.
- `web/routes/hebrew.py` contains FSRS scheduling helpers and multiple progress/review routes. The plan must reconcile these paths rather than create another scheduler.
- The tutor needs a compact, deterministic progress snapshot rather than wholesale database or transcript injection.

### Quiz bug evidence

- `web/routes/hebrew.py` returns quiz answers as string data (`correct_answer`), while `frontend/src/components/HebrewQuizCard.jsx` and `frontend/src/components/QuizCard.jsx` contain index-based grading assumptions.
- `frontend/src/components/HebrewQuiz.jsx` and `HebrewLessonView.jsx` normalize/compare answers differently from `HebrewQuizCard.jsx`.
- `CardRenderer.jsx` can intentionally paint the stored correct option green and a different selected option red; with mismatched answer representations this can look like simultaneous correct/wrong feedback.
- `/api/v1/hebrew/progress` trusts a client-supplied boolean, so stored progress can disagree with displayed grading.
- Existing tests cover basic practice grading and payload shape but not string-vs-index answers, accepted Hebrew variants, or mutually exclusive feedback.

## Gematria evidence model

The core problem is not that numerical methods exist; it is that raw numerical scores and graph paths can be mistaken for semantic proof. The implementation should make the evidence class explicit and enforce a ceiling after calibration multipliers.

### Retain, with bounds

1. Exact standard/Mispar Hechrachi word-value matches when both Hebrew words are attested.
2. Exact ordinal/Mispar Siduri matches when the method is stated and context supports surfacing it.
3. Reduced/Mispar Katan only for anchored comparisons; do not create broad nine-value buckets.
4. Exact divine-name values with the name, spelling, system, and value displayed.
5. Atbash and notarikon as explicit hidden/Sod transformations with the input, transformation, output, and confidence shown.

### Neutralize or retire

- Broad sacred-number/factor matches.
- Arbitrary `a + b = c` gematria sums.
- Whole-verse total significance without a preregistered interpretive reason.
- Substring/skip-letter scans that search until a desired value appears.

The initial deployment should neutralize and stop new generation, capture counts, and only then archive/purge old rows. This preserves rollback and makes the intentional graph change measurable.

## Recommended Hebrew learner-state model

The tutor should use multiple layers rather than one global “Hebrew level”:

```text
hebrew_attempt_events
  id, user_id, skill_ids, item_ids, mode, task_type
  response/transcript_ref, rubric_result, error_tags
  hint_level, created_at, content_version, evaluator_version

hebrew_skill_state
  user_id, skill_id, mastery_estimate, uncertainty, evidence_count
  last_evidence_at, common_errors, goal_relevance, state_version

hebrew_review_state
  user_id, item_id/node_id, fsrs_state, due_at, stability, difficulty
  fsrs_version, last_review_event_id

hebrew_tutor_memory
  id, user_id, scope, content, source_event_id, confidence
  created_at, updated_at, expires_at, supersedes_id
```

The existing tables can be retained as compatibility/materialized projections while the event and skill tables are introduced. An updater must be deterministic and versioned. The LLM may classify an answer or propose an error tag, but it must not directly set mastery or intervals.

## Long-term tutor memory rules

1. Working context: current turn and a small recent window.
2. Session memory: a concise summary and unresolved learning goals.
3. Durable learner profile: explicit goals/preferences only.
4. Pedagogical state: skills, errors, item history, due reviews.
5. Raw transcript archive: searchable/auditable, never injected wholesale.

Retrieval must filter by `user_id` and `mode=hebrew`; general chat must not receive Hebrew tutor memories. Candidate memories should be staged, deduplicated, conflict-resolved, superseded, and forgettable. A vector/FTS index may improve recall, but structured progress remains authoritative.

## Online research notes

Research supports the following design choices:

- ACTFL Proficiency Guidelines 2024 and NCSSFL-ACTFL Can-Do Statements: model skills and modes separately and require repeated evidence, not one success.
  - https://www.actfl.org/proficiency-guidelines-overview
  - https://www.actfl.org/educator-resources/ncssfl-actfl-can-do-statements
- CEFR Companion Volume 2020: learner ability is multidimensional across activities and competences.
  - https://rm.coe.int/cefr-companion-volume-with-new-descriptors-2020/16809ea0d4
- FSRS official project and Anki documentation: item scheduling should be separate from proficiency; review ratings must reflect recall quality and the scheduler version should be recorded.
  - https://github.com/open-spaced-repetition/free-spaced-repetition-scheduler
  - https://docs.ankiweb.net/deck-options.html#fsrs
- Duolingo HLR research: language items should distinguish lemmas, surface forms, part of speech, and morphology rather than treating every string as one item.
  - https://aclanthology.org/P16-1174/
- OpenAI context personalization/conversation-state guidance: separate structured state from narrative memory, stage and consolidate notes, resolve conflicts, and retrieve only relevant slices.
  - https://developers.openai.com/cookbook/examples/agents_sdk/context_personalization
  - https://platform.openai.com/docs/guides/conversation-state
- LoCoMo: long-term memory should be evaluated for temporal recall, changed facts, contradictions, and evidence—not just retrieval hit rate.
  - https://arxiv.org/abs/2402.17753

These sources do not define a single Biblical Hebrew tutor schema. They support the boundaries and evaluation strategy; the project-specific tables still need to be designed against the existing database and routes.

## Truth-seeking research notes

- TruthfulQA (Lin et al., 2021) shows that scaling alone does not maximize truthfulness and that models can imitate popular falsehoods. Build adversarial Scripture cases rather than optimizing fluency.
  - https://arxiv.org/abs/2109.07958
- Lilian Weng's hallucination survey summarizes retrieval grounding, abstention, Chain-of-Verification, FActScore, and self-evaluation signals. The key product implication is to abstain when evidence is absent instead of guessing.
  - https://lilianweng.github.io/posts/2024-07-07-hallucination/
- ALCE, Self-RAG, and VeriCite support claim-level citation and entailment checking; a relevant source is not necessarily a supporting source.
  - https://arxiv.org/abs/2310.11511
  - https://arxiv.org/abs/2510.11394
- Constitutional AI supports an inspectable principle set plus critique/revision. For this project the constitution should prioritize honest uncertainty, text-first evidence, non-sycophancy, and user-verifiable source spans.
  - https://arxiv.org/abs/2212.08073
- Kadavath et al. describe `P(True)`/`P(IK)` calibration signals; verbal confidence should be tied to evidence class and evaluated with calibration error, not treated as a decorative percentage.
  - https://arxiv.org/abs/2207.05221

The combined recommendation is a grounded pipeline: retrieve versioned Scripture → draft → split atomic claims → verify claim/citation entailment → revise or abstain → show evidence class and confidence. Prompt rules alone should not be considered sufficient.

## Open decisions for implementation

- Choose canonical quiz answer representation: `correct_index` for choice cards plus `accepted_answers` for free text is preferred over one overloaded field.
- Decide whether old numerical connections are archived in a separate table or marked retired in place before deletion.
- Confirm whether the Hebrew Tutor tab lives inside `HebrewLearnView` first, with a later global mode toggle, or both at launch.
- Confirm which backend becomes the single memorization scheduler after the compatibility period (recommended: Go FSRS for scripture memorization; preserve Hebrew API adapters until parity).
- Confirm the exact native OpenCode Go model/catalog id for Muse Spark Contributor with a provider preflight; do not assume OpenRouter or Zen naming.
- Choose the local worker IPC mechanism and process supervisor integration. Recommended: one `ai-secret exec` worker per workspace, protected Unix socket, pooled by a small provider adapter.
