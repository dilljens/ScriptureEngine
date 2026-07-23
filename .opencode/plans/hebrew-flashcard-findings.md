# Findings: Flashcard-Only Hebrew Learning

## Quality Baseline
- **sentrux quality signal**: 0.4212 (recorded before plan creation)
- **Files**: 1295 | **Import edges**: 566 | **Lines**: 410,772

## Research Synthesis

### The Math Academy Way — Lesson Structure
- Each lesson = Introduction → Worked Example (KP1) → Practice → Worked Example (KP2) → Practice → ...
- The "worked example" IS the instruction — a demonstration, not a wall of text
- Active practice follows immediately after each worked example
- Multiple KPs scaffold difficulty: simplest case → progressively harder
- Key principle: cognitive load minimization through micro-scaffolding
- The expertise reversal effect: beginners need direct instruction + worked examples; scaffolding removed as expertise grows

### Language Learning Platforms — How They Teach Letters
| Platform | Explanation in flow? | Card format |
|----------|---------------------|-------------|
| **Anki** | ❌ No explanation text | Letter → Name, Letter → Pronunciation, Name → Writing (multi-card per note) |
| **Duolingo** | ❌ No explanation in flow (Tips in separate tab) | Pure exercise immersion (matching → selection → translation) |
| **Memrise** | ❌ No explanation text | Show (item + audio + image) → Test (MC → typing) |
| **Clozemaster** | ✅ AI "Explain" button (optional layer) | Cloze sentence + SRS |

**Common pattern:** Letter + name + sound + (optional example word). That's all. No paragraph explanations. No key points lists. Audio is standard. Mnemonics are optional extras.

### Why Our Current System Fails

1. **Triple-redundant lesson content**: The same info is shown three ways:
   - `explanation` (paragraph) — already complete
   - `key_points` (bullet list) — restates the same facts
   - `worked_examples` (Q&A format) — rephrases the same content
   This creates a wall of text, and the last two blocks add no new information.

2. **KP badges are broken**: The KP1/KP2/KP3 badges were designed to gate progression from recognition → recall → production, but the gating logic was never implemented. Clicking them does nothing. They are dead UI.

3. **Timed batch drills are overwhelming**: Countdown timers, auto-fail on timeout, multi-KP scaffolding gates — high pressure for what should be low-stakes letter learning.

4. **Flashcard mode hidden**: The simpler, more effective CardQueue mode is behind a toggle that users have to discover.

### What Anki-Inspired Hebrew Letter Cards Look Like
From the most popular Anki shared decks (Algorithmist's Hebrew alephbet, Hebrew Alphabet with vowels):

| Front | Back |
|-------|------|
| א | Alef — silent glottal stop, vowel carrier |
| ב | Bet — 'b' sound (b), 'v' without dagesh |

No classification label. No "example" field. Just letter → name + pronunciation.

## Changes Required

### HebrewLessonView.jsx
- Consolidate lesson content into ONE block: show `explanation` only (remove separate key_points and worked_examples sections — they're redundant)
- Remove KP1/KP2/KP3 badge row (broken — never implemented)
- Remove "Flashcards" toggle button (no longer needed)
- Remove ALL timed batch drill rendering (~200 lines)
- Remove timer system, progress bar, remediation, keyboard overlay
- Keep verse attestations below explanation
- Always show CardQueue flashcards after content

### CardRenderer.jsx — HebrewLetterCardRenderer
- Front: Hebrew letter (unchanged)
- Back: Only name + transliteration (remove classification and example)

## Non-Changes
- HebrewLearnView dashboard stays intact (user confirmed)
- All backend API routes continue serving data
- No database schema changes
- Seed data stays unchanged (frontend simply stops rendering the redundant sections)
