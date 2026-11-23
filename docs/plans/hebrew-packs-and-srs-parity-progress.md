# Progress: Hebrew packs & SRS parity

## Session 2026-10-04
- Plan created (`hebrew-packs-and-srs-parity.md` + `-findings.md`).
- ✅ Track A Phase A1 DONE: `scripts/import_anki_audio.py` →
  `scripts/import_apkg_pack.py` (git mv, legacy fns untouched) + gloss
  auto-detect, `<img>` extraction, `--pack` presets (whv/hackett/bbh2),
  `--exclude-tag/--exclude-media` (Ross-audio filter), `pack.json` output
  for seeding. 4 new tests in `tests/test_import_apkg_pack.py`; legacy
  parity test updated to new name. 68 pytest green.
- Regression note: no WHV .apkg on disk (original import came from the live
  Anki collection), so the manifest-diff gate was satisfied by (a) legacy
  `build_mapping`/`apply_import` bodies byte-identical in the rename diff,
  (b) `test_legacy_audio_only_path_unchanged` asserting the old manifest
  shape on a WHV-like fixture.
- Current track: Track A, Phase A2 DONE (see plan file); TTS synthesis
  running in background (~1,751 words). Next: A3 (Hackett doc) or B1.
- Tests: 71 pytest green (incl. 4 apkg-pack + 3 vocab-seed).
- Prior shipped state (context): WHV 686-note import, 3-way AnkiReview,
  grammar-focus, session summarizer, guided lessons, affix-strip resolution
  (568/700 top-700), vocab bands with `schedulable=1`.
- Uncommitted at plan time: `web/routes/hebrew.py` (M), `GuidedLessonView.jsx`
  (??), `hebrew_session_summary.py` (??), `test_hebrew_focus_summary.py` (??).
  Recommend `/yeet` before starting Track A.
- Tests: n/a yet for this plan.

## 2026-10-04 — B1 + A3 DONE
- B1 DONE: `hebrew_prefs.desired_retention` (0.70–0.99, default 0.9, server-clamped on read; old clients keep stored value); threaded into all 4 FSRS sites (preview/review/placement/lesson-loop) via `schedule(..., retention)`; queue due-cutoff honors it. Leech: `LEECH_LAPSE_THRESHOLD=8`, `is_leech` on submit + focus topics, `leech_due` on queue, 🪲 badge in Grammar Focus + queue stats, retention % control in deck options.
- A3 DONE: `docs/hebrew-pack-imports.md` (Hackett AnkiWeb 1662721723, Ross-audio filter rationale, dry-run-first workflow, BBH2 fallback, media policy); linked from `docs/hebrew-card-rules.md` rule 4. No .apkg vendored.
- Verification: 465 pytest green (3 skipped), `vite build` ✓ 26s. New test `test_retention_shortens_intervals_and_leech_threshold` + prefs roundtrip/clamp; temp-DB queue check leech_due 0→1.
- TTS: kokoro synthesis ~50% (~881/1751 wavs) still running in background; leave it.
- Next: C1 (WHV png picture direction) or commit batch (`/yeet`).

## 2026-10-04 — TTS complete + 87-gap recovery
- Main run done: 1,748 generated, 0 errors, 0 suspiciously-short
  (`data/audio/words/`, gitignored as per media policy).
- Spot-check (12 random wavs): valid 24 kHz, 0.85–1.32 s, peaks 0.55–0.84,
  uniform normalized RMS — real voiced audio, no silence/clipping.
- Serve path verified: `/api/v1/hebrew/audio/{word}` tiers Tier-0 anki →
  verse timestamps → alignments → letters → words (node-id match covers
  the `vocab_<surface>_<freq>` files).
- Gap audit: 87 seeded nodes had no wav (unpointed lesson `hebrew`, no
  lemma link). 6 covered by Tier-0 anki audio. Recovered 70 more by
  fold-matching surfaces to pointed OSHB tokens in `gematria`
  (most-frequent pointed form, exact corpus attestation — no guessing):
  `/tmp/opencode/tts_gap81.json` → 70/70 generated, 0 bad.
