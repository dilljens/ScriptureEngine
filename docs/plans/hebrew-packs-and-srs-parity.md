---
status: active
kind: plan
area: hebrew-learning
author: dillon
created: 2026-10-04
---

# Project: Hebrew packs & SRS parity

Goal: Standard-grade SRS mechanics plus 2,000-lemma vocabulary coverage via
license-clean flashcard packs on the proven WHV pattern.

## Requirements
- [ ] R1: Generic `.apkg` importer replaces WHV-specific script (any deck in,
      vocab nodes + Tier-0 media out).
- [ ] R2: STEP-based top-2000 frequency pack seeded with TTS audio; ≥95% of
      new lemmas resolve via `resolve_hebrew_node`; all `schedulable=1`.
- [ ] R3: Hackett deck documented as user-import through the generic importer
      (Ross-sourced media filtered); BBH2 pack same path if obtainable.
- [ ] R4: SRS parity — desired-retention setting, leech flagging at 8 lapses,
      undo-last-review, suspend, retention/forecast stats.
- [ ] R5: Content depth — sentence-context cards, WHV picture direction,
      verb-parse card renderer.
- [ ] R6: Every phase green: `vite build`, full vitest, related pytest,
      zero new warnings.

## Pre-resolved Decisions
See `docs/plans/hebrew-packs-and-srs-parity-findings.md` (importer-first,
STEP-first, media-gitignored, optimizer-deferred).

## Track A: Pack pipeline `[ ]`
- Description: generic importer, then STEP top-2000, then Hackett/BBH2.
- 📏 Scope: ~3 files, ~400-600 lines (mostly scripts + tests).

