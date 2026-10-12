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