- Remaining 17 (0.9%) have no exact corpus/lexicon form (prefixed or
  suffixed edge spellings: באשר, מאז, יהרגני, צבאם …). Deliberately left
  silent — hand-composing niqqud would risk teaching wrong pronunciation.
  Future fix: Renikud diacritizer pass, not hand-pointing.
- Coverage: 1,821/1,838 nodes = 99.1% (+ Tier-0 overlaps).

## 2026-10-06 — C1 DONE (WHV picture direction)
- Data: 683 WHV pngs imported from the live collection via the tested
  `build_pack(media="images")`/`apply_pack` path (`/tmp/opencode/import_whv_images.py`;
  no WHV .apkg on disk, and Anki 26 exports a zstd layout `parse_apkg` can't
  read — live-collection parse was the honest route). `pack.json` created
  (686 entries, 683 with images); `manifest.json` hash UNCHANGED (audio-only merge).
- Backend (`web/routes/hebrew.py`): `_load_anki_pack` + `_match_anki_image`
  (exact → `_anki_fold`), Tier-0 block in `get_hebrew_image` returning
  `/api/v1/image/anki/{file}` (source `anki`); new file route in
  `web/routes/audio.py` with image media types. `card_mode` allowlists
  (intervals + review submit) accept `picture` → own FSRS rows (rule 7).
  Deliberately NOT in backend `CARD_MODES` — scheduler never auto-deals
  picture; queue surfaces due picture rows once rated.
- Frontend (`AnkiReview.jsx`): two-pass build (prefetch Tier-0 pictures,
  then deal modes via exported `modesForCard` — picture only where a png
  exists, server due_modes pass through); `picture` front (🖼️ + img);
  rating path unchanged (mode-agnostic `card_mode`).
- Docs: `hebrew-card-rules.md` rules 1/6/7 updated for the 4th direction.
- Tests: `test_picture_schedules_distinct_rows` (live isolated DB),
  `test_match_anki_image_exact_folded_and_miss` + missing-pack test,
  `ankiReviewModes.test.js` (3 vitest for `modesForCard`).
- Verification: `vite build` ✓ (~8 s), 515 vitest ✓ (16 files),
  469 pytest ✓ (3 skipped, pre-existing). Live smoke: Tier-0 resolves
  exact + folded (אלהים → אֱלֹהִים png), file exists.
- Note: `pnpm build` wrapper fails on a pre-existing env quirk
  (ERR_PNPM_IGNORED_BUILDS blocks esbuild install check); direct
  `./node_modules/.bin/vite build` works. Unrelated to C1.
- Next: B2 (undo/suspend), B3 (retention/forecast stats), C2/C3, or commit batch.

## 2026-11-22 — B2 DONE (undo / suspend)
- Backend (`web/routes/hebrew.py`): `hebrew_review_undo` snapshot table + `hebrew_suspended` table (mode='' = whole node), both in `_ensure_all_hebrew_tables` + `idx_suspended_user` added to `_SCHEMA_INDEXES` (fixes short-circuit ensure on existing DBs; also fixed hardcoded 4-placeholder IN). `process_hebrew_review` snapshots prior review_state + progress (incl. last_practiced/source; progress upsert now preserves source instead of wiping it) and fixes state tuple indices for the added due/last_rating cols.
- Endpoints: `POST /hebrew/fsrs/undo` (single-step restore, consumed on use; 404 when nothing to undo), `POST /hebrew/suspend|unsuspend`, `GET /hebrew/suspended`. Queue filters whole-node + per-mode suspends (due, legacy-estimate, frontier SQL, grammar focus, leech_due); `suspended_count` in queue response.
- Frontend (`AnkiReview.jsx`): ↩ Undo button + Ctrl/Cmd+Z (steps back to re-rate, drops undone rating), suspend-this-direction + suspend-whole-word on card back, undo status line.
- Tests: `tests/test_hebrew_undo_suspend.py` (exact-state restore, new-card undo deletes rows, suspend hides/unsuspend restores incl. compressed groups) 3 passed; 40 hebrew pytest green; `vite build` ✓ 4s; ankiReviewModes vitest 3 passed.
- Note: `test_memorize_preview.py::test_mastery_verse_ids_all_exist_in_library` fails on clean tree too (missing jsh.1.15-20) — pre-existing, unrelated.
- Next: B3 (retention/forecast stats), C2 (sentence-context), C3 (verb-parse), or commit batch.

