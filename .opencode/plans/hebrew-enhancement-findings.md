# Findings: Hebrew Learning System Enhancements

## Requirements (from review)

The review identified 10 gaps between the current Hebrew learning system and an ideal learning experience:

1. **PassageReader not connected to reading lessons** — reading lessons just say "Read this chapter" with no actual text
2. **Vocabulary distractors are trivial** — always ["LORD", "God", "Israel"] — any learner can eliminate them
3. **No cumulative interleaved quizzes** — review queue exists but no explicit "quiz" checkpoint experience
4. **Verb drills separate from learning flow** — toggled on/off as a separate mode instead of auto-queued
5. **No audio for individual words in PassageReader** — audio backend exists but not surfaced in reading
6. **Connection graph not surfaced in reading** — 1.8M typed edges exist but learners never see them
7. **Phrase lesson practice is too easy** — distractors include "Hello", "Goodbye", "Amen" — never plausible
8. **Grammar cross-links not shown** — prerequisite edges exist in DB but not surfaced in lesson UI
9. **Daily Verse lacks context** — no link to learner's known vocabulary or study actions
10. **No known-vocab highlighting** — learner can't see which words they've studied when reading real text

## Architecture Notes

### PassageReader Component
- Located at `frontend/src/components/HebrewPassageReader.jsx` (306 lines)
- Fetches word data from `/api/v1/verses/{ref}/grammar` — returns words with hebrew, english, morph, lemma, gematria
- Also fetches verse text from `/api/v1/verses/{ref}`
- Words rendered as clickable chips; popup shows gloss, morphology, gematria
- Side panel shows word list with known/learning status (localStorage)
- No audio, no connection enrichment, no vocab cross-reference currently

### HebrewLearnView (Curriculum Dashboard)
- Located at `frontend/src/components/HebrewLearnView.jsx` (637 lines)
- Opens `HebrewLessonView` for all lessons via `onOpenLesson(node.id)`
- Reading lessons use same flow — no special handling for category === 'reading'
- Has PassageReader mode but it's a separate button ("📖 Read Passage"), not tied to reading lessons

### Reading Lesson Data
- 31 reading nodes with IDs like `read_gen1`, `read_exo14` — encode the chapter reference
- Each has a `content_json` with explanation text and key vocabulary
- Reading lessons currently show basic text: "Reading Assignment: Genesis 1. Read it in your preferred Bible version."
- The PassageReader already supports any `verseRef` like `gen.1` or `gen.1.1`

### Audio System
- Word-level: `GET /api/v1/hebrew/audio/{word}` — returns audio_url from Shmueloff alignments + letter recordings
- Verse-level: `GET /api/v1/read-along/{ref}` — returns audio URL + word timestamps
- `AudioReviewSession.jsx` already exists for audio-only review mode
- `DailyVerse.jsx` already has play-audio + TTS fallback

### Verb Drill
- Backend: `GET /api/v1/hebrew/verb-drill` generates questions from verb lesson nodes
- Frontend: `HebrewVerbDrill.jsx` has category selection but backend doesn't filter by it
- Currently a separate mode — not integrated into the learning flow

### Connection Graph
- `GET /api/v1/verses/{ref}/connections` returns typed edges (quotation, allusion, thematic, etc.)
- 1,819,093 connections in the graph
- Already used in the verse view (shows connections panel)
- Not surfaced in PassageReader or reading lessons

### Daily Verse
- `GET /api/v1/verse-of-day` returns a random verse
- `DailyVerse.jsx` shows verse with gematria, read-along audio, word breakdown toggle
- No link to learner's vocabulary progress

## Pre-resolved Decisions

All decisions documented in task_plan.md under Pre-resolved Decisions.

Key rationale: Everything suggested exists in the codebase already in some form. All 5 tracks are about connecting existing pieces, not building new infrastructure from scratch.

### What each track DOES NOT cover (anti-scope)

| Track | Out of scope |
|-------|-------------|
| Track 1 | Generating new audio files, translating new texts, building a new reader |
| Track 2 | Rewriting the vocabulary seed script, new DB tables |
| Track 3 | Spaced repetition algorithm changes, new DB tables |
| Track 4 | Creating new verb conjugation data, frontend redesign |
| Track 5 | Daily verse server changes, notification system |

## Open Questions → Resolved

- Q: Should reading lessons change the PassageReader or vice versa? → A: Minimal change to both. Reading lesson click sets `passageStudyRef` (existing pattern). PassageReader gets new features conditionally (audio button, connection indicator — only shown when data exists).
- Q: Should quizzes create new DB tables for quiz history? → A: No. Quizzes are runtime-generated. Results go to existing `hebrew_progress` table per-node. No quiz-specific storage needed.
- Q: How do we handle chapter-range refs for reading lessons? → A: For Phase 1.1, just use first verse of the chapter. The PassageReader component already takes a `verseRef` and can display multiple verses. The grammar endpoint supports chapter-range (it returns all words for all verses in the chapter).
