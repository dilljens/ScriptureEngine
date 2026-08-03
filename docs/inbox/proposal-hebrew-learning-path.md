---
status: implemented
kind: proposal
area: hebrew-learning
author: agent
created: 2026-08-03
implemented: 2026-08-03
---

# Hebrew learning path: audio, images, quiz-in-lesson, SRS, placement

Research-backed design for the Hebrew memorization feature. Covers: verse + word
audio, word→image association, quiz-in-lesson, the interleaved learning path
(words + grammar + reading), and an adaptive placement test.

**Status: implemented (P1–P5, 2026-08-03).** See the "Implemented" section at the
bottom for what shipped and how to extend it.

**Headline:** the codebase already ships most of this — FSRS-5 spaced repetition
(`hebrew.py` FSRS_W), an interleaved non-interference review queue
(`/hebrew/review-queue`), a `word_images` table + `/hebrew/image/{word}`, and a
verse/word audio pipeline (`web/routes/audio.py`, F5-TTS + WhisperX alignment).
What's missing is **coverage** (audio/images exist for a handful of items),
**integration** (no image or audio in the lesson view; no quiz button), and
**adaptivity** (the diagnostic is static, not adaptive). This proposal closes
those gaps and maps the full learning path.

---

## 1. Audio — verse playback + per-word listening

**Goal:** play a full verse, and tap any word to hear just that word.

**Recommended approach (already 90% built): synthesize the full verse, then
word-align with Whisper.** Slicing words from the natural continuous reading is
better than synthesizing each word separately — Hebrew has heavy contextual
shifts (proclitic particles, sheva elision, begadkefat across word boundaries),
so isolated-word synthesis sounds wrong and breaks verse flow.

- **Verse audio:** F5-TTS Hebrew v2 (Apache-2.0) already wired in
  `scripts/generate_word_audio.py`; extend to verses, or reuse the existing
  OmniVoice/Shmuelof-clone pipeline in `scripts/generate_audio.py`. Feed the
  **pointed (niqqud-carrying)** text — that's what disambiguates pronunciation
  for a memorization app. Strip ta'amim before synthesis.
- **Word audio:** WhisperX forced alignment (`scripts/align_hebrew_whisperx.py`
  already does this; reuses verse boundaries, no ASR text step) → per-verse
  `words.json` of `{word, start_ms, end_ms}`. The existing
  `/api/v1/hebrew/audio/{word}` lookup already checks
  `audio_timestamps.word_timestamps` then alignment JSONs — just needs the
  coverage.
- **Cloud TTS (only if open-source F5-TTS quality disappoints):** Google
  he-IL-Wavenet-A ($4/1M chars ≈ $25–40 one-time for the whole Tanakh) or
  Chirp3 HD ($30/1M). Azure has he-IL Avri/Hila. Amazon Polly has **no Hebrew**
  voice — exclude. All major TTS speak Modern Israeli (≈ Sephardic vowels);
  none chant ta'amim, which is acceptable for memorization. espeak-ng is the
  offline fallback (robotic).
- **Licensing alternative for common words:** Wiktionary hosts 2,021 Hebrew
  pronunciation files (CC BY-SA) — a free word-audio supplement.
- **Caching:** pre-generate at ingest time, serve statically (`data/audio/`),
  store `voice_version` per verse for regeneration. No per-request TTS.

**Coverage plan:** generate for the vocabulary/reading nodes that have
attestations first (the ~2,870 practice items reference words — attach
`audio_url` to `hebrew_practice_items` at ingest), then Genesis 1 as the
read-along demo chapter, then scale.

## 2. Word → image association

**Goal:** concrete words show a picture (cow → 🐄-style photo).

**Recommended primary source: Openverse API** (`api.openverse.org/v1/images/`)
— aggregates CC-licensed images from Wikimedia Commons and Flickr, returns a
pre-built `attribution` string per image, filters to commercial-safe licenses
(`license_type=commercial`; skip `by-nd` if we crop). Wikimedia Commons API
(`commons.wikimedia.org/w/api.php`, free, no key, needs a User-Agent) is the
deeper source for ancient/biblical items (tent, altar, sacrifice, oil) and the
fallback when Openverse returns nothing good.

