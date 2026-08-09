# Progress: Hebrew Content Follow-ups

Plan: `docs/plans/hebrew-content-followups.md` · Parent: `docs/plans/hebrew-learning-content-overhaul.md`
Closes the three follow-ups: Maqqef reingestion, frontend session wiring, last
top-frequency vocabulary seeding.

## Session 2026-08-06 (Maqqef — Track A)

**Finding: the current source text does NOT contain maqqef; restoration
requires a reingest.** The live `gematria` table has 0 U+05BE tokens across
392,256 rows (only a stray DSS line has a similar glyph); `verses.text_hebrew`
has 1/30,868. Root cause found in the pinned source itself: morphHB OSIS XML
stores maqqef as `<seg type="x-maqqef">־</seg>` elements *between* `<w>`
tokens, and the existing `parse_morphhb_xml` only read `<w>` children — so the
maqqef was silently dropped at ingest.

**Pinned source secured (not a gap):** `data/raw/morphhb/wlc/*.xml` is a copy
of OpenScriptures/morphhb at commit `3d15126fb1ef74867fc1434be1942e837932691f`
(the commit already pinned by the aligner/reader scripts); HEAD == that commit.
WLC manifest sha256 (39 books, excl. VerseMap.xml):
`f32cf0c442ec090f54ed13c9d48a0809e6be33cd5926dbefac695ccb8472e0cd`.
TAHOT (STEPBible, CC BY 4.0) was re-confirmed to contain maqqef (`עַל־`,
`וַֽיְהִי־`) and remains a cross-check only, per the plan's pre-resolved
decision.

**Token-safety proof (the critical rule):** attaching the `<seg>` to the
PRECEDING token (WLC convention: `אֶת` → `אֶת־`) changes token *surfaces* but
never the token *count* or `word_index` sequence. Verified across the whole OT:
23,213/23,213 verses have exact per-verse token-count parity between the live
DB and the pinned source, with 0 surface diffs excluding maqqef, and 42,570
maqqef tokens in the source. Gematria values are unaffected (compute_all skips
U+05BE).

**Implemented:**
- `scripts/ingest.py` — `extract_hebrew_words_from_verse()` folds maqqef segs
  into the preceding token; `extract_hebrew_text()` joins the same token dicts;
  `OSHB_SOURCE` records URL + commit + manifest hash; new
  `verify_maqqef_token_integrity(conn, sample_books)` regression gate + a
  `--check-hebrew-tokens` CLI mode (read-only).
- Reingest exercised on a **temp copy** of scripture.db (gen/psa/isa): 0
  token-count diffs, 0 word_index contiguity violations, maqqef restored exactly
  (2,953 / 2,404 / 1,832 — matching the source).
- A2: `align_hebrew_vocabulary.py` re-run against the reingested text on a temp
  memorize DB — 375 gen/psa/isa-aligned lessons, **0 cloze mismatches**, 0
  out-of-range positions (cloze answers are unpointed consonant skeletons, so
  maqqef is invisible to them by construction).
- `tests/test_oshr_maqqef.py` (6 tests): maqqef-attach/word_index unit tests +
  the full OT token-integrity gate + sampled-book scope.

**⚠ Live apply still required:** the production `data/processed/scripture.db`
was NOT reingested (per instruction — do not write production DBs). To apply
maqqef to the live text, run:
`python3 scripts/ingest.py` (full rebuild) or a targeted reingest of
`text_hebrew`/`gematria` from `data/raw/morphhb/wlc/`, then re-run the gate
(`--check-hebrew-tokens`) to confirm 0 token drift. The ingest path is now
functional because the pinned source is vendored under `data/raw/morphhb/wlc/`.

## Session 2026-08-06 (Sessions — Track B)

**Frontend:** added `hebrewSessionUser()` to `frontend/src/api.js` — resolves
the real user id from the stored `scripture_session_token` (localStorage key is
`scripture_session_token`, NOT `scripture_n`) via `/auth/me`, caching and
falling back to `'default'` on invalid/expired/absent tokens (graceful, no error
toast). `frontend/src/components/HebrewLearnView.jsx` now resolves the session
user and passes `user_id` to the per-user Hebrew reads it owns: curriculum,
gamification, review-queue, and verb-drill (all GET endpoints take `user_id`;
the write endpoints — `/hebrew/progress`, `/hebrew/fsrs/review`,
`/hebrew/diagnostic/apply` — already bind `session_token` in the body and are
hit from other components).

**Backend binding asserted:** `tests/test_hebrew_session.py` (7 tests) proves
valid token → real user with forged `user_id` ignored (`/hebrew/progress` row
lands on `real-user-123`, not `attacker-forged`), invalid token → 401, and the
same for `/hebrew/fsrs/review`; plus `_resolve_hebrew_user` unit cases.

**Verification:** `vite build` clean; 92/101 frontend unit tests pass (the 9
`chatStream.test.js` failures are **pre-existing** — reproduce with my changes
stashed). `python3 -m pytest tests/ -k hebrew -q` → 54 passed.

## Session 2026-08-06 (Vocabulary — Track C)

Determined the exact gap from the frequency ranking (`get_top_words` against the
lexicon): within the top-520 window, 6 surfaces lack lessons — H1197a בָּעַר,
H8057 שִׂמְחָה-construct (שמחתכם), H1197b יבער, H2181 זנה 3fs (זנתה), H2459
חֵלֶב, H1616 גֵּר. יבער is skipped at seed time as a homonym of בָּעַר (same
Strong's base 1197), so **5 new lessons** are created → 517 → **522** aligned.

**Implemented:** `scripts/seed_hebrew_vocabulary.py` default `--count` 500 → 520
(ranking-safe; skips any surface or (language, base) already present) and
`scripts/align_hebrew_vocabulary.py` default `--count` 500 → 520 to stay in
lockstep so every seeded lesson falls in the aligner's candidate set.

**Verified on a temp DB** (copy of data/memorize.db, never the live DB):
- seed → 5 new lessons; 2nd seed run → **0 new** (idempotent)
- align → all 5 aligned to exact OT tokens (בָּעַר→exo.3.2 burning bush,
  זנה→gen.38.24, חֵלֶב→gen.45.18, גֵּר→gen.15.13, שִׂמְחָה→num.10.10); 2nd align
  → 0 changes (updated_at stable)
- repair + `validate_hebrew_learning_content.py` → green; 522 vocab lessons =
  522 alignment rows (checkpoint ≥522 ✓)

**⚠ Live apply still required:** the live `data/memorize.db` was NOT seeded
(per instruction). To apply: `bash scripts/seed_hebrew_all.sh` (or
seed → align → repair → validate).

## Net line delta

Code: +231 / −44 (ingest.py +171/−36, HebrewLearnView +23/−6, api.js +27,
seed_hebrew_vocabulary +7/−1, align_hebrew_vocabulary +3/−1) · Tests: +223
(test_oshr_maqqef.py 111, test_hebrew_session.py 112). Net ≈ **+410 lines**.

## Blockers / open actions

- Live reingest of `data/processed/scripture.db` to apply maqqef (Track A).
- Live `seed_hebrew_all.sh` run to apply the 5 new vocab lessons (Track C).
- The diagnostic POST components (`HebrewDiagnostic.jsx`, `AssessmentView.jsx`,
  `HebrewQuiz.jsx`, `HebrewLessonView.jsx`) are outside this session's file
  ownership; their `/hebrew/diagnostic/apply` + `/hebrew/progress` calls already
  send `user_id` and the backend already binds `session_token` there, so a
  follow-up can add the token to those calls' bodies if per-user diagnostics is
  desired.
