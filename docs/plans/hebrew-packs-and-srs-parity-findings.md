# Findings: Hebrew packs & SRS parity

## Requirements (discovery answers)
1. **Goal:** Close the standard-feature gaps in Hebrew learning and grow
   vocabulary coverage via more flashcard packs on the proven WHV pattern
   (Anki deck → 3-way cards + audio + FSRS persistence).
2. **Workstreams (tracks):** A) pack importer + new packs; B) SRS-mechanic
   parity (retention control, leech, undo/suspend, stats, optimizer);
   C) card-content depth (sentence context, pictures, verb parsing).
3. **Pre-resolution:** decisions below; nothing left that blocks Track A.
4. **Constraints:** personal-study media never committed (`data/audio/anki/`
   stays gitignored — extends to ALL third-party mp3/png); stdlib-first,
   no new deps; minimal diffs; `vite build` + vitest + pytest green per phase.
5. **Acceptance:** per-phase checkpoints in the plan file.
6. **Anti-scope:** no multi-device sync; no bundled third-party audio/images;
   no new scheduler (everything rates through FSRS/progress paths);
   no LLM-generated *facts* without curriculum grounding (guided-lesson rule).

## Pre-resolved decisions
- **Importer over one-offs:** generalize `scripts/import_anki_audio.py`
  (WHV-specific: hardcoded fields, audio-only) into
  `scripts/import_apkg_pack.py` — dumps `models`/`notes`, takes a
  field-map + media allowlist per pack, writes vocab nodes + Tier-0 media.
  Rationale: 3rd pack would otherwise mean a 3rd bespoke script.
- **STEP TBESH as the coverage base (CC BY 4.0, attribution in seed script
  + docs):** full-OT lemma+morph TSVs → frequency-ranked lemma list →
  join gloss → new `word` nodes. No audio in source → use the existing
  kokoro TTS pipeline (`web/routes/audio.py`, `AUDIO_SOURCES` already
  includes `"tts"`). Rationale: zero license risk, ~2,000 lemmas ≈ 90%
  running-text coverage, exercises the TTS path we already ship.
  → SUPERSEDED at A2 kickoff: the in-repo `lexicon` table (11,515 lemmas
  with corpus frequencies from `gematria` + definitions + `lemma_gloss`)
  already plays STEP's role with zero download risk. A2 seeds from the
  local lexicon via `seed_hebrew_vocabulary.py`.
- **Media policy:** repo stores scripts + manifests only. All mp3/png/wav
  (third-party AND generated, incl. kokoro weights) live under gitignored
  `data/audio/` (env in gitignored `venv-align/`) and are reproduced by
  seed scripts. WHV precedent applies to every pack.
- **Seeder fixes landed in A2** (all in `seed_hebrew_vocabulary.py`):
  `--allow-shared-base` (one node per surface, WHV-style; the old
  Strong's-base dedup hid 127 high-freq inflected forms), derived-gloss
  fallback (`lemma_gloss` → definition first clause, +35 words), and
  `frequency >=` instead of `>` (the freq==10 boundary hid 87 words).
- **Hackett deck (CC BY-SA 4.0, author audio CC0)** is the reference
  user-import pack: document the import command, do NOT vendor the .apkg.
  Ross-audio subsets inside it carry third-party terms → strip or skip
  Ross-sourced media on import (field/tag filter).
- **Verb-parse cards** reuse `recall`/`multiple_choice` practice items and
  grade via `/hebrew/progress` (server-side match) — no new grading path.
  New renderer only (prompt=surface form, answer=parse).
- **Sentence-context cards** reuse verse corpus + TTS; rating flows through
  existing card modes (no new scheduler).
- **FSRS optimizer deferred:** optimization needs dense per-card review
  history we don't retain yet. Track B records what's needed and ships
  defaults + desired-retention control; optimizer is an explicit later phase.

## Architecture notes
- Resolution: new STEP lemmas must resolve through `resolve_hebrew_node`
  layers (exact → folded → affix-strip incl. imperfect prefixes → Strong's
  lemma → LIKE). Bare-form STEP lemmas should hit the folded map; log the
  miss rate at seed time, gate on ≥95% resolvable (WHV bar: 568/700 ≈ 81%
  raw, 100% top-100 — new pack should beat raw WHV since lemmas are
  dictionary forms).
- `schedulable=1` convention extends to every new word (vocab bands filter
  on it; Tools menu bands pick up new words automatically).
- Desired retention threads through existing FSRS calls as a parameter with
  the current hardcoded value as default — no behavior change until the
  user touches the setting.
- Leech threshold: Anki-standard 8 lapses; lapses already summed in
  `hebrew_review_state` and surfaced in Grammar Focus.

## Open questions → resolved
- Q: Bundle packs in repo? → A: No. Scripts + manifests only; media
  gitignored; user runs one seed command per pack.
- Q: Which pack first? → A: STEP top-2000 (license-clean, biggest coverage
  win). Hackett second (proves the generic importer on a real .apkg).
- Q: Ship generated TTS audio? → A: No, generate at seed time (same rule
  as third-party media; keeps the repo small and the pipeline honest).

## Audio sourcing verdict (2026-10-04): kokoro-hebrew stays the backbone
- Surveyed alternatives: Lingua Libre/Wikimedia Commons human clips, Forvo,
  Piper Hebrew, Meta MMS-tts-heb, Mamre-TTS, HebTTS (academic), commercial
  APIs (ElevenLabs/OpenAI/Google he-IL), cutting word clips out of verse
  narration, more Anki decks.
- Commons spot-check (12 common words, exact-title audio match): isolated
  human clips exist for ~half of common base forms (איש, אני, בור, כוס,
  מכה via Lingua Libre `heb`), miss on others (עצום, אלך), and inflected /
  suffixed forms (גשמיכם, תזנותיך … — much of the queue) have ~zero
  coverage anywhere. CC BY-SA 4.0 would also need attribution/share-alike
  handling if vendored.
- Piper Hebrew is WIP (unreleased; MIT "Motek" voice lower quality; engine
  now GPL-3.0); MMS-tts-heb quality rated poor by the community;
  Mamre-TTS weights are NC-only; commercial APIs are paid + cloud +
  unpointed-text (lose phonikud's niqqud precision — espeak drops Hebrew
  vowels entirely, our pipeline's whole reason for being).
- Decision: keep phonikud → kokoro-hebrew TTS as the 100%-coverage
  backbone, human Tier-0 preferred where held (WHV 686, already wired).
  Lingua Libre backfill for common words is a possible later
  enhancement, low priority.
- ⚠️ License caveat: kokoro-hebrew-nc derives from gated
  `avris/kokoro-hebrew-saspeech` (non-commercial terms apply to model +
  voice). Fine for personal-study use; re-evaluate (Piper Hebrew MIT
  voice / commercial API) if ScriptureEngine ever ships commercially.
