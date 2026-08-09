---
status: completed
kind: plan
area: hebrew-learning
author: dillon
created: 2026-08-05
---

# Project: Hebrew Learning Content Follow-ups

Goal: Close the three documented follow-ups of
`docs/plans/hebrew-learning-content-overhaul.md` (status: active): Maqqef
reingestion, wiring the learner frontend to real sessions, and seeding the last
~5 top-frequency vocabulary surfaces. Parent plan's core work is done (content
overhaul, exact alignment, persisted scheduler, validator).

## Requirements
- [x] R1: **Maqqef reingestion** — pointed text with U+05BE maqqef restored,
      with OSHB token positions (word_index) preserved so the
      alignment/cloze/passage layers keep working
- [x] R2: **Real session wiring** — learner frontend sends its session token
      to review/progress/diagnostic endpoints so data is per-user instead of
      the shared 'default' user
- [x] R3: **Vocabulary seeding** — the last ~5 top-frequency OT surfaces that
      have no lesson get lessons (idempotent, no duplicates)

## Pre-resolved Decisions
- **Maqqef**: the progress doc already evaluated STEPBible TAHOT (has U+05BE,
  CC BY 4.0) but rejected naive restoration because it breaks OSHB token
  positions. Approach: pin a specific OSHB-XML snapshot (record version+hash),
  reingest with maqqef retained, and add a regression check that
  `word_index`/gematria token counts are unchanged per verse. TAHOT remains a
  cross-check, not the primary source. If a pinned OSHB source can't be
  secured, ship a **documented gap** instead of risking the token layer.
- **Sessions**: the API side already supports `session_token`
  (`web/routes/auth.py` + `memorize.py`, forged user_id ignored, 401 on
  invalid). The frontend already stores the token at `scripture_n` in
  localStorage (`frontend/src/api.js::getSessionToken`-equivalent used by
  settings/auth). Work = send it on hebrew review/progress/diagnostic calls
  and handle 401 by treating the session as the default user (no hard failure).
- **Vocabulary**: extend `scripts/seed_hebrew_vocabulary.py` (already
  ranking-safe — skips existing surfaces) with the missing surfaces from the
  exact-frequency ranking; run through the existing
  `scripts/align_hebrew_vocabulary.py` + `repair_vocabulary_metadata.py`
  pipeline; idempotency verified by a second no-op run.

## Track A: Maqqef Reingestion `[x]`
- Description: restore maqqef without breaking token positions.
- 📏 Scope: 3 files + data pipeline, ~200 lines

### Phase A1: Source pinning + ingestion plan `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 14
- [x] Locate/pin an OSHB-XML snapshot (or exact source text) that retains
      maqqef; record source URL/commit + hash in the ingest script
- [x] Reingest pointed text with U+05BE preserved (extend the existing
      OSHB ingest path; do NOT touch DSS/pseudo sources)
- [x] Regression gate: per-verse `word_index` sequence and gematria token
      counts identical pre/post reingest for a sampled book set (validator
      integration — see `scripts/validate_hebrew_learning_content.py`)
- 📏 Scope: ingest script ~120, validator +40, `lib/db.py` +10 (if a
      maqqef flag column is needed)
- ✅ Checkpoint: `python3 scripts/validate_hebrew_learning_content.py --db
      data/processed/memorize.db` green; sampled-book token counts unchanged;
      pointed text now contains U+05BE where expected
- ⚙ Fallback: if no trustworthy pinned source, **document the gap** in
      progress.md with the TAHOT analysis and leave the token layer untouched
      (explicit no-risk decision)

### Phase A2: Alignment + cloze verification `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [x] Re-run `align_hebrew_vocabulary.py` + `repair_vocabulary_metadata.py`
      against the reingested text; confirm cloze answers (consonant skeletons)
      still match surfaces
- [x] Spot-check known maqqef surfaces (e.g. וּבְנֵי, כָּל־) render correctly
      in lesson/practice UI
- 📏 Scope: pipeline run + targeted fixes, ~50 lines
- ✅ Checkpoint: alignment idempotent (2nd run = 0 changes); 36 Hebrew
      backend tests + validator green
- ⚙ Fallback: if alignment drifts, keep maqqef in display text but align on
      unpointed surface (existing identity-stable path)

## Track B: Frontend Session Wiring `[x]`
- Description: per-user hebrew data via the existing session token.
- 📏 Scope: 3 files, ~90 lines

### Phase B1: Token on hebrew API calls `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [x] Find the hebrew API call surface (`frontend/src/components/HebrewLearnView.jsx`,
      review/diagnostic actions) and attach the stored `scripture_n` token
      (same pattern as `AuthButton.jsx`/settings)
- [x] 401 handling: fall back to 'default' user gracefully (no error toast
      for anonymous learners)
- 📏 Scope: `frontend/src/components/HebrewLearnView.jsx` ~40,
      `frontend/src/api.js` +10 (helper), misc +10
- ✅ Checkpoint: with a logged-in session, review progress lands on the real
      user; anonymous still works via default
- ⚙ Fallback: wrap token attach behind the existing `getSessionToken()`
      helper so absence of the key is a no-op

### Phase B2: Verify + tests `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [x] Backend: extend one hebrew route test asserting session-token binding
      (valid token → real user; forged id ignored) — pattern exists in
      `tests/` for memorize
- [x] Frontend: build + existing 94 unit tests pass
- 📏 Scope: `tests/` +40
- ✅ Checkpoint: `python3 -m pytest tests/ -k hebrew -q`; `vite build` clean
- ⚙ Fallback: none

## Track C: Vocabulary Seeding `[x]`
- Description: last ~5 top-frequency surfaces get lessons.
- 📏 Scope: 1 script + data, ~40 lines

### Phase C1: Seed the gap `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 6
- [x] Identify the ~5 surfaces from the exact-frequency ranking (per
      overhaul progress: קהל/שבת/רעב/עמוד-style gaps already fixed; the
      remaining ~5 top-frequency + a few inflected display surfaces)
- [x] Extend `scripts/seed_hebrew_vocabulary.py` seed list; run
      seed → align → repair → validate (the `seed_hebrew_all.sh` path)
- 📏 Scope: `scripts/seed_hebrew_vocabulary.py` +25, data +15
- ✅ Checkpoint: second run creates 0 lessons (idempotent); vocabulary at
      ≥522 aligned lessons; validator green
- ⚙ Fallback: if a surface's lexicon entry has unreliable
      `hebrew_plain` (documented gap), skip it with a comment rather than
      seeding a broken lesson

## Track D: Rollup `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 5
- [x] Update `docs/plans/hebrew-learning-content-overhaul.md`: check the
      Masoretic/discourse requirement if still unchecked, note follow-up
      closure, flip status to completed once all tracks pass
- [x] Progress log `docs/plans/hebrew-content-followups-progress.md`
- ✅ Checkpoint: all tracks checked; parent plan accurate; live DB hebrew
      tables fingerprint unchanged by tests
- ⚙ Fallback: none

## Out of Scope
- New lesson types or grammar content (content overhaul is complete)
- DSS/Pseudepigrapha text changes
- Server-side account system changes beyond accepting the existing token
