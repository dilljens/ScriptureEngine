# Project: Hebrew Learning & UI Fixes

Goal: Fix all reported Hebrew learning issues — broken audio, practice content quality, missing keyboard vowels, memorize review, top-bar tab naming, and navigation UX.

## Requirements
- [x] R1: Clarified verse click behavior → quick review popup
- [x] R2: Clarified top bar → show tab label only for non-chapter views
- [x] R3: Clarified keyboard vowels → toggle row + long-press
- [x] R4: Clarified audio → pre-generate letter sounds via OmniVoice cloning from Schmueloff recordings
- [x] R5: Clarified practice items → full audit of all 428
- [x] R6: Clarified navigation → keep arrows + add nav/command button

## Pre-resolved Decisions
- Audio: Use existing OmniVoice pipeline (`k2-fsa/OmniVoice`) with voice cloning via `schmueloff_8s.wav`
- Keyboard: Extra vowel toggle row + long-press popup on consonants
- Top bar: Replace breadcrumb with tab label when `view !== 'chapter'`
- Memorize click: Single-card CardQueue popup for verse in queue
- Practice items: Python migration script to fix all question_text entries
- Navigation: Add command palette trigger button to toolbar

---

## Track A: Audio & Letter Pronunciation `[ ]`

### Phase A1: Generate letter audio files via OmniVoice `[ ]`
- [ ] Write `scripts/generate_letter_audio.py` (patterned after `generate_audio.py`)
  - Load OmniVoice model with voice cloning from `schmueloff_8s.wav`
  - For each letter (consonants + vowels): generate `{letter_id}.wav`
  - Output to `data/audio/letters/`
- [ ] Verify generated files play correctly with consistent volume/normalization
- 📏 Scope: 1 new script, ~100 lines
- ✅ Checkpoint: `ls data/audio/letters/*.wav | wc -l` ≥ 47
- ⚙ Fallback: If OmniVoice model not available, use gTTS/espeak as fallback

### Phase A2: Update audio endpoint for letter fallback `[ ]`
- [ ] Modify `get_hebrew_audio` in `web/routes/hebrew.py`
  - After existing DB/alignment lookups fail, check `data/audio/letters/{word}.wav`
  - Return audio URL pointing to a new `/api/v1/audio/letter/{letter_id}` endpoint
  - Add the letter audio serving endpoint
- 📏 Scope: ~1 file, ~20 lines changed
- ✅ Checkpoint: `curl /api/v1/hebrew/audio/aleph` returns audio_url
- ⚙ Fallback: Serve via static file route instead of custom endpoint

---

## Track B: Practice Item Content Quality `[ ]`

### Phase B1: Audit and fix all 428 practice items `[ ]`
- [ ] Write `scripts/audit_practice_items.py` that:
  - Reads all items from `hebrew_practice_items`
  - For letter nodes (consonant, vowel categories): fix question_text so the answer is not given away
    - `multiple_choice`: Show Hebrew character (e.g. "ע"), options are letter names (no answer in question)
    - `transliteration`: Show Hebrew character, ask for transliteration
    - `typing`: Show letter name, ask to type Hebrew character (or vice versa)
    - `recall`: Vary front/back — sometimes show Hebrew ask name, sometimes show name ask Hebrew
  - For vocabulary/verb/noun nodes: check question_text doesn't reveal the answer, check options_json doesn't include the correct answer as distractors
  - For grammar/syntax/phrase nodes: review for pedagogical soundness
- [ ] Run the migration against `data/memorize.db`
- [ ] Manual spot-check of 10+ items across different categories
- 📏 Scope: 1 new script, ~200 lines
- ✅ Checkpoint: All 8 `ayin` items have question_text that doesn't contain "Ayin" in a way that gives away the answer
- ⚙ Fallback: Roll back via git if migration corrupts data

---

## Track C: Hebrew Keyboard Vowels `[ ]`

### Phase C1: Add vowel toggle row to HebrewKeyboard `[ ]`
- [ ] Add state `[showVowels, setShowVowels] = useState(false)` to HebrewKeyboard
- [ ] Add vowel buttons row (hidden by default): ְ ֻ ֹ ִ ֶ ַ ָ ֵ ּ ֶ ֱ ֲ ֳ
- [ ] Add "Niqqud" toggle button between rows
- [ ] Style vowel buttons smaller than consonants, different color
- 📏 Scope: 1 file (`HebrewKeyboard.jsx`), ~30 lines changed
- ✅ Checkpoint: Vowel toggle visible and vowels appear in the typed text when activated
- ⚙ Fallback: Keep as separate toggle button only, skip long-press

