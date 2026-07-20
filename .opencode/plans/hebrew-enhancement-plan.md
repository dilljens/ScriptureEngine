# Hebrew Learning System Enhancements — Plan

**Goal**: Bridge the largest experience gaps — make reading lessons interactive, add cumulative quizzes, improve vocabulary practice, integrate verb drills, enrich reading with connections + audio.

## Pre-resolved Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture | All additive — no existing code deleted | Safe incremental improvements |
| Frontend | React (existing components) | PassageReader, HebrewLearnView, LessonView already exist |
| Backend | Python/FastAPI + SQLite | Existing API patterns |
| Audio | Use existing `/api/v1/hebrew/audio/{word}` + read-along endpoint | No new audio pipelines needed |
| Connections | Use existing `connections` table | Just surfacing existing data in UI |
| Quizzes | Runtime-generated from `hebrew_practice_items` | No new DB tables |
| Deploy | Existing `scripts/deploy.sh` | Test suite + rsync pattern already works |

## Tracks

### Track 1: Reading Lesson Makeover `[ ]`
Connect reading lessons to PassageReader. Add word-level + verse-level audio. Surface connection graph. Highlight known vocabulary.

**Phase 1.1 — Reading lesson → PassageReader bridge** `[ ]`
- When learner clicks a reading lesson, open PassageReader at its chapter instead of HebrewLessonView
- Reading node IDs encode the ref: `read_gen1` → `gen.1`, `read_exo14` → `exo.14`
- Add "Lesson info" toggle in PassageReader showing the reading's explanation text
- 📏 Scope: ~2 files, ~100-150 lines
- ✅ *Checkpoint*: Clicking reading lesson opens PassageReader at correct chapter with clickable words
- ⚙ *Fallback*: Use first verse of chapter; add range iteration later

**Phase 1.2 — Word-level audio** `[ ]`
- Audio button in word popup — fetch from `GET /api/v1/hebrew/audio/{word}`
- Small speaker icon next to each word in popup
- Cache audio URLs in component state
- 📏 Scope: ~2 files, ~80-120 lines
- ✅ *Checkpoint*: Clicking a word shows audio button; clicking it plays pronunciation
- ⚙ *Fallback*: If no audio file exists, hide button gracefully

**Phase 1.3 — Verse audio ("play entire verse")** `[ ]`
- "🔊 Play Verse" button in PassageReader header
- Fetch read-along data: `GET /api/v1/read-along/{ref}` — audio URL + word timestamps
- Highlight words in sync with audio
- Fallback to browser TTS if no real audio
- 📏 Scope: ~1 file, ~100-150 lines
- ✅ *Checkpoint*: Play Verse button plays audio, highlights words in sync
- ⚙ *Fallback*: Browser `SpeechSynthesis` API

**Phase 1.4 — Connection enrichment** `[ ]`
- For each verse, fetch `GET /api/v1/verses/{ref}/connections?limit=3`
- Show 🔗 indicator on verses with notable connections
- Popup shows connected verse, connection type, text preview
- 📏 Scope: ~2 files, ~80-120 lines
- ✅ *Checkpoint*: Verse with connections shows 🔗; clicking shows details
- ⚙ *Fallback*: Hide indicator if fetch fails

**Phase 1.5 — Known-vocab highlighting in reading** `[ ]`
- Cross-reference reading's key vocabulary against learner's progress
- Highlight known words (green glow) and mastered words (gold) in passage
- "Review These Words" button → mini vocab drill for unmastered passage words
- 📏 Scope: ~2 files, ~80-100 lines
- ✅ *Checkpoint*: Known vocab highlighted; review button opens relevant practice
- ⚙ *Fallback*: Use client-side Set intersection if server too expensive

---

### Track 2: Smarter Vocabulary Practice `[ ]`
Replace generic distractors, upgrade phrase lessons.

**Phase 2.1 — Dynamic distractors** `[ ]`
- Replace hardcoded `["LORD","God","Israel"]` distractors with same-frequency-band or same-domain alternatives
- Query words with similar frequency (±20%), same POS, or same root pattern
- Migration script updates all existing vocabulary practice items
- 📏 Scope: ~2 files, ~80-120 lines
- ✅ *Checkpoint*: "בית" MC has distractors like "עיר", "שדה", "אוהל" instead of "LORD"/"God"
- ⚙ *Fallback*: If no similar word found, fall back to random common words

**Phase 2.2 — Phrase lesson upgrades** `[ ]`
- Replace generic distractors ("Hello", "Goodbye", "Amen") with real Hebrew options
- Add cloze items: blank out key word in phrase
- Add typing items: English → type the Hebrew phrase
- Migration updates existing phrase practice items
- 📏 Scope: ~2 files, ~80-100 lines
- ✅ *Checkpoint*: "Thus Says YHWH" has: real MC options, cloze ("כֹּה ___ יְהוָה"), typing prompt
- ⚙ *Fallback*: For hard phrases, use word-bank multi-select instead of free typing

---

