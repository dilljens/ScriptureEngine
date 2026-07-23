# Plan: Flashcard-Only Hebrew Learning

**Informed by:** The Math Academy Way (micro-scaffolding, worked examples → active practice) + Anki/Duolingo/Memrise language learning patterns (compact intro + SRS retrieval).

**Files changed:** 2 (both frontend JSX)
**Lines changed:** ~280 removed, ~30 changed

---

## Phase 1: Fix HebrewLessonView layout — compact intro → flashcards

**File:** `frontend/src/components/HebrewLessonView.jsx`

**Current flow (broken):**
1. Lesson content in 3 redundant blocks: explanation + key_points + worked_examples
2. Broken KP1/KP2/KP3 badges (never implemented — clicking does nothing)
3. Timed batch drills with countdown timers and auto-fail
4. "Flashcards" toggle button hidden in header

**New flow (compact intro → flashcards):**
1. **Header**: back button, title, level/category badge, audio play
2. **Consolidated explanation**: Show ONLY `explanation` text (remove separate key_points and worked_examples sections — they repeat the same info). One clean block.
3. **Verse attestations**: Below explanation (keep as-is)
4. **CardQueue flashcards**: Immediately after, no toggle needed — always starts in flashcard mode

**Remove (~280 lines):**
- Key points display section (lines ~573–585)
- Worked examples display section (lines ~587–605)
- KP1/KP2/KP3 badge row (lines ~517–531) — broken dead UI
- "Flashcards" toggle button (line ~508)
- Progress/speed bar (lines ~688–701)
- All batch-based timed practice rendering + submit/next logic (lines ~704–893)
- Timer system (useEffects with `timersRef`, time-outs)
- Remediation system (lines ~858–876)
- Hebrew keyboard overlay (lines ~902–917)
- State fields: `batch`, `batchSize`, `answers`, `submitted`, `timedOut`, `responseTimes`, `startTimes`, `kpState`, `currentKP`, `remediation`, `showKeyboard`, `keyboardTarget`, `audioRef`
- `flashcardMode` state — now always flashcard mode

**Keep (~55 lines):**
- Node + practice items loading (useEffect)
- Header (back button, title, category badge, audio play)
- Prerequisites links
- `handleFlashcardRate` (simplified)
- `playAudio` for Hebrew audio
- CardQueue rendering with `practiceToCards`
- **Sort practice items by `difficulty` ascending** before passing to CardQueue — MC (0.3) first, recall (0.5) next, typing (0.7) last. Math Academy scaffolding: easy → hard.
- Empty state when no practice items

**📏 Scope:** 1 file, ~280 lines removed, ~55 rewired.

**✅ Checkpoint:** Opening any lesson shows: [Back button] [Title] [Audio] → [explanation in one block] → [verse attestations] → [CardQueue flashcards]. No KP badges. No timers. No drills.

**⚙ Fallback:** If `practice` array is empty, show compact intro + "No practice items yet" with back button.

---

## Phase 2: Simplify Hebrew letter card to Anki-style

**File:** `frontend/src/components/CardRenderer.jsx`

**Component:** `HebrewLetterCardRenderer` (lines ~594–612)

**Before:** Shows on back: name + transliteration + classification + example

**After (Anki-style):**
- Front: Hebrew letter (large, centered — unchanged)
- Back: name + transliteration only

Remove `classification` and `example` from the back display. These add visual noise in a flashcard recall context.

**📏 Scope:** 1 component, ~10 lines changed.

**✅ Checkpoint:** Consonant card shows letter on front, only name + transliteration on back.

**⚙ Fallback:** If transliteration is empty, show just name.

---

## Files NOT changed
- `HebrewLearnView.jsx` — dashboard stays as-is (user confirmed)
- Any backend files (API, DB, seeds, mcp_server)
- `card-factory.js`, `CardQueue.jsx`
- `HebrewQuiz.jsx`, `HebrewVerbDrill.jsx` — accessible from dashboard

## Math Academy Principles Applied
| Principle | How We Apply It |
|-----------|----------------|
| **Worked example → active practice** | Compact intro (letter + name + sound) IS the worked example. CardQueue is the active practice. |
| **Micro-scaffolding** | Practice items sorted by difficulty ascending: MC (0.3) → recall (0.5) → typing (0.7). No gating yet, but order guides progression. |
| **Mastery learning** | CardQueue's FSRS rating (Again/Hard/Good/Easy) + `/hebrew/progress` API tracks mastery per node. You don't advance in curriculum without mastering prerequisites. |
| **Spaced retrieval** | Existing FSRS-5 + `/hebrew/review-queue` serves interleaved reviews on due items. |
| **Non-interference** | Existing: confusable pairs are spaced apart in the review queue. |

**Not applied (future work):** Hard mastery gating (must pass MC before recall unlocks), timed automaticity quizzes.

## Research References (in findings)
- The Math Academy Way (micro-scaffolding, worked example effect, expertise reversal)
- Anki Hebrew letter decks (Algorithmist's Hebrew alephbet, Hebrew Alphabet with vowels)
- Duolingo Hebrew (immersion-first, no in-flow explanations)
- Memrise (show → test, no explanation text)