- The existing `word_images` table (424 rows, source `freebibleimages`,
  remote URLs) already has the right schema: `word_hebrew, node_id, source,
  image_url, attribution, width, height`. FreeBibleImages is actually ideal for
  the biblical/cultural words; Openverse covers everyday concrete nouns
  (cow, bread, king, donkey) where FreeBible is thin.
- **Recommendation:** multi-source ingest — FreeBible (existing) → Openverse →
  Wikimedia Commons → emoji fallback → no image. **Download to local storage**
  (`data/images/words/`) at ingest with attribution in the DB; remote URLs are
  a liability (hotlinking, dead links). Coverage expectation: ~80–90% of
  concrete nouns get a good match; abstract/grammar words gracefully skip.
- **Surface in UI:** show image + attribution in `HebrewLessonView` header
  (when the node has a word_image) and on the back of `AnkiReview` cards
  (already wired — extend to lessons and practice cards).

## 3. Quiz button in lessons

**Goal:** a "Start Quiz" button in `HebrewLessonView` instead of one question
at a time.

**Design:**
- Add `GET /api/v1/hebrew/lesson/{node_id}/quiz` — returns this lesson's
  practice items as a quiz (interleave MC → recall → typing, per Math Academy
  scaffolding; mix in 1–2 confusable distractor items from
  `hebrew_confusability` if present).
- Add a "Start Quiz" button in `HebrewLessonView` above the CardQueue; quiz
  mode = timed, graded, runs the full item set, shows a results screen with
  per-item feedback, then hands back to the flashcard practice.
- **Feed SRS:** lesson practice currently posts to `/hebrew/progress` (mastery
  only). Quiz answers should ALSO post ratings to `/hebrew/fsrs/review` so quiz
  performance drives the review queue. This is the single biggest wiring gap.

## 4. The learning path — interleaved words + grammar + reading

Mapped from Anki/SRS research + the existing 7-level curriculum tree
(703 nodes, 11 categories, `hebrew_edges` prerequisites).

**Curriculum spine (already exists):** Level 1 letters/vowels → syllables →
high-frequency words + basic grammar → phrases → reading practice → roots +
advanced grammar. Prerequisite edges gate unlocking. Keep it.

**SRS design (Anki-blessed, mostly already built):**
- **One broad deck, interleaved** — Anki's explicit guidance: "review your
  content mixed together in a single deck most of the time (for optimum
  memory)." No per-topic decks. The existing `/hebrew/review-queue` already
  round-robins categories and spaces confusable pairs ≥3 apart (non-interference)
  — exactly right. Don't block words-grammar-reading into separate sessions;
  mix new + review every session.
- **New-card introduction:** cap new cards/day (Anki default 20; for a
  scripture app 10–15/day → ~100–150 reviews/day steady state). New cards go
  through intra-day learning steps (Anki default 1m/10m; slightly longer, e.g.
  10m/2h, suits script + roots), then graduate at 1d. FSRS handles the rest —
  the repo's FSRS-5 already implements this.
- **Interleaving caveat (research):** Dunlosky's review found interleaving did
  NOT help French vocab-by-category or comma-grammar learning — spacing/retrieval
  is the engine, interleaving is a queue property (prevents order-cueing, trains
  recognizing-which-construction). So: keep every item on its own independent
  schedule; interleave the *presentation*.
- **Card types in the mix (add):** the strongest cards are full-sentence cloze
  that embed both a word and a construction (Duolingo lexeme-tag / Pimsleur
  "organic learning" pattern). The reading/phrase categories already provide
  this raw material; make sentence-cloze a first-class practice item type for
  reading nodes.
- **Guardrails:** stop new cards when backlogged (Anki manual advice); leech
  threshold ~8 lapses → tag + suspend; desired retention knob (default 90%,
  beginners under load can drop to 80–85% to cut workload).

