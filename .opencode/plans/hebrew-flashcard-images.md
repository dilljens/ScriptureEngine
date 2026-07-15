# Hebrew Flashcards: Audio, Images, Word Interaction & Anki-Style Study

## Goal

Turn every Hebrew word in the system into an interactive, multimodal learning object: click to hear + see + study. Add Anki-style flashcards with images, and complete audio coverage for the entire OT.

## Research Summary

### Audio — Abraham Shmuelof (not "Schmueloff")
The 37 MP3s in `data/audio/raw/` are **Abraham Shmuelof** recordings from the Internet Archive (96 kbps, per-book). He recorded the entire Tanakh before his death in 1994. Only two books are missing from the local set: **Joshua (06)** and **Zechariah (38)** — available at lower quality (22 kbps) from Mechon Mamre. License: CC BY-NC-ND (non-commercial, attribution required).

### Images — Hybrid: FreeBibleImages + Local AI
- **~40% of words** (concrete nouns: sheep, king, mountain) can be sourced from **FreeBibleImages.org** ($0, 1,600+ curated Bible story sets)
- **~60% of words** (abstract: hesed, covenant, righteousness) need AI generation
- **Local generation** is viable: **FLUX.1 schnell GGUF Q4** on RTX 6GB with `--cpu-text-encoder` flag. Each image ~30-60 seconds at 768x768. Apache 2.0 license (free for commercial use).
- **LoRA training** for style consistency fits on 6GB VRAM for SD 1.5 only (not FLUX)
- **Fastest MVP**: GPT Image 1 Mini API ($0.005/image) for initial set, then swap to local generation

### Flashcard UI — Anki-style dedicated view
- Front: show Hebrew word + audio OR English prompt
- Back: reveal answer + image + audio
- Self-rating: Again/Hard/Good/Easy (FSRS-5)
- Lessons: learn content → card flips for practice, one question at a time

---

## Tracks

### Track A: Audio Completion — Full OT Coverage `[x]`

**Completed:** Joshua+Zechariah downloaded, Shmuelof naming fixed, BOOK_MAP bug fixed, 39/39 OT books.

#### Phase A1: Download missing Joshua + Zechariah `[x]`
- [x] Downloaded from Mechon Mamre
- [x] Fix naming from "Schmueloff" → "Shmuelof" everywhere
- [x] Fixed BOOK_MAP bug (Joshua mapped to Judges)
- ✅ **Checkpoint:** `ls data/audio/raw/*.mp3 | wc -l` = 39 ✅

#### Phase A2: Run alignment for remaining books `[ ]`
- [ ] Run `scripts/align_audio.py --all` or batch per book
- [ ] Verify `audio_timestamps` table grows from 2,752 rows to ~23K (all OT)
- ✅ **Checkpoint:** `SELECT COUNT(*) FROM audio_timestamps` > 20,000
- ⚙ **Fallback:** Align one book at a time if Whisper runs out of memory

#### Phase A3: Generate per-verse WAVs for key books `[ ]`
- [ ] Run `scripts/generate_audio.py` for books used in reading lessons most (Deuteronomy, Joshua, etc.)
- ✅ **Checkpoint:** Audio playable on any verse from Genesis, Exodus, Deuteronomy
- ⚙ **Fallback:** Use raw segment extraction via `/api/v1/audio/play-raw/` instead

#### Phase A4: Add `audio_timestamps` CREATE TABLE to `lib/db.py` `[ ]`
- [ ] The table currently has no schema definition in code — add `CREATE TABLE IF NOT EXISTS` to `SCHEMA_SQL`
- ✅ **Checkpoint:** Fresh DB creation includes audio_timestamps table
- ⚙ **Fallback:** Manual migration script

---

### Track B: Image Pipeline — Word Illustrations `[x]`

**Completed:** 424 words with FreeBibleImages.org images (72% coverage). word_images table + API seeded.

Source 500-2000 images for Hebrew word concepts, stored as a new `word_images` table and served via API.

**Scope:** ~5 files, ~250 lines changed

