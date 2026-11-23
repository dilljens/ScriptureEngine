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

## 2026-11-22 — Student-eye review fixes + R4a comprehension + Room composer
- Student walkthrough verdict: lesson quizzes served 2 recognition taps for
  5-question lessons (same-answer dedup kept easiest-per-answer, deleting all
  production); first word was את (untranslatable particle); reader "known"
  disagreed with SRS mastery (two known-systems).
- Fixes: dedup is now per (answer, recognition-vs-production) with DAY
  ROTATION among same-answer production items (stable within day, varied
  across days); 18-word concrete starter set (Genesis-core, all with
  items+audio) leads the L4 frontier; coverage endpoint returns
  known_folded and PassageReader colors from FSRS mastery first (local
  marks fallback) — one "known" everywhere.
- R4a DONE: `scripts/seed_comprehension.py` → 492 verse-presence T/F
  ("The word X ('gloss') appears in gen.1.1", foil verified absent;
  ambiguous gloss-frame fixed to presence-frame). true_false kept binary
  in mc transform (never padded to 5); cumulative serves as 2-option
  choice. Full meaning-judgment stays deferred (needs hand review).
- R4b composer DONE: `GET /hebrew/daily-session` (due interleaved + new
  to cap + verse block = most-represented due verse with text + audio)
  and `HebrewRoom.jsx` (verse block + due review + new words through the
  existing GameReviewModal; Room entry first in Practice dropdown).
- Tests: rotation stability, starter-first frontier, known_folded merge
  path, comprehension grade both ways + 2-option serving, composer shape
  (textless block omitted, not shipped empty). 517+ pytest green.

## 2026-11-22 — Student-eye audit fixes + R4 (comprehension + composer + Room)
- Audit as a student found: (1) lesson quizzes served 2 recognition taps
  for 5-question lessons — same-answer dedup kept easiest-per-answer,
  deleting all production; (2) first vocab word was את (untranslatable
  particle); (3) reader "known" (learn-modules/localStorage) disagreed
  with SRS mastery. All fixed, all with regression tests.
- Fix 1: quiz dedup is now per (answer, recognition-vs-production) with
  DAY ROTATION among same-answer production items (stable within day,
  varied across days; lesson quizzes serve MC + rotating production).
- Fix 2: 18-word concrete starter set (Genesis-core nouns + 2 verbs +
  adjectives, all with items + audio) leads the L4 frontier; level gate
  and prereqs unchanged. Fresh users meet אלהים, not את.
- Fix 3: coverage endpoint returns known_folded; PassageReader colors
  from FSRS mastery first, local marks as fallback — one "known".
- Hardening found en route: starter reorder shifted new-card inflow and
  exposed that "strict" non-interference was best-effort at drain.
  Interleaver is now most-constrained-first (force-emit stranded pairs
  while buffers exist) + 3-pick mate bans, deterministic tie-breaks
  (hash-seed nondeterminism fixed — verified across PYTHONHASHSEEDs).
  Pure regression test for the drain shape added.
- R4a DONE: `scripts/seed_comprehension.py` → 492 verse-presence T/F
  ("The word X ('gloss') appears in gen.N." — foil verified absent from
  folded verse tokens; prompt reframed from ambiguous gloss wording).
  true_false kept binary in mc transform, served in cumulative; meaning
  judgments deferred (need hand review).
- R4b DONE: `GET /hebrew/daily-session` (due interleaved + new to cap +
  verse block = most-represented due verse with text + audio; textless
  verse block omitted, not shipped) + `HebrewRoom.jsx` (verse block with
  player, due review + new words through GameReviewModal; Room entry
  first in Practice dropdown).
- Verification: 526 pytest green, 10 vitest, vite build clean (only
  excluded failure is the pre-existing unrelated memorize_preview gap).

