---
status: proposed
kind: plan
area: hebrew-learning
author: opencode
created: 2026-11-22
---

# Full language learning system: master plan

Subsumes `hebrew-active-recall.md` (R2–R5 live on as §6 tracks) and links
the completed tracks (packs/parity, intraday, v7, history). This document
is the map; the phase plans stay the work orders.

## 1. What the research says (and what we stole from git repos)

### 1a. Second-language acquisition: the load-bearing findings

- **Krashen — input hypothesis (i+1).** Acquisition comes from
  comprehensible input slightly above level; the affective filter (anxiety,
  boredom) blocks it. Governs: graded reading, known-word tracking, the
  level gate (frustration is a filter-raiser).
- **Swain — output hypothesis.** Production forces noticing (what you
  can't say), hypothesis testing, and metalinguistic reflection. Governs:
  every production card shipped (R1) and the ≥40% production quota — output
  is not "harder input," it is a different mechanism.
- **Long — interaction hypothesis.** Negotiation of meaning (clarification
  requests, recasts) drives acquisition. Governs: the tutor's correction
  behavior and the planned conversation mode (recast + explicit note).
- **Nation — four strands.** A balanced course gives roughly equal time to:
  (1) meaning-focused input, (2) meaning-focused output, (3) language-focused
  learning, (4) fluency development. Governs the whole architecture: our
  bank is ~80% strand 3, some strand 1, little strand 2, no strand 4.
  The plan below is mostly "build strands 2 and 4 without breaking 1."
- **Nation/Laufer — coverage thresholds.** ~95% known-word coverage for
  assisted reading, ~98% for unassisted. Governs: frequency-tier vocab
  (top-2000 ≈ 90% running-text coverage), known-word %, milestone
  definitions ("read Genesis 1 with <2 lookups" ≈ 98% of its tokens).
- **Laufer & Hulstijn — involvement load.** Retention follows task-induced
  involvement: need + search + evaluation. Mining a word you met while
  reading (need: you, search: you looked it up, evaluation: you chose it)
  beats being handed the same word. Governs: tap-to-mine as the primary
  intake path, not a footnote.
- **Repo's own six** (`docs/learning-review.md` — Bjork desirable
  difficulties, Roediger/Karpicke testing effect, Rohrer/Taylor
  interleaving, Habgood/Ainsworth intrinsic integration, Settles/Meeder
  half-life → FSRS, Mogavi gamification misuse). Unchanged; the room and
  mix-enforcement are their enforcement layer.

### 1b. What open-source repos taught (read, not copied — licenses respected)

| Repo (stars, license) | Idea to take |
|---|---|
| `mengxi-ream/read-frog` (10.5k, GPL-3) — immersive translate + save-words-to-FSRS | **Mine-the-wild loop**: input you care about → tap unknown → SRS. Our corpus equivalent: passage reader → WordPopup → add-word-to-queue endpoint (already exists server-side). |
| `artcc/freelingo` (306, AGPL-3) — A1–C2 CEFR plans, placement → 4/8/12/16-week plan, units with competencies + prerequisites, AI lessons across grammar/vocab/comprehension/writing, voice tutor with memories, SM-2 cards, phrasebook, skill scores, end-of-level tests, per-language plans | **Independent confirmation of the architecture**: plan → units → tutor → measure, per language. We keep FSRS-7 instead of SM-2 and corpus-grounded lessons instead of pure AI generation. |
| `lingkuma/LingKuma` (127, MIT) — LingQ-style: highlight/translate/analyse/listen, import own content, word explosion | **Known-word tracking + import**: % known per chapter as the readability dial; learner-imported text as input. Our `known_words` count in chat context is the seed. |
| `kantord/LibreLingo` (2.6k) — community courses-as-data (skills → challenge types) | **Content is data**: our `hebrew_practice_items` (10+ types, FSRS rows, provenance) is the same idea with a scheduler attached. Format stays internal; no vendoring. |
| `ankitects/anki` (AGPL-3, `/tmp/anki-upstream`) + `open-spaced-repetition/fsrs-rs` v7 | Scheduler substrate only: queues, learn-ahead, undo, FSRS-7 reference. Already absorbed. |

## 2. Target architecture (what "full system" means here)

One learner, one bank, one scheduler, five loops:

```
 profil(e) ──► composer ──► session ──► scheduler ──► analytics ──► profile
   ▲                          │  │  │                                │
   │              input ───────┘  │  └─────── strands 1+4            │
   │              retrieve ──────┘  └──────── strands 3 (+moves)     │
   │              produce ─────────────────── strands 2             │
   └────────────── tutor (memory, correction, conversation) ────────┘
```

- **Learner profile** (new): skill levels per strand, goals, pace, production
  ratio, fluency baselines. Computed from existing tables first; driving
  later. This is the only genuinely new data object.
- **Content bank** (built): nodes + lessons + 10 practice types + media +
  provenance. R2–R4 extend it; nothing in it changes shape.
- **Session composer / Room** (active-recall R4): due interleaved across all
  modes + new cards to cap + authentic verse block; mix enforcement (R5).
- **Scheduler** (done): FSRS-7 canonical, intraday steps, learn-ahead,
  undo/suspend, history log (ADR substrate).
- **Analytics** (mostly built): retention, forecast, heatmap, session
  summaries; add production-ratio + fluency curves (R5).
- **Tutor** (exists, extend): Hebrew teacher mode + memory; add conversation
  mode with recast-then-note correction logged as attempt events.
- **Pipelines in** (half-built): tap-to-mine (endpoint exists, wire the
  reader button), learner text import (LingKuma-style; parse → known-% →
  mine list), TTS/alignments (done).
- **Milestones** (new, cheap): predicates over stored data
  ("Genesis 1 <2 lookups", "any Qal verb parsed", "10 verses dictated @90%").

## 3. Gap analysis (concrete, file-referenced)

1. No `learner_state` object — levels live in five tables that never meet.
2. Twelve doors, no room (`HebrewLearnView` dropdowns; active-recall R4).
3. Strand 2/4 coverage: R2 grammar-application, R3 dictation, R4
   comprehension, fluency timing — all specced, none built.
4. Mining loop unwired: add-word endpoint exists (`hebrew.py:3114`), reader
   button + known-% dial don't.
5. No milestones; progress is mastery numbers without meaning.
6. Tutor has no conversation mode with logged correction.
7. Greek: LXX pipeline exists, no Greek spine (`hebrew_nodes` is
   Hebrew-only in practice).
8. Third scheduler copy in `learn.py` (hand-rolled FSRS-5-era) — consolidate
   or quarantine per the one-scheduler rule.
9. ADR auto-tuning blocked on history depth — now unblocked structurally
   (`hebrew_review_history` flows), waiting on months of reviews.

## 4. Build order (dependency-sorted, each shippable)

| # | Work | Depends | Size |
|---|---|---|---|
| R1 | Production seeders + typed cumulative (done) | — | done |
| R2 | Grammar-application seeder | bank | S |
| R3 | Dictation (word → verse) + UI audio prompt | alignments (done) | M |
| R4a | Comprehension seeder (verse-claim T/F) | corpus | S |
| R4b | Room composer + view (reuses all renderers) | R2–R4a | M |
| P1 | `learner_state` (computed, displayed) | analytics (done) | S |
| M1 | Tap-to-mine wiring + known-% dial | reader, endpoint (done) | S–M |
| M2 | Milestones (predicates + UI) | P1 | S |
| T1 | Tutor conversation mode + logged correction | tutor memory (done) | M |
| G1 | Greek spine (letters → reading) on same rails | LXX pipeline | L |
| F1 | Fluency timing (read-along wpm, dictation curves) | R3, R4b | S |
| R5 | Mix enforcement + production-ratio analytics | R4b | S |
| A1 | ADR evaluation (needs history depth) | history (done, filling) | L |
| X1 | learn.py scheduler consolidation | decision | S |

## 5. Principles (carried forward, non-negotiable)

- One scheduler (ADR-0001): everything rates through FSRS paths; no second
  scheduler, no scheduler forks per surface.
- Corpus-grounded facts: no LLM-invented paradigms, glosses, or verses;
  seeders parse lesson/corpus content (the parse-seeder discipline).
- License-clean: scripts + manifests in repo, media gitignored; upstream
  code (Anki AGPL, Read Frog GPL, FreeLingo AGPL) read for design, never
  vendored or pasted.
- Script-first, idempotent seeders; append-only evidence
  (`hebrew_attempt_events`, `hebrew_review_history`); undo restores
  schedule, never history-of-record semantics.
- Enforcement over availability: mix quotas, level gates, re-ask — a bank
  of good cards with unenforced presentation is the documented failure mode.
