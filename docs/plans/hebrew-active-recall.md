---
status: proposed
kind: plan
area: hebrew-learning
author: opencode
created: 2026-11-22
---

# Active recall everywhere: production coverage + one study room

## Why

The bank teaches recognition far better than it teaches use. Coverage audit
(2026-11-22, live DB):

| Skill | Recognition | Production | Verdict |
|---|---|---|---|
| Words (535 nodes) | MC/recall/cloze ×1900 | typing ×517 + context cloze | strong both ways |
| Letters/vowels | MC/contrast | typing names | adequate |
| Verb morphology | MC + **parse naming** (C3) | **form writing** (R1, 41+41) | now both ways |
| Roots | MC ×42 | **extraction writing** (R1, 17) | now both ways |
| Phrases | MC ×16 | **say-it writing** (R1, 8) | now both ways |
| Grammar/syntax rules | MC/recall ×70 | — | recognition only |
| Reading | recall ×204 + cloze | — (cloze is word-level) | no comprehension check |
| Listening | hearing cards (word) | — | no graded listening |
| Speaking | — | — | opted out (learner decision) |

The learning-review's ranked gaps say the same thing: direction mix
unenforced, no re-ask of misses (closed by intraday steps), bank
recognition-heavy. And the learner faces ~12 doors (Quiz, Review, Verb
Drills, 3 vocab bands, Grammar Focus, Audio Review, Word/Root Tiles, Verse
of Day, Passage Reader, 5-min Quick, games) into what is one memory
system. The fix is two-sided: finish production coverage per skill, then
collapse the doors into one room.

## Requirements

- [ ] R1 (DONE 2026-11-22): production seeders for verbs/roots/phrases +
      `typing` served typed in the cumulative quiz. 55 cards, all grading
      through existing paths.
- [ ] R2: grammar-application production (rule → inflected form in a
      sentence blank), seeded from affix/construct/agreement lessons.
- [ ] R3: listening dictation (audio slice → type what you hear), word
      level first (alignments exist), verse level next.
- [ ] R4: reading comprehension (verse-claim true/false) + the one-room
      session composer with an authentic verse block.
- [ ] R5: per-session production-ratio enforcement (≥40% production, the
      review doc's gap #1) + analytics on the ratio.

## Method notes (why these, not alternatives)

- **Production before recognition, always.** Generation effect (Roediger
  side of the review doc): typing יכתוב from "Qal imperfect 3ms 'he will
  write'" builds the trace that MC option-picking never does. Every new
  type below outputs Hebrew; English output stays recognition-only.
- **Roots before rare words.** One root (כתב) unlocks dozens of surfaces;
  root-extraction cards have the highest leverage-per-minute in the bank.
  The curriculum already gates roots at L4 with the word↔root synergy
  bonus — production cards complete the loop.
- **Dictation, not just hearing.** Hearing cards (audio → think gloss) test
  recognition; dictation (audio → type the form) tests segmentation +
  orthography — the next rung on the Bjork gradient. Infra is already
  there: `/api/v1/hebrew/word-audio/{verse}`, verse alignments, skeleton
  grading. Word-level first (isolated audio), verse-level when word-level
  retention clears 80%.
- **Comprehension, not just cloze.** Sentence cloze proves the word fits;
  verse-claim true/false proves the meaning landed ("The verse says God
  created heav'n/earth: true" vs a distortion). Cheap to seed (verse
  English + one swapped content word), graded by the existing MC path.
- **Speaking stays out.** Prior learner decision (audiobook listener);
  flagged, not relitigated. If revisited: read-aloud + self-compare
  against verse audio, no ASR needed for v1.

## The room (R4 design)

One `GET /api/v1/hebrew/daily-session` composes: due reviews interleaved
across ALL modes (the existing queue + directed modes + new production
types), new cards to the daily cap, then a 5-minute authentic block —
one verse: listen (verse audio) → read along → 1 comprehension + 1 cloze.
One frontend view reuses AnkiReview/CardQueue/Quiz renderers by
`question_type` + `answer_mode` (dictation = audio front + typed input;
no new renderer family). Every rating lands on an existing FSRS path
(rule 7 holds); the session ends with the existing session summary.
The composer enforces the mix: fill production slots first (R5), then
recognition, then new.

Entry points don't disappear on day one — the room becomes the default
tab; the twelve doors shrink to "practice one thing" shortcuts.

## Anti-scope

- No speaking/ASR. No new scheduler (rule 7 everywhere). No LLM-generated
  facts (sentence sources stay verse-corpus + lesson content). No bundled
  third-party media. Grammar-application seeding must parse lesson
  explanations, not invent paradigms — same discipline as the parse seeder.

## Update 2026-11-22 — R2 DONE, M1 DONE
- R2 done as designed above (16 cards). One deviation: breakdown restricted
  to morphological nodes (sentence-level "parses" restate, don't test).
- M1 (master plan) done: `GET /hebrew/coverage?book=&chapter=` — chapter
  tokens resolved through exact→folded→affix→lemma layers, mastery ≥ 0.8 =
  known; Gen 1 @ 48.4% for the live user with mineable unknowns. Reader
  header shows the 📖 dial (green ≥95 / amber ≥80 / red below) with a
  tap-to-mine hint; WordPopup's Add-to-Learning was already wired.
  `tests/test_hebrew_coverage.py` 3 passed.