## 2026-11-22 — Content sufficiency pass + R5 mix enforcement
- Audit: 20 thin nodes (0-2 items). Verdict: 9 topical reading nodes +
  binyan/weqatal/furtive/root-extract are concept lessons (1-3 checks is
  correct density, left alone). Real gaps: 7 prefix lessons (2 items each)
  and read_zec8 (2 items, seeder skipped it on a book-id bug: description
  said zec.8, corpus uses zech — fixed, plus repaired 2 stale answers it
  left behind: verse-count 0→23, ref zec.8.1→zech.8.1).
- `scripts/seed_prefix_apply.py` → 14 corpus-attested inflection cards
  (בכל/ביום/בארץ/ביד/לכל/המלך/הארץ/מכל/מארץ/מבית/ככל/כיום/כדבר/לאמר).
  Guards that survived reviewer eyeball of every item: Tanakh-only books
  (DSS layer excluded — caught מימ), lexicon-headword exclusion
  (lexicalized forms aren't compositional), skeleton dedup across
  cantillation variants, pointed answers with free-text grading.
  Deliberate exclusions: vav (conversive), shin (relative), miqtal-trap
  denylist (מזבח — own lexeme, caught by hand, documented in seeder).
- R5 DONE: lesson quota 1/3 → 40% (ceil); cumulative gets a production-first
  40% floor pass (category-alternating) before the rest interleaves; both
  quiz responses carry auditable `mix` (production/total/rate); composer
  inherits it through GameReviewModal. Verified: qal_perfect 62%,
  cumulative 38% (pool-limited best effort).
- Meaning comprehension v1: 10 hand-verified Genesis 1 claims on read_gen1
  ([hand-verified] marker, both directions grade correctly). Beyond-Gen-1
  meaning judgments still need hand review — the auto path stays at
  verse-presence.
- Verification: 528 pytest green, 10 vitest, vite build clean (only
  excluded failure is the pre-existing unrelated memorize_preview gap).

## 2026-11-22 — UI review pass (as a student, end to end)
- Walked the whole learner path: diagnostic → lessons → quizzes → review
  → reader → stats → Room. Design verdict: the learning loop is sound;
  found 1 soft-lock, 2 dead-ends-by-omission, and a tray of papercuts.
- P0 fixed: adaptive diagnostic served parse/contrast items with no way to
  answer (no options + not text-input) — now falls back to text input, and
  parse grades by keywords server-side (was strict-match-or-nothing).
- P1 fixed: suspend had no undo/unsuspend path (cards vanished with no way
  back) — one-tap Undo suspend toast; hearing cards had no replay (autoplay
  once, then silence) — replay buttons front + back.
- P2 fixed: diagnostic showed ✓/✗ with no correction (the review doc's #1
  fix, missing here) — correct answer + explanation on misses, longer dwell
  on wrong (backend now returns correct_answer); GameReviewModal got
  Escape-to-close, disclosed mode-reset behavior, working Study links;
  HebrewRoom got an error state and flattened new-card picking.
- Polish: dictation color + 20s timer, HebrewKeyboard backspace wired in
  quiz + diagnostic, guided-lesson example audio buttons (pronunciation in
  context, silent when no audio), action-row wraps on small phones,
  WordPopup dialog semantics.
- Verification: 531 pytest (incl. new placement-answerability contract +
  adaptive parse-grading tests), 522 vitest, vite build clean.

## 2026-11-22 — Goal-relative pacing strip (Anki daily-goals parity)
- Queue now reports `reviews_done_today` + `new_introduced_today` (distinct
  cards from the append-only history; first row of the day decides
  introduced-vs-reviewed, matching Anki's new-budget accounting; undo
  deletes rows so counts are net). Strip reads
  "N due · M new · ✅ K done · 🔴 learning" — progress, not just backlog.
- Fixed en route: (1) history INSERT omitted reviewed_at so SQLite filled
  a UTC default while the app runs local — now passed explicitly from the
  review's own timestamp; (2) counts computed after conn.close() (always
  zero) — moved before close; (3) a test INSERT missing the card_mode
  value shifted every column. Deliberately unchanged: 4am rollover
  (calendar day is fine), 10/100 caps (sim-verified workload).
- Verification: new undo-aware counts test; 532 pytest, 522 vitest, build.