**The daily diet (recommended shape):** 1) due reviews (longest-waiting first),
2) new cards (frontier = unlocked-by-prereqs, mixed categories, capped), 3)
short interleaved cumulative quiz (existing `/hebrew/quiz`) — one session,
mixed.

## 5. Placement test — test out of what you know

**Goal:** let users skip content they already know; seed SRS so known items
aren't reviewed heavily.

**What exists:** `HebrewDiagnostic.jsx` + `GET /hebrew/diagnostic` +
`POST /hebrew/diagnostic/apply` — static 2 MC × 10 categories, single-use batch,
applies per-category credit. The adaptive BLIM/IRT engine (`lib/assessment/`)
is real but wired to scripture `knowledge_items`, not Hebrew.

**Recommended design (research-backed, no calibrated item bank needed):**
- **Per-skill adaptive subtests** (alphabet/vowels → vocab → grammar → reading),
  each using a **1-up-3-down staircase** over difficulty, where difficulty =
  curriculum position (lesson index) from `hebrew_practice_items.difficulty`.
  Staircase needs no item calibration, converges to ~79% correct, and is
  trivial to implement. Min ~6 / max ~15 items per section; stop early when the
  confidence band fits inside one lesson band, else at max length.
- **Vocab sampling** stratified across frequency bands (high-frequency words
  first, rare words late) so someone who knows "the basics" isn't tripped by a
  rare word.
- **Scoring:** Bayesian EAP with a mild prior (so all-correct/all-wrong users
  get a finite estimate); map θ → "start at lesson N" per dimension.
- **Partial credit** on typed/translation items (Duolingo's mistake-type
  weighting) to reduce noise.
- **SRS seeding (the "don't review as much" part):** every placement item
  answered correctly → seed high initial stability (FSRS `fsrs_initial_stability`
  with a long half-life → effectively mature, rarely reviewed); missed → low
  stability (review soon); partially correct → middle. Mark tested-out nodes as
  mastered in `hebrew_progress` so they unlock but don't burden the queue.
  (Half-life regression from the Duolingo ACL paper: correct answers double the
  half-life — a principled way to convert placement answers into intervals.)
- **Reuse note:** the BLIM/IRT engine could be extended to source items from
  `hebrew_practice_items` (category = difficulty axis), but the staircase over
  curriculum position is simpler, needs no calibration, and is good enough for
  lesson-band placement. Start with the staircase; graduate to IRT if placement
  accuracy matters later.

## 6. Implementation phases (rough)

| Phase | Work | Effort |
|---|---|---|
| P1 | Wire lesson practice + quiz answers → `/hebrew/fsrs/review`; add "Start Quiz" button + per-lesson quiz endpoint | S |
| P2 | Image ingest: Openverse/Wikimedia downloader → local `data/images/words/` + attribution; surface image in lesson view + practice cards | M |
| P3 | Audio coverage: F5-TTS for attested vocab + read-along chapter; attach `audio_url` to practice items; word-tap in lesson view + passage reader | M |
| P4 | Placement: adaptive per-skill staircase over `hebrew_practice_items.difficulty`; EAP scoring; SRS seeding + test-out credit | M |
| P5 | Curriculum polish: sentence-cloze card type for reading nodes; new-card cap + backlog guardrails in review queue | S–M |

## Sources

- Anki manual (card states, deck options, FSRS, leeches), SM-2 spec, FSRS docs
- Dunlosky 2013 "Strengthening the Student Toolbox" (interleaving boundaries)
- Settles & Meeder 2016 (half-life regression, Pimsleur/Leitner schedules)
- Google Cloud TTS voices/pricing; Azure voice table; AWS Polly voice list (no
  Hebrew); Piper VOICES.md (no Hebrew); espeak-ng; Wiktionary Hebrew audio