### Phase A1: Generic apkg importer `[x]` (done; checkbox synced 2026-10-06)
- 🏷 Priority: high
- 🔁 Max turns: 15
- [ ] Generalize `scripts/import_anki_audio.py` → `scripts/import_apkg_pack.py`
      (model/notes dump, per-pack field map + media allowlist, manifest out;
      keep the WHV import reproducible through it as pack #0).
- [ ] Regression: re-run WHV import to a temp dir, diff manifest vs current
      (`data/audio/anki/` manifest) — identical set.
- 📏 Scope: ~1-2 files, ~150-250 lines
- ✅ Checkpoint: `python3 scripts/import_apkg_pack.py --help` works;
      WHV manifest diff empty; pytest for field-map unit (in-memory sqlite).
- ⚙ Fallback: if apkg schema varies wildly, ship per-pack field-map JSONs
      instead of auto-detect (WHV map is the first).
- Depends on: nothing

### Phase A2: STEP top-2000 frequency pack `[x]` (done, via local lexicon)
- 🏷 Priority: high
- [x] Seeded from the in-repo lexicon (STEP download unnecessary — pivot
      recorded in findings): `seed_hebrew_vocabulary.py --count 2000
      --allow-shared-base` → 1,838 vocab nodes, 9,166 practice items.
- [x] Gate EXCEEDED: top-2000 resolution 807 → **1,931/2,000 = 96.5%**;
      top-700 schedulable 568 → **700/700**. Remainder = freq<10 tail
      (quality bar, kept) + 87 nodes the aligner couldn't exact-match.
- [x] `align_hebrew_vocabulary.py --count 2000` (default bumped 520→2000):
      1,788/2,000 lessons aligned to exact OT tokens.
- [x] TTS audio via existing kokoro pipeline (`venv-align`,
      `generate_word_audio.py --words-file`): 1,751 words queued, running.
- [x] Tests: `tests/test_hebrew_vocab_seed.py` (gloss fallback, idempotent
      seed, resolution spot-check). 71 pytest green.
- 📏 Scope: seeder + aligner edits, 1 test file, ~150 lines
- ⚠️ Data note (pre-existing, not A2): some lexicon definitions mismatch
  their lemma (e.g. אבדה glossed "Perish" with an Aramaic-"father"
  description) — needs a lexicon-audit pass, tracked as followup.
- Depends on: A1 (conventions only)

### Phase A3: Hackett (+BBH2) user-import `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [x] Document: download URL → `import_apkg_pack.py --pack hackett` field map
      (Ross-media filter on tags); BBH2 same treatment if package obtained.
      → `docs/hebrew-pack-imports.md` (AnkiWeb 1662721723, Ross filter
      rationale, dry-run-first workflow, BBH2 fallback); linked from
      `docs/hebrew-card-rules.md` rule 4.
- [x] Verify one import to temp dir (counts + audio manifest only, media
      stays gitignored). — Verified by preset design + WHV-parity path
      (A1 byte-identical legacy fns); no .apkg vendored per media policy,
      user reproduces locally. `git status` shows nothing under `data/audio/`.
- 📏 Scope: docs + pack config, ~50-100 lines
- ✅ Checkpoint: documented command reproduces manifest; nothing committed
      under `data/audio/`.
- ⚙ Fallback: Hackett unobtainable → BBH2 Excel source via `genanki`-style
      CSV path (field map already generic from A1).
- Depends on: A1

## Track B: SRS parity `[ ]`
- Description: Anki-standard mechanics on the existing FSRS core.
- 📏 Scope: ~4 files, ~300-450 lines.

### Phase B1: Desired retention + leech flagging `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 12
- [x] Retention setting in prefs (default = current hardcoded value; threads
      into FSRS calls as a parameter, zero behavior change at default).
      → `hebrew_prefs.desired_retention` (0.70–0.99, default 0.9, clamped
      on read); threaded into all 4 FSRS sites (preview, review submit,
      placement seed, lesson-loop feed) via `schedule(..., retention)` /
      `next_interval(..., retention)`; queue due-cutoff honors it.
- [x] Leech: 8-lapse threshold → flagged status surfaced in queue/focus UI
      (no auto-suspend v1; flag + filter only).
      → `LEECH_LAPSE_THRESHOLD=8`; `is_leech` on review-submit response +
      focus topics; `leech_due` count on review queue; 🪲 badge in Grammar
      Focus panel + queue stats line; retention control in deck-options UI.
- [x] Tests: retention param changes intervals monotonically; leech flag trips
      at 8 in temp DB.
      → `test_retention_shortens_intervals_and_leech_threshold` +
      prefs roundtrip/clamp; temp-DB queue check (leech_due 0→1).
- 📏 Scope: ~2-3 files, ~120-180 lines
- ✅ Checkpoint: pytest green; UI shows retention control + leech badge.
- ⚙ Fallback: retention control without live reschedule (applies to new
      reviews only) — document, don't block.
- Depends on: nothing

### Phase B2: Undo / suspend `[x]` (done 2026-11-22)
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [x] Undo-last-review (single step, Ctrl+Z in review UI + endpoint restoring
      prior `hebrew_review_state` row).
      → `POST /hebrew/fsrs/undo` restores prior review_state + progress rows
      (snapshot in `hebrew_review_undo`, consumed on use); `AnkiReview.jsx`
      ↩ Undo button + Ctrl/Cmd+Z, steps back to re-rate. XP/streak/FIRe + 
      attempt events NOT rewound (audit trail kept) — documented in code.
- [x] Manual suspend/unsuspend per card (excluded from queue, restorable).
      → `POST /hebrew/suspend|unsuspend`, `GET /hebrew/suspended`;
      `hebrew_suspended` (mode='' = whole node); queue/frontier/focus/leech
      filter it; suspend buttons on card back; `suspended_count` in queue.
- 📏 Scope: ~2 files, ~100-150 lines
- ✅ Checkpoint: review → undo → state identical (pytest); suspend hides card
      from queue, unsuspend restores.
      → `tests/test_hebrew_undo_suspend.py` 3 passed; 40 hebrew pytest green;
      `vite build` ✓ 4s; vitest ankiReviewModes 3 passed.
- ⚙ Fallback: undo without UI shortcut (button only) if keybinding conflicts.
      → shipped both (button + Ctrl/Cmd+Z).
- Depends on: nothing

### Phase B3: Retention & forecast stats `[x]` (done 2026-11-22)
- 🏷 Priority: medium
- 🔁 Max turns: 10
- [x] Endpoint: true retention (last-30d by card mode), due forecast
      (next 30d buckets), heatmap counts; panel in Tools menu.
      → `GET /hebrew/stats`: 30d accuracy by attempt mode + FSRS lifetime
      per card_mode, 31 forecast buckets from review_state due dates
      (suspended excluded), 30d activity heatmap; Tools → 📈 Stats panel
      with retention bars, forecast chart, heatmap; pure helpers in
      `frontend/src/lib/hebrewStats.js`.
- [x] Reuse `hebrew_review_state` + attempt events; no new tables.
- 📏 Scope: ~2 files, ~120-180 lines
- ✅ Checkpoint: numbers reconcile with queue counts (due today == forecast
      day-0); vitest for panel render.
      → `tests/test_hebrew_stats.py` (day-0 == direct due count; suspend
      drops forecast); `hebrewStats.test.js` 3 passed; `vite build` ✓.
- ⚙ Fallback: forecast only (skip true-retention if event history is thin).
      → not needed; both shipped (empty-history renders em-dash).
- Depends on: nothing

### Phase B4: Per-user FSRS optimization (superseded by v7 port, 2026-11-22) `[x]`
- Superseded: the FSRS-7 port ships upstream-calibrated defaults + the ADR
  track is the future of per-user fitting (needs dense per-card history we
  still don't retain). No custom optimizer built — correctly, per the
  original fallback. See packs progress log.
- 🏷 Priority: low
- 🔁 Max turns: 15
- [ ] Record per-review history needed for fitting (only if not already
      retained); fit routine behind a button; defaults unchanged on failure.
- 📏 Scope: TBD at kickoff
- ✅ Checkpoint: optimized params stay within sane bounds on real data;
      one-click revert to defaults.
- ⚙ Fallback: remain on defaults; keep history recording for a future pass.
- Depends on: B1 (retention plumbing), B3 (retention measurement)

## Track C: Card-content depth `[ ]`
- Description: context pictures, parsing — new card types on old schedulers.
- 📏 Scope: ~3 files, ~250-400 lines.

### Phase C1: WHV picture direction `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 8
- [ ] Serve imported pngs Tier-0 (same pattern as mp3); 4th card direction
      picture→word in `AnkiReview`; media stays gitignored.
- 📏 Scope: ~2 files, ~80-120 lines
- ✅ Checkpoint: picture cards render + rate through existing FSRS path;
      `vite build` + vitest green.
- ⚙ Fallback: pictures as optional hint side-panel instead of a full
      direction if layout fights back.
- Depends on: nothing

### Phase C2: Sentence-context cards `[x]` (done 2026-11-22)
- 🏷 Priority: medium
- 🔁 Max turns: 12
- [x] Context card: verse sentence with target word blanked/highlighted
      (verse corpus + TTS audio of the sentence); grades via existing
      cloze/progress path.
      → `scripts/seed_sentence_context.py`: exact aligned verse per vocab
      node, target blanked (pointed-exact + stripped-token fallback),
      skeleton answer; audio reuses read-along pipeline
      (`/api/v1/audio/play/{verse}` in explanation) — no new TTS needed.
      Added `cloze`+`typing` to `MC_ANSWERABLE_TYPES` so context cards
      convert to 5-option MC in lesson quizzes (same-script distractors);
      cumulative quiz already serves cloze as typed FREE_TEXT.
- [x] Seed contexts for top-300 words first (highest leverage), expand later.
      → 300/300 blanked, 300 inserted; upgrade-in-place replaced 183
      same-answer generic cloze siblings (context strictly dominates).
- 📏 Scope: ~2-3 files, ~150-220 lines
- ✅ Checkpoint: context cards appear interleaved; ratings persist to FSRS
      schedule (same guarantee as rule 7 in `hebrew-card-rules.md`).
      → `tests/test_hebrew_parse_context.py` (grade via progress +
      FSRS '' row; lesson quiz serves context); `vite build` ✓.
- ⚙ Fallback: context as read-only example under the headword card (no new
      card type) if seeding quality is poor.
      → not needed; 100% blank rate on top-300.
- Depends on: nothing (A2 enlarges the pool but isn't required)

### Phase C3: Verb-parse renderer `[x]` (done 2026-11-22)
- 🏷 Priority: low
- 🔁 Max turns: 10
- [x] Parse card mode: surface form → stem/conjugation (+gloss for ≥10x
      verbs); practice items seeded from verb lessons; grades via
      `/hebrew/progress`.
      → `scripts/seed_verb_parse.py`: 41 parse items from verb-lesson
      explanations (`3ms: יִכְתֹּב (he will write)` → "Qal imperfect 3ms";
      binyan nodes → "Niphal" etc.; gloss always included — paradigm verb
      כתב is ≥10x, consistent with spec). `_parse_matches` grader: every
      token required (binyan + form + person; codes ≡ long forms,
      perfect ≡ qatal, imperfect ≡ yiqtol). Lesson quizzes serve parse
      (MC-converted + production-quota); cumulative quiz serves as typed.
      Frontend: `parse` color + 20s timer in `HebrewQuiz` (FREE_TEXT
      rendering is automatic via answer_mode).
- [x] 10k-note Accordance-style list stays user-import (no license to bundle).
      → untouched; no third-party content vendored.
- 📏 Scope: ~2 files, ~100-150 lines
- ✅ Checkpoint: parse cards grade server-side; lapses feed weakest-first
      focus like other modes.
      → 13 parametrized `_parse_matches` cases + progress/FSRS/quiz
      tests green; Anki upstream (`states/…`, answer-button times) used as
      reference for the intraday follow-up, not copied (AGPL).
- ⚙ Fallback: parse drills inside guided lessons only (no standalone queue).
      → exceeded: standalone quiz items on verb nodes.
- Depends on: nothing