### Phase C2: Add long-press vowel popup on consonants `[ ]`
- [ ] Implement long-press detection (500ms `onPointerDown` + timer)
- [ ] When long-press fires on a consonant, show a small popup above the pressed key with common vowel variants for that letter
- [ ] On selecting a vowel from popup, insert consonant+vowel combined character
- [ ] Dismiss popup on pointer up / selection / timeout
- 📏 Scope: 1 file (`HebrewKeyboard.jsx`), ~40 lines changed
- ✅ Checkpoint: Long-pressing "ב" shows vowel options, selecting "ַ" inserts "בַ"
- ⚙ Fallback: Only implement toggle row (Phase C1), skip long-press

---

## Track D: Memorize Verse Click & Review `[ ]`

### Phase D1: Add click-to-review on queue verse `[ ]`
- [ ] Add state to MemorizeQueue: `[reviewVerse, setReviewVerse] = useState(null)`
- [ ] Add `onClick` handler to verse card in queue list → `setReviewVerse(v)`
- [ ] When `reviewVerse` is set, show a CardQueue with that single verse
- [ ] On rating complete, go back to queue view and refresh
- [ ] Add "Read in context" link in the review popup → navigates to chapter view
- 📏 Scope: 1 file (`MemorizeQueue.jsx`), ~40 lines changed
- ✅ Checkpoint: Clicking a verse in the queue opens a flashcard for it
- ⚙ Fallback: Navigate to chapter view instead of popup

---

## Track E: Top Bar Tab Labeling `[ ]`

### Phase E1: Show tab name for non-reading views `[ ]`
- [ ] In App.jsx toolbar (around line 1105), add logic:
  - If `view !== 'chapter' && view !== 'book' && view !== 'work'`: show `currentTab.label` instead of breadcrumb
  - Keep the rest of the toolbar (search, menus, arrows) unchanged
- [ ] Ensure tab labels from `openHebrewTab()`, `openWikiTab()`, etc. show correctly
  - Hebrew: "Biblical Hebrew" or "Hebrew: aleph"
  - Wiki: "📖 Wiki" or "Wiki: abraham"
  - Learn: "📚 Learn"
  - Memorize: "Memorize"
- 📏 Scope: 1 file (`App.jsx`), ~15 lines changed
- ✅ Checkpoint: Hebrew tab shows "Biblical Hebrew" in toolbar, not "Old Testament Genesis"
- ⚙ Fallback: Override document.title instead

---

## Track F: Navigation & Command Button `[ ]`

### Phase F1: Add command palette trigger button `[ ]`
- [ ] Add a `?` or `/` button next to (or inside) the SearchBar that dispatches the command palette
- [ ] Or add a dedicated "Nav" dropdown with prev/next/up/down + wiki button
- [ ] Ensure the existing SearchBar command features (`/chat`, `/dark` etc.) are still accessible
- 📏 Scope: 1 file (`App.jsx`), ~10 lines changed
- ✅ Checkpoint: Command/help button visible in toolbar
- ⚙ Fallback: Use hotkey cheatsheet instead of toolbar button

### Phase F2: Add Wiki button to toolbar `[ ]`
- [ ] Add a "📖 Wiki" button in the toolbar area (desktop)
- [ ] On click, calls `openWikiTab()`
- [ ] Already exists in Menu dropdown — making it more prominent
- 📏 Scope: 1 file (`App.jsx`), ~10 lines changed
- ✅ Checkpoint: Wiki button visible in toolbar, clicking opens wiki view
- ⚙ Fallback: Only add via menu, not toolbar

---

## Track G: Verse Ref Formatting `[ ]`

### Phase G1: User-facing verse refs use book names `[ ]`
- [ ] In `HebrewLessonView.jsx` `renderTextWithRefs`, map book IDs to display names
  - `"gen"` → `"Genesis"`, `"exo"` → `"Exodus"`, etc.
  - Import or reference the book title mapping
- [ ] Also fix the verse attestations display (use formatted refs)
- [ ] Keep the dot-format refs only for internal APIs / links
- 📏 Scope: ~2 files, ~30 lines changed
- ✅ Checkpoint: Hebrew lesson shows "Genesis 1:1" not "gen.1.1"
- ⚙ Fallback: Use a simple lookup object instead of DB query

---

## Track H: Scripture Letter Recognition — Hebrew Text `[ ]`

### Phase H1: Display Hebrew text with highlighted letter in attestations `[ ]`
- [ ] In `HebrewLessonView.jsx`, in the verse attestations section (lines 444-482):
  - When `attestation_type === 'letter_recognition'`, display the Hebrew verse text prominently
  - Highlight the target letter in the Hebrew text (e.g., via `<mark>` or colored span)
  - Show English translation below as secondary
- [ ] The `explanation` field already names the word containing the letter (e.g., "The letter Ayin (ע) appears in 'עַל'") — use this to locate the letter
- 📏 Scope: 1 file (`HebrewLessonView.jsx`), ~20 lines changed
- ✅ Checkpoint: Ayin attestation shows "עַל" with the ע highlighted
- ⚙ Fallback: Just show Hebrew text without highlighting