### Track 3: Cumulative Interleaved Quizzes `[ ]`
Add mixed-topic quizzes from recently-studied material.

**Phase 3.1 — Quiz API** `[ ]`
- `GET /api/v1/hebrew/quiz?count=10&user_id=default`
- Select 2-3 practice items from 3-4 recent nodes (from `hebrew_progress` ordered by `last_practiced`)
- Enforce: no consecutive questions from same category
- Return flat list with `node_id`, `type`, `question`, `options`, `correct_answer`
- 📏 Scope: ~1 file, ~80-120 lines
- ✅ *Checkpoint*: `curl /api/v1/hebrew/quiz?count=8` returns 8 questions from ≥3 categories, no consecutive duplicates
- ⚙ *Fallback*: If user has <3 studied nodes, include unstudied low-level nodes

**Phase 3.2 — Quiz frontend** `[ ]`
- `HebrewQuiz.jsx` component — progress bar, question counter, per-category badge
- Per-question timer scaled by type (same as LessonView)
- End screen: score + per-category breakdown + "review these" links for missed items
- Submit results to progress endpoint for each node
- 📏 Scope: ~1 file, ~150-200 lines
- ✅ *Checkpoint*: Quiz shows 10 mixed questions, timer ticks, end screen has score + review links
- ⚙ *Fallback*: On timer expiry, auto-submit with unanswered = incorrect

**Phase 3.3 — Quiz trigger in curriculum** `[ ]`
- "📝 Quiz" button in `HebrewLearnView` toolbar
- Badge when new quiz available (every 5 completed lessons)
- Quiz completion → XP bonus in gamification
- 📏 Scope: ~1 file, ~30-50 lines
- ✅ *Checkpoint*: Quiz button visible; clicking starts quiz with recent material
- ⚙ *Fallback*: No recent material → gray out button with tooltip

---

### Track 4: Verb Drill Integration + Grammar Cross-Links `[ ]`
Auto-queue verb practice, show prerequisites in lesson view.

**Phase 4.1 — Verb drill auto-queue** `[ ]`
- In `POST /api/v1/hebrew/progress`: if node category is 'verb', auto-insert verb drill items from verb-drill endpoint into review queue
- Difficulty-based selection: mastery ≥ 0.8 → harder (recall/typing), < 0.8 → easier (MC)
- 📏 Scope: ~1 file, ~40-60 lines
- ✅ *Checkpoint*: Completing "Qal Perfect" auto-adds 3-5 verb drill questions to queue
- ⚙ *Fallback*: If verb-drill endpoint fails, silently skip

**Phase 4.2 — Grammar prerequisite cross-links** `[ ]`
- Add "Prerequisites" section at top of `HebrewLessonView` — clickable pills/badges
- Data already returned by lesson endpoint as `prerequisites` array
- Wrong answer → highlight which prerequisite might be weak
- 📏 Scope: ~1 file, ~60-80 lines
- ✅ *Checkpoint*: Grammar lesson shows prerequisite pills; clicking opens that prerequisite lesson
- ⚙ *Fallback*: If no prerequisites returned, hide section

**Phase 4.3 — Verb drill category filter** `[ ]`
- Backend `GET /api/v1/hebrew/verb-drill` already has `category` param in frontend but backend ignores it
- Fix backend to filter drills by category
- 📏 Scope: ~1 file, ~20-30 lines
- ✅ *Checkpoint*: `/api/v1/hebrew/verb-drill?category=qal` returns only Qal-related drills
- ⚙ *Fallback*: If category not found, return all drills (current behavior)

---

### Track 5: Daily Verse Enhancement `[ ]`
Make Daily Verse contextual — highlight known vocab, add study links.

**Phase 5.1 — Known-vocab highlighting** `[ ]`
- Check each daily verse word against `hebrew_progress`
- Green highlight for studied, gold for mastered
- Click highlighted word → open its vocab lesson
- 📏 Scope: ~1 file, ~50-80 lines
- ✅ *Checkpoint*: Daily Verse shows known words highlighted; clicking opens correct lesson
- ⚙ *Fallback*: If fetch fails, show verse without highlighting

**Phase 5.2 — "Study These Words" button** `[ ]`
- Collect unmastered words from daily verse
- "📚 Study These Words (N)" button → CardQueue flashcard review (Hebrew→gloss, gloss→Hebrew)
- If all mastered, show "All words known! 🎉"
- 📏 Scope: ~1 file, ~50-70 lines
- ✅ *Checkpoint*: Button appears with word count; clicking starts practice session
- ⚙ *Fallback*: If all mastered, skip button

---

### Rollout `[ ]`
- ✅ Commit all changes
- ✅ Run tests: `python3 -m pytest tests/ -q --tb=short --deselect tests/test_api.py::TestHebrewRoutes::test_hebrew_fsrs_review`
- ✅ Frontend build: `cd frontend && npm run build`
- ✅ Deploy: `bash scripts/deploy.sh`
- ✅ Verify each track's checkpoint live on scriptureengine.org