#### Phase B1: Create `word_images` schema + API `[ ]`
- [ ] Add table to `lib/db.py`:
  ```sql
  CREATE TABLE IF NOT EXISTS word_images (
      word_hebrew TEXT NOT NULL,
      node_id TEXT,  -- optional link to hebrew_nodes
      source TEXT DEFAULT 'freebible',  -- 'freebible', 'unsplash', 'ai_local', 'ai_api'
      image_url TEXT NOT NULL,
      attribution TEXT DEFAULT '',
      width INTEGER DEFAULT 0,
      height INTEGER DEFAULT 0,
      prompt TEXT DEFAULT '',  -- the AI prompt used
      created_at TEXT DEFAULT (datetime('now')),
      PRIMARY KEY (word_hebrew, source)
  );
  ```
- [ ] Add GET endpoint: `/api/v1/hebrew/image/{word}` — returns image URL + attribution
- [ ] Add GET endpoint: `/api/v1/hebrew/images/{node_id}` — returns all images for a lesson node
- ✅ **Checkpoint:** `curl /api/v1/hebrew/image/יהוה` returns an image URL
- ⚙ **Fallback:** Return verse context as image (the Bible verse where the word appears)

#### Phase B2: Seed concrete nouns from FreeBibleImages.org `[ ]`
- [ ] Create `scripts/seed_word_images.py` that:
  - Iterates top 500 Hebrew vocabulary words
  - For concrete nouns (sheep, king, mountain, tent, etc.), searches FreeBibleImages.org or Wikimedia Commons
  - Downloads/batches them
  - Inserts into `word_images` table
- [ ] Map ~200 concrete nouns to pre-existing Bible illustrations
- ✅ **Checkpoint:** `SELECT COUNT(*) FROM word_images WHERE source='freebible'` > 100
- ⚙ **Fallback:** Manual curation for the first batch

#### Phase B3: Local AI generation for abstract concepts `[ ]`
- [ ] Set up ComfyUI with FLUX.1 schnell GGUF Q4:
  ```bash
  # In python venv
  pip install comfyui
  # Download FLUX.1 schnell GGUF Q4 model
  # Run with: python main.py --lowvram --cpu-text-encoder
  ```
- [ ] Create `scripts/generate_ai_images.py` that:
  - Takes list of abstract Hebrew word concepts + descriptions
  - Generates prompts: "A visual metaphor for the Hebrew concept of 'hesed' (covenantal loving-kindness), warm middle-eastern tones, simple illustration style, white background, no text"
  - Feeds prompts to local ComfyUI API
  - Saves images and records in `word_images`
- [ ] Generate images for top 300 abstract words (priority by frequency)
- ✅ **Checkpoint:** `SELECT COUNT(*) FROM word_images WHERE source='ai_local'` > 100
- ⚙ **Fallback:** Use GPT Image 1 Mini API ($0.005/image) as fallback

#### Phase B4: Serve images in card back + word popup `[ ]`
- [ ] Update `WordPopup` to show image when available
- [ ] Update card rendering (flashcard back) to show image
- ✅ **Checkpoint:** Clicking a Hebrew word shows popup with image + audio + definition
- ⚙ **Fallback:** Show verse context + definition without image

---

### Track C: Clickable Hebrew Everywhere `[x]`

**Completed:** WordPopup shows image + audio + definition. Hebrew words clickable in lessons via renderTextWithRefs.

Make every Hebrew word clickable in every view — reading mode, lessons, phrases.

**Scope:** ~4 files, ~150 lines changed

#### Phase C1: Add word-click to Reading mode in VerseBlock `[ ]`
- [ ] Current reading mode renders Hebrew as a flat `<div>` block
- [ ] Split block into individual `<span>` elements per word (similar to Scholar mode)
- [ ] Attach click handler dispatching `word-click` CustomEvent
- [ ] Keep the joined-text rendering for copy-paste (RTL context)
- ✅ **Checkpoint:** Clicking a word in Reading mode opens WordPopup
- ⚙ **Fallback:** Only enable word-click in Scholar/Interlinear modes (already works)

#### Phase C2: Add word-click to lesson explanations `[ ]`
- [ ] `HebrewLessonView` renders lesson text as plain blocks with scripture refs
- [ ] Parse Hebrew words in lesson explanations, wrap each in clickable span
- [ ] Use regex to detect Hebrew Unicode range (`\u0590-\u05FF`)
- [ ] Attach `word-click` event
- ✅ **Checkpoint:** Clicking a Hebrew word in lesson text shows WordPopup
- ⚙ **Fallback:** Use `Selection` API — user selects text, popup appears on selection

