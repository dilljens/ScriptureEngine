# Progress: Flashcard-Only Hebrew Learning

**Status: PLAN FINALIZED — Ready for Execution**

## Phase 1: Fix HebrewLessonView layout — compact intro → flashcards
- [ ] `frontend/src/components/HebrewLessonView.jsx`
  - [ ] Consolidate lesson content to one block (explanation only, remove key_points + worked_examples)
  - [ ] Remove KP1/KP2/KP3 badge row (broken dead UI)
  - [ ] Remove timed batch practice system + timers
  - [ ] Remove progress bar, remediation, keyboard overlay
  - [ ] Remove "Flashcards" toggle (always flashcard mode)
  - [ ] Sort practice items by difficulty ascending (Math Academy scaffolding: MC 0.3 → recall 0.5 → typing 0.7)
  - [ ] Clean up unused state variables
  - [ ] Always show CardQueue after content

**Checkpoint:** Lesson opens with: explanation block → verse attestations → CardQueue flashcards. No KP badges, no timers, no drill mode toggle.

---

## Phase 2: Simplify letter card rendering
- [ ] `frontend/src/components/CardRenderer.jsx` — `HebrewLetterCardRenderer`: remove classification and example from back; show only name + transliteration

**Checkpoint:** Letter card front = letter, back = name + transliteration only.

---

## Blockers
None.
