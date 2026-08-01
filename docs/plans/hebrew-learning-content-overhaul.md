---
status: active
kind: plan
area: hebrew-learning
author: agent
created: 2026-07-31
---

# Biblical Hebrew learning content overhaul

Goal: help learners read the pointed Hebrew Bible accurately through verified
content, objective practice, staged reading, and transparent source provenance.

## Requirements

- [x] Audit all Hebrew lesson, practice, progression, reading, and UI systems.
- [x] Research authoritative Biblical Hebrew, corpus, licensing, and pedagogy sources.
- [x] Correct the audited foundational factual errors and broken practice paths.
- [x] Validate generated content and isolate unverified examples.
- [x] Make lesson and diagnostic mastery depend on graded evidence rather than self-report or category inference.
- [ ] Add missing Masoretic reading and Biblical Hebrew discourse topics.

## Pre-resolved decisions

- Corpus: prefer OSHB/WLC public-domain text and CC BY 4.0 morphology; use STEP
  data where helpful. Treat BHSA/SHEBANQ as noncommercial unless permission is obtained.
- Content: write original explanations with citations; do not copy modern grammars.
- Pedagogy: use a balanced progression of comprehensible reading, concise explicit
  instruction, retrieval practice, spacing, and interleaving.
- Scope: repair correctness before adding more generated lessons or dependencies.

## Track A: Content correctness `[~]`

### Phase A1: Foundational corrections `[x]`
- [x] Correct script, syllable, root, construct-chain, suffix, verb, numeral, and verse-reference errors.
- [x] Clearly label prototypes and interpretations instead of presenting them as universal facts.
- [x] Add a deterministic content validator.
- Checkpoint: validator passes against seed content and the learning database.

### Phase A2: Missing reading topics `[x]`
- [x] Add dagesh lene/forte, mappiq, furtive patah, maqqef, stress, and accents.
- [x] Add ketiv/qere and consonantal-text versus Masoretic-pointing awareness.
- [x] Add weak-verb, discourse, poetic, legal, and prophetic reading units.
- [x] Add Biblical Aramaic boundary awareness and label Hebrew versus Aramaic data.
- Checkpoint: each topic has an explanation, authentic OT example, and graded retrieval item.

## Track B: Learning flow `[~]`

### Phase B1: Repair learner-facing flows `[x]`
- [x] Fix review-card construction, vocabulary/audio response handling, quiz completion,
  timer scoring, Hebrew keyboard input, and reading references.
- [x] Keep Hebrew and English verse text in separate fields.
- Checkpoint: targeted frontend tests and Hebrew Playwright flow pass.

### Phase B2: Evidence-based progression `[x]`
- [x] Standardize prerequisite-edge direction and remove dangling edges.
- [x] Replace category-wide diagnostic mastery with atomic, server-graded node evidence.
- [x] Persist review state (hebrew_review_state) under an honestly labeled adaptive scheduler.
- [x] Assess normal lesson answers objectively before accepting a confidence rating.
- Checkpoint: graph invariant, diagnostic, review, and mastery tests pass on an isolated DB.

## Track C: Data provenance and quality `[x]`

### Phase C1: Corpus-safe vocabulary `[x]`
- [x] Restrict examples to exact OT tokens/lemmas rather than substring matches or DSS text.
- [x] Store source, version, license, lemma, and confidence per generated datum.
- [x] Quarantine non-OT examples and remove invalid, duplicated, contradictory, or non-OT practice.
- [x] Correct the five Aramaic lexemes' citation forms, glosses, descriptions, and practice.
- Checkpoint: foreign-key, provenance, exact-token, and practice-item audits pass.

## Acceptance criteria

- No known foundational linguistic errors remain in shipped seed lessons.
- All visible practice accepts an answer and records objective correctness.
- Reading lessons open valid verse-level morphology data.
- Hebrew text remains logical-order Unicode with RTL/language markup.
- Tests do not mutate the production learning database.