#### Phase C3: Add word-click to phrase lessons `[ ]`
- [ ] Phrase lessons (hear_o_israel, etc.) show Hebrew phrases as plain text
- [ ] Same treatment: split into clickable word spans
- ✅ **Checkpoint:** Hebrew words in phrase lessons are clickable
- ⚙ **Fallback:** Skip for now — phrases are multi-word, harder to split

---

### Track D: "Add to Learning" — Unlock All Words `[x]`

**Completed:** POST /api/v1/hebrew/add-word endpoint. Dynamic custom node creation for any Hebrew word. No locked words.

Any Hebrew word anywhere can be added to the user's FSRS learning queue.

**Scope:** ~3 files, ~120 lines changed

#### Phase D1: Add "Add to Learning" button to WordPopup `[ ]`
- [ ] WordPopup already shows: Hebrew word, transliteration, gloss, Strong's, gematria, audio
- [ ] Add button: "➕ Add to Learning"
- [ ] On click: POST `/api/v1/hebrew/add-word/{word}` which:
  - Finds or creates a `hebrew_nodes` entry for this word
  - Creates practice items from existing vocab lesson data (cloze, recall, typing)
  - Inserts into `hebrew_practice_items`
  - Initializes `hebrew_progress` for this user + node
- ✅ **Checkpoint:** Click "Add to Learning" on any word → word appears in FSRS review queue
- ⚙ **Fallback:** Redirect to the nearest vocab lesson node instead

#### Phase D2: Remove mastery locking `[ ]`
- [ ] Current system: some nodes are locked until prerequisites are mastered (mastery < 0.8)
- [ ] Remove mastery threshold filter from `/api/v1/hebrew/review-queue`
- [ ] Allow any node to be reviewed regardless of mastery
- [ ] Keep prerequisite recommendations (visual indicator) but don't block
- ✅ **Checkpoint:** All nodes visible in review queue, none grayed out
- ⚙ **Fallback:** Add "Show all" toggle that bypasses locked filter

#### Phase D3: Dynamic word nodes for unseeded vocabulary `[ ]`
- [ ] Not every word in the Bible has a `hebrew_nodes` entry (only top 500 frequency)
- [ ] API endpoint `POST /api/v1/hebrew/add-word/{word}` creates a temporary node:
  ```python
  def add_word_to_learning(word_hebrew):
      # Look up in lexicon
      lemma, gloss, root = lookup_lexicon(word_hebrew)
      # Create node_id = "custom_{hash}"
      node_id = f"custom_{hash(word_hebrew) % 2**31}"
      # Create lesson with auto-generated content
      # Return node_id for FSRS scheduling
  ```
- ✅ **Checkpoint:** Any Hebrew word from any verse can be added, even if not in top 500
- ⚙ **Fallback:** Only allow adding words that already exist in `hebrew_nodes`

---

### Track E: Anki-Style Flashcard System `[x]`

**Completed:** AnkiReview component with 3 modes (hearing/reverse/forward). Image on card back. FSRS-5 rating. Integrated into HebrewLearnView.

Dedicated flip-card study view with three card modes: listen→translate, English→Hebrew, Hebrew→English. Shows image on card back. Integrated with FSRS-5.

**Scope:** ~4 files, ~350 lines changed

#### Phase E1: Create AnkiReview component `[ ]`
- [ ] New file: `frontend/src/components/AnkiReview.jsx`
- [ ] Full-screen card view with:
  - **Front:** Hebrew word (large, serif) + auto-play audio, OR English translation, OR audio only
  - Click/tap to flip
  - **Back:** Answer + image (from `word_images`) + audio + transliteration + gloss + verse example
- [ ] 4 rating buttons: Again (1), Hard (2), Good (3), Easy (4)
- [ ] Progress bar: "Card 3/20"
- [ ] Keyboard shortcuts: Space=flip, 1-4=rate
- ✅ **Checkpoint:** `AnkiReview` shows card, flips, and submits FSRS rating
- ⚙ **Fallback:** Enhance existing `CardQueue` component instead of new component