- Duolingo placement blog (partial credit, adaptive, skill unlock)
- Wikipedia CAT / IRT; psychophysics staircase methods (1-up-N-down)
- Openverse API (live-tested); Wikimedia Commons API (live-tested)

---

## Implemented (2026-08-03)

All five phases shipped. Every Hebrew test passes (31 in `TestHebrewRoutes`),
frontend builds clean, server verified live.

**P1 — Quiz-in-lesson + SRS wiring**
- `GET /api/v1/hebrew/lesson/{node_id}/quiz` — per-lesson quiz: practice items in
  micro-scaffolding order (MC → recall → typing), plus confusable distractors
  from `hebrew_confusability` appended last. Returns the `/hebrew/quiz` shape.
- "Start Quiz" button in `HebrewLessonView` → full-screen `HebrewQuiz` (nodeId mode).
- `HebrewQuiz` now renders ALL practice types: MC/true_false/contrast as choice,
  transliteration/cloze/recall/typing/letter_name as typed input with Hebrew
  keyboard + niqqud-insensitive grading. Quiz answers POST to `/hebrew/progress`,
  which feeds the FSRS review state — so quizzes are retrieval practice, not just tests.

**P2 — Word images (local, licensed)**
- `scripts/ingest_word_images.py` — Openverse (primary, with optional auth) or
  Wikimedia Commons (no daily cap, 429 backoff built in) search by English gloss,
  filters commercial-safe licenses (cc0/by/by-sa, excludes by-nd), downloads to
  `data/images/words/`, upserts LOCAL url + attribution into `word_images`.
  Resumable, idempotent, skips abstract function words.
- `/images/words/` static mount + `/hebrew/image/{word}` prefers local files.
- `HebrewLessonView` shows the word image + attribution for vocab nodes.

**P3 — Audio coverage**
- 605 word/phrase/root WAVs now exist (was 580; 25 more generated via
  phonikud → Kokoro, including phrase_* and root_* nodes via improved title
  extraction). `generate_word_audio.py` is idempotent (--force to regen).
- `/api/v1/audio/word/{node_id}` endpoint; `/hebrew/audio/{word}` falls back to
  words/ dir then node-id lookup. RFC 5987 Content-Disposition for Hebrew names
  (fixed a 500 on `root_כתב`).
- Practice items + lesson responses now carry `audio_url` / `hebrew_word` /
  `gloss` / `transliteration` so the UI avoids fragile word lookups.

**P4 — Adaptive placement test**
- `POST /api/v1/hebrew/diagnostic/adaptive/start|answer` — per-skill
  (alphabet/vocab/grammar/reading) 1-up-3-down staircase over curriculum level
  (converges ~79%, no calibrated item bank needed). Min 6 / max 15 items/skill.
- EAP-style estimate per skill, clamped to the skill's level range; confidence.
- On completion: tested-out credit (nodes ≥2 levels below estimate → mastery 0.8),
  SRS seeding per answer (correct → mature interval, miss → review soon).
- `HebrewDiagnostic.jsx` rewritten to drive the adaptive flow one question at a
  time with per-skill results.

**P5 — Sentence-cloze + new-card guardrails**
- `scripts/generate_sentence_cloze.py` — 150 sentence-cloze items across 26
  reading nodes: Hebrew cloze (blank the word in the real verse, type it) +
  English MC cloze (blank the gloss, pick the Hebrew word), with prefix-aware
  distractor filtering (excludes ומיהוה vs יהוה).
- Review queue: `new_cards_per_day` cap (default 10), frontier = unlocked-unpracticed
  nodes, mixed into the interleaved queue (`is_new: true`), suppressed when the
  backlog > 3× the daily cap (Anki manual guidance).

**Extending:** images are rate-limited by Wikimedia (~1-3/word after 429 backoff);
re-run `scripts/ingest_word_images.py --apply` to grow coverage (resumable). Set
`OPENVERSE_CLIENT_ID/SECRET` for a much higher rate limit. Audio: run
`venv-align/bin/python scripts/generate_word_audio.py --apply` after adding nodes.
