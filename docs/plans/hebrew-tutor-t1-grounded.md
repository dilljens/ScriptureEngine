---
status: proposed
kind: plan
area: hebrew-tutor
author: opencode
created: 2026-11-25
parent: language-learning-system
---

# T1 — Grounded Socratic tutor: conversation mode + logged correction

## Why this, why now

The expert evaluation (docs/hebrew-expert-evaluation.md) finds the bank
strong enough to teach from *without inventing content*. That makes a
grounded tutor possible: every tutor move cites a lesson, verse, or item
that already exists. The research case (LLM tutoring ≈ Bloom's 2σ, but
only when it quizzes and corrects rather than lectures) sets the protocol:
production-first, correction-logged, retrieval-enforcing.

## Non-negotiables (from the one-scheduler + corpus-grounded rules)

1. **No invented facts.** Every claim the tutor makes carries a citation:
   `{node_id}` for rule statements, `{verse_ref}` for textual claims.
   Anything without a citation is phrased as a question, not a statement.
2. **Every correction is an attempt event.** A tutor-marked error writes
   the same row a quiz answer would (`question_id` of the nearest matching
   item when one exists, else a `tutor_drill` event with the cited node),
   so FSRS sees it. Tutoring that doesn't schedule is entertainment.
3. **Production-first sessions.** The tutor *asks* (parse this, dictate
   that, explain this verse's syntax), then corrects. Explanation follows
   attempted production, never precedes it — generation effect before
   instruction, enforced by the turn template, not by hope.
4. **Correction = recast + explicit note** (Long). First mirror the
   correct form naturally, then state the rule in one line with its
   citation. Both land in the transcript; the rule lands in tutor_memory.

## The turn template (server-enforced shape, not prompt vibes)

Each tutor turn returns exactly one of:

- `ask` — a production prompt grounded in one node/verse, with the
  expected answer held server-side (same shape as a quiz question;
  reuses `_practice_to_quiz_question` server-side where possible).
- `correct` — recast + one-line rule + citation + the logged attempt.
- `explain` — ≤120 words, only after attempted production or on explicit
  "explain" request, every claim cited.
- `done` — session summary: what was produced, what was corrected,
  which nodes moved, what's due next (reads the queue, doesn't invent).

The template is validated server-side (unknown shapes rejected), so a
misbehaving model degrades to silence, never to uncited lecturing.

## Session flow (orchestrates the bank, per the expert eval)

1. Open from the Room or profile: pick the learner's weakest live area
   (grammar-focus topics, leech list, due queue) — never a random lesson.
2. Production rounds, highest-value first:
   a. **Aspect judgment** on a due verb (expert finding 2): "this qatal —
      past, present, or gnomic? why?" (new `discourse_function` items
      feed this; until then, tutor asks from lesson content).
   b. **Syntax parse** of the session verse (finding 4): "find the verb /
      bracket the construct chain."
   c. **Wayyiqtol spot-checks** once the L3 recognition node lands.
   d. **Theological-gloss rotation** (finding 3): demand the non-default
      gloss ("host", not "army") with the verse citation.
3. Close with the summary + what the scheduler now says is due.

## Backend work

- `POST /api/v1/hebrew/tutor/turn` — takes `{session_key, mode}`,
  returns the templated turn. Wraps the existing ProviderRouter +
  tutor_memory hydration; adds the citation requirement to the system
  prompt AND a response validator (cite-or-question rule).
- Attempt-event writer for tutor corrections (reuses `_record_attempt_event`
  path with `source='tutor'` + cited node; no new table).
- Session summary already exists (`session-summary` endpoint) — extend
  with tutor-turn counts, not a new endpoint.
- Tests: template validation (reject uncited statements, accept cited),
  correction writes an attempt event, FSRS row moves, fallback to
  curriculum drills when the LLM is unreachable (existing fallback
  pattern in guided-lesson).

## Frontend work

- Conversation surface inside the Room (not a twelfth door): turn list,
  Hebrew keyboard on production turns, audio playback on verse turns,
  citation chips that deep-link to lesson/verse.
- "Forget this" UI for tutor_memory (shipped backend, still no button —
  carried over from P2-A).

## Anti-scope

- No free-chat tutor mode (uncited lecturing is the failure mode).
- No voice I/O in v1 (typed Hebrew + TTS playback is enough).
- No new scheduler, no new tables (attempt events + tutor_memory cover it).
- Verse-level dictation and syntax_parse items are separate content tracks
  (R3-verse, expert finding 4); the tutor consumes them, doesn't block on them.

## Acceptance

- A full session runs with the LLM provider disabled (fallback path) and
  still schedules correctly.
- Every tutor statement in a 20-turn probe session carries a citation;
  audit via transcript.
- Corrections appear in attempt history and move FSRS rows (test).
- Expert-eval gaps 1–4 each have at least one tutor turn type addressing them.