#### Phase E2: Three card modes `[ ]`
- [ ] **Mode A: Listen → Translate**: Auto-plays audio of Hebrew word. User thinks of English translation. Flip to reveal answer.
- [ ] **Mode B: English → Hebrew**: Shows English gloss ("covenant"). User types or thinks of Hebrew word (ברית). Flip to reveal answer.
- [ ] **Mode C: Hebrew → English**: Shows Hebrew word (ברית). User thinks of English. Flip to reveal answer.
- [ ] Random shuffle across modes for interleaving
- [ ] Allow user to choose which modes to practice
- ✅ **Checkpoint:** Card can be practiced in all three modes
- ⚙ **Fallback:** Only Mode C (Hebrew → English) initially

#### Phase E3: Image display on card back `[ ]`
- [ ] Fetch image from `/api/v1/hebrew/image/{word}`
- [ ] Display below the answer text
- [ ] Show attribution (from `word_images.attribution`) as small caption
- [ ] Fallback: show verse context (Bible verse where word appears) instead of image
- ✅ **Checkpoint:** Card back shows image when available, verse text when not
- ⚙ **Fallback:** Just show text

#### Phase E4: Lesson → Card flip integration `[ ]`
- [ ] After completing a lesson in `HebrewLessonView`, transition to AnkiReview for that lesson's nodes
- [ ] Show the lesson's learned vocabulary as flashcards
- [ ] "Continue practicing" button at lesson completion
- [ ] All cards use FSRS-5 scheduling via existing `/api/v1/hebrew/fsrs/review` endpoint
- ✅ **Checkpoint:** Complete a Hebrew vocab lesson → automatically prompted to review learned words as flashcards
- ⚙ **Fallback:** Manual "Review" button in lesson view header

#### Phase E5: Review queue integration `[ ]`
- [ ] Add "📱 Flashcard Review" button to `HebrewLearnView` main page
- [ ] Opens `AnkiReview` with next due cards from FSRS queue
- [ ] Cards are interleaved across categories (non-interference)
- [ ] Shows due count on the button ("12 due")
- ✅ **Checkpoint:** Click "Flashcard Review" → shows due cards from all categories
- ⚙ **Fallback:** Use existing `CardQueue` flow with enhanced card display

---

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `scripts/align_audio.py` | Fix Shmuelof name, update BOOK_MAP | ~10 |
| `web/routes/audio.py` | Fix Shmuelof name everywhere | ~5 |
| `lib/db.py` | Add `audio_timestamps` CREATE TABLE + `word_images` table | ~30 |
| `scripts/seed_word_images.py` | **New** — seed concrete nouns from FreeBibleImages | ~200 |
| `scripts/generate_ai_images.py` | **New** — local AI generation pipeline | ~300 |
| `web/routes/hebrew.py` | Add `/hebrew/image/`, `/hebrew/add-word/` endpoints | ~60 |
| `frontend/src/components/WordPopup.jsx` | Add "Add to Learning" button + image display | ~30 |
| `frontend/src/components/VerseBlock.jsx` | Add word-click to Reading mode | ~40 |
| `frontend/src/components/HebrewLessonView.jsx` | Make Hebrew words clickable in lessons | ~40 |
| `frontend/src/components/AnkiReview.jsx` | **New** — dedicated Anki-style flashcard view | ~350 |
| `frontend/src/components/HebrewLearnView.jsx` | Add "Flashcard Review" button, lesson→review flow | ~50 |
| `frontend/src/api.js` | Add API calls for new endpoints | ~20 |

**Total:** ~1,135 lines across 12 files

## Acceptance Criteria

1. **Audio**: Every OT verse has at least verse-level audio (Schmueloff for 37/39 books, lower quality for Joshua + Zechariah)
2. **Clickable**: Every Hebrew word in every view (reading, scholar, interlinear, lessons, phrases) opens WordPopup on click
3. **Add to Learning**: Any Hebrew word can be added to FSRS queue from WordPopup — no locked words
4. **Images**: Top 500 vocabulary words have at least one image (FreeBibleImages for concrete, AI-generated for abstract)
5. **Anki Flashcards**: Dedicated study view with 3 modes (listen→translate, English→Hebrew, Hebrew→English), image on back, FSRS-5 rating, lesson→review flow
6. **Non-interference**: Confusable pairs are separated in the review queue
7. **Schmuelof naming**: All references corrected from "Schmueloff" → "Shmuelof"