## 2026-11-22 — B3 + C2 + C3 DONE (Track B/C complete except deferred B4)
- B3 DONE: `GET /hebrew/stats` (30d retention by mode + FSRS lifetime per direction, 31-day forecast buckets ex-suspended, 30d heatmap; no new tables) + Tools → 📈 Stats panel (`hebrewStats.js` pure helpers). Checkpoint: forecast day-0 == direct due count (25==25 live). Tests: `test_hebrew_stats.py` 2 passed, `hebrewStats.test.js` 3 passed.
- C2 DONE: `scripts/seed_sentence_context.py` → 300 top-300 vocab context cloze (100% blank rate, idempotent), audio via existing read-along `/api/v1/audio/play/{verse}`. Upgrade-in-place: 183 same-answer generic cloze siblings replaced (context dominates; lesson-quiz same-answer dedup would otherwise hide them forever; dup groups now 0). `cloze`+`typing` added to `MC_ANSWERABLE_TYPES` so context cards convert to 5-option MC in lesson quizzes; cumulative quiz serves cloze/parse as typed FREE_TEXT.
- C3 DONE: `scripts/seed_verb_parse.py` → 41 parse items across 20/21 verb nodes (binyan_intro has no forms — correctly skipped). `_parse_matches` keyword grader (binyan+form+person; codes ≡ long forms; qatal/yiqtol aliases); `parse` in PRODUCTION_TYPES/order/KP recall/cumulative list; HebrewQuiz color+timer. Tests: `test_hebrew_parse_context.py` 16 passed (13 grader params + progress/FSRS/quiz).
- Verification: 175 pytest green in scope (1 pre-existing unrelated fail: memorize_preview jsh.1.15-20, fails on clean tree), `vite build` ✓ 3.9s, 12 vitest green.
- Remaining: B4 per-user FSRS optimization (explicitly deferred — needs dense per-card review history we don't retain yet). Anki upstream cloned to /tmp/anki-upstream (AGPL, reference only) for the intraday-learning follow-up spec.

## 2026-11-22 — Content arrangement audit (curriculum spine review)
- Spine order is sound: L1 consonants (28) → L2 vowels (20) → L3 grammar/syllables (12) → L4–L7 vocab/grammar/reading/verb/root (622). Every one of 703 nodes has practice items; type mix is healthy (recall 850, MC 824, cloze 762 post-C2, typing 620, parse 41, contrast 33, transliteration 29).
- Hollow gating past L3: only 304 edges total; 551/622 L4–L7 nodes have NO incoming edge → instantly unlocked on day one. The 10/day new-card cap + backlog guardrail is the only flood control; mastery≥0.8 prerequisite rule is decorative for vocab. "Continue Learning" (level, mastery sort) guides order, but locks don't enforce it.
- Recommendation (follow-up, not this pass): level-gate the frontier — unlock L(n+1) only when L(n) average mastery ≥ 0.5 (query-time rule, no migration) — or auto-derive frequency-tier vocab edges (top-100 → next-200). Logged for the intraday plan or a tuning pass.
- Known content debts (unchanged): 17 silent words (no exact corpus form — deliberately unpointed, needs Renikud pass), lexicon gloss mismatches (e.g. אבדה/אב, pre-existing A2 note), maqqef reingest deferred (documented in overhaul progress).

## 2026-11-22 — FSRS v7 update (supersedes B4)
- Canonical core (`lib/api/fsrs.py`) ported FSRS-6 → FSRS-7 (34 weights,
  dual slow/fast stability, weighted forgetting curve, Newton+bisection
  intervals; no separate short-term branch — same-day flows through the
  fast component). New: `initial_fast_stability` (0.8×S0, upstream ratio),
  4-tuple `schedule()` (…, new_fast_stability), state-aware
  `retrievability`/`next_interval`/`next_difficulty`.
- Verified against the reference runtime: Rust harness on crates.io
  `fsrs v7.0.0` dumped 122 vectors (new/review/recall/s90) — port matches
  all 122, including the crate's own new-card doctest. Permanent pins in
  `tests/test_fsrs_v7_reference.py` (8 tests); `test_fsrs_unified.py`
  re-cut for v7 (identity + behaviors hold; v6 vectors retired).
- Persistence: `stability_fast` column on `hebrew_review_state` (backfilled
  0.8×slow, snapshotted in undo, threaded through review/preview/queue/
  stats/feed/placement-seed). memorize.py reuses the core with the 0.8
  default (no memorize-table migration — upstream's scalar convention).
- Sim re-run @ v7: 10 new/day, 0.9 → 31.4 reviews/day, retention 0.863,
  262 matured/60d; intraday adds 236 retries (+11% workload, retention
  0.839 — consolidation, not efficiency gain).
- Follow-ups logged, not taken: learn.py's private hand-rolled FSRS copy
  (third scheduler — consolidate per ADR-0001 spirit); FSRS-7 ADR
  auto-retention policy (needs dense per-card history — same blocker B4
  always had); second optimizer pass if usage grows.

## 2026-11-22 — Production coverage (Track C depth, beyond plan)
- `scripts/seed_production.py` → 55 production cards: 41 verb-form writing
  ("Write the Qal imperfect 3fs ('she will write')" → תִּכְתֹּב), 17 root
  extraction (derived forms → root, from lesson `derived_words`), 8 phrase
  production (title surface — gloss). All `typing` (typed FREE_TEXT,
  Hebrew keyboard), niqqud-insensitive grading verified exact + skeleton.
- `typing` added to the cumulative quiz item list (was MC/recall-only in
  practice: lesson mc-quizzes convert typing→MC, cumulative never served
  it — production is now genuinely typed, not just convertible).
- Coverage map + room design recorded in `docs/plans/hebrew-active-recall.md`
  (status: proposed): R1 done here; R2 grammar-application, R3 dictation,
  R4 comprehension + one-room composer, R5 mix enforcement. Speaking stays
  opted out.

## 2026-11-22 — R2 grammar-application cards (Track C depth)
- `scripts/seed_grammar_apply.py` → 16 cards, attested-only: 7 inflect
  (typing; "Example: BASE → FORM (gloss)" lines + STEM+affix compositions,
  sound-description/junk filtered, batch-deduped) + 8 breakdown (parse;
  "Parse X" worked examples on morphological nodes only — sentence-level
  restatements excluded, final full-form step never a part). Keyword grader
  requires both Hebrew parts AND gloss (half-answers fail verified).
- Tests: grade-via-progress (skeleton), parse discrimination, lesson-quiz
  serving — in `test_hebrew_parse_context.py` (18 passed).

## 2026-11-22 — R3 dictation (word level) + P1 learner profile
- R3 word level DONE: `scripts/seed_dictation.py` → 517 cards (every vocab
  node has a node-id wav; prompt carries no text, audio_url is node-id
  based so the surface never leaks). `GET /hebrew/dictation/next`
  (due '' rows + new fallback, no answer in payload — graded via
  progress). Quiz integration: `audio_url` on dictation questions +
  audio player in HebrewQuiz; cumulative IN-list, PRODUCTION_TYPES,
  order, KP_RECALL updated; mc-lesson converts to hear-and-pick (audio
  kept). Verse-level (gloss-cued target in verse audio) waits for
  word-level retention ≥ 80%.
- P1 DONE: `GET /hebrew/profile` — per-skill practiced/mastered/due,
  frontier level, 30d production ratio + retention, pacing, goal
  (`hebrew_prefs.goal`, validated choices read/vocab/parse/fluency).
  "Your Hebrew" panel in LearnView (skill bars, production %, goal pill
  or set-goal link); goal selector in deck options, saved via set_prefs.
- Tests: endpoint no-leak + grade + audio-carry (parse_context file),
  profile shape + goal roundtrip/reject (stats file). 521 pytest green.
