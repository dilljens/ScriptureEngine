# Card-Based Learning System

> **Status:** Phase 1-2 built, Phase 3-7 planned
> **Inspired by:** The Math Academy Way (FIRe, interleaving, mastery learning)

## Design Principle: Separate by Area

Each learning area (Hebrew, Learn, Memorize) owns its own CardQueue instance
with its own cards, its own FSRS schedule, its own backend endpoints.
The CardQueue and CardRenderer are **shared UI components** — each area
chooses which card types it uses:

| Area | Card Types Used | Backend | State |
|------|----------------|---------|-------|
| **Hebrew** | `hebrew_letter`, `vocab`, `drill` | `/api/v1/hebrew/*` | Independent |
| **Learn** | `knowledge`, `drill` | `/api/v1/learn/*`, `/api/v1/assess/*` | Independent |
| **Memorize** | `verse` | `/api/v1/memorize/*` | Independent |

No cross-area merging. No unified queue. Each area's cards stay in their own pipeline.

## Architecture

```
                    Card Sources
    ┌───────────┬──────────┬───────────┬──────────┬──────────┐
    │  Lesson   │   Verse  │  Hebrew   │  Graph   │  Study   │
    │  Content  │  Memory  │  Vocab    │  Conn's  │  Steps   │
    └─────┬─────┘────┬────┘─────┬─────┘────┬─────┘────┬─────┘
          │          │          │          │          │
          └──────────┴────┬─────┴──────────┴──────────┘
                          │
              ┌───────────▼───────────┐
              │    Card Factory        │  ← card-factory.js
              │   (type dispatch)      │     converts any content → cards
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │      CardQueue         │  ← CardQueue.jsx
              │  - one card at a time  │     generic queue engine
              │  - click to reveal     │
              │  - FSRS rating (1-4)   │
              │  - progress tracking   │
              │  - completion screen   │
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │    CardRenderer       │  ← CardRenderer.jsx
              │  type-specific render │     8 card types
              └───────────┬───────────┘
                          │
              ┌───────────▼───────────┐
              │   Rating → FSRS-5     │
              │   → FIRe credit flow  │  ← future: unified backend
              └───────────────────────┘
```

## What's Built

### Phase 1: CardQueue Engine ✅
- `CardQueue.jsx` — generic queue: show one card, click to reveal, rate 1-4, auto-advance
- Progress bar, type badges, completion screen with per-rating breakdown
- Keyboard support (Space/Enter to flip)

### Phase 2: Card Type Registry ✅
8 card type renderers in `CardRenderer.jsx`:

| Type | Front (prompt) | Back (answer) | Source |
|------|---------------|---------------|--------|
| `verse` | "Recall this verse…" | Full verse text | Memorize queue |
| `knowledge` | Question/prompt | Answer + explanation | Wiki articles, lessons |
| `connection` | "Which verse connects to X?" | Target verse + type + strength | Graph connections |
| `gematria` | "What is the value?" | Value + meaning | Gematria data |
| `vocab` | Hebrew/Greek word | Definition + transliteration + lemma | Lexicon |
| `drill` | Multiple-choice question | Correct answer + explanation | Verb drills |
| `study_step` | Study step explanation | Connections + choices | Study guides |
| `hebrew_letter` | Letter display | Name + transliteration + classification | Hebrew curriculum |

### Phase 3: Card Factory ✅
- `card-factory.js` — converts any content → generic card array
- `lessonToCards(module)` — Learn module questions
- `wikiToCards(articles)` — Wiki entity articles  
- `hebrewToCards(nodes)` — Hebrew curriculum nodes
- `connectionsToCards(sourceVerse, connections)` — Graph connections
- `gematriaToWords(words)` — Gematria words
- `studyToCards(study)` — Study guide steps
- `drillsToCards(drills)` — Hebrew verb drills

### Integration
- `MemorizeView.jsx` refactored to use CardQueue
- Backwards compatible: old MemorizeQueue component still renders

## What's Planned (Phases 3-7)

### Phase 3: LearnView → CardQueue ✅ COMPLETE
- LearnView's practice mode now uses CardQueue with `learn_question` card type
- Supports both MC (select option → reveal correct) and open-ended (textarea → LLM grading → reveal)
- `lessonToCards()` in card-factory converts module questions to cards
- New `LearnQuestionRenderer` card type in CardRenderer handles the full Learn UX
- Rating submits to `/api/v1/learn/modules/{id}/practice` endpoint
- Independent queue — no mixing with Hebrew or Memorize

### Phase 4: HebrewLearnView → CardQueue ✅ COMPLETE
- "Review Mode" button converts unlocked Hebrew nodes into `hebrew_letter`/`vocab` cards
- Uses `hebrewToCards()` from card-factory
- Rating submits to `/api/v1/hebrew/fsrs/review` endpoint
- Independent queue — separate from Learn and Memorize

### Phase 5: MemorizeView Connection Cards (~4h)
- Optional: from a verse in the memorize queue, generate `connection` cards
- "Which verse connects to Psalm 23 via direct_quotation?"
- Stays within MemorizeView's CardQueue — doesn't merge with Hebrew or Learn
- Uses graph API: `/api/v1/connections/{verse}`

### Phase 6: Within-Area Hebrew Interleaving ✅ COMPLETE
- `interleaveCards()` utility in card-factory.js — takes multiple card arrays, interleaves by type with max 2 consecutive of same type, round-robin with fallback
- HebrewLearnView "Review" button now loads BOTH hebrew_letter/vocab cards from curriculum AND drill cards from verb-drill endpoint, interleaves them in one session
- Hebrew learner sees: letter → vocab → drill → letter → vocab → drill (no two of same type in a row)
- Independent queue — stays within Hebrew area, no cross-area mixing

### Phase 7: Per-Area FSRS + FIRe (~6h)
- Hebrew area already has its own FSRS + FIRe (done)
- Learn area: add FSRS scheduling to practice question history
- Memorize area: already has FSRS-5 (done)
- FIRe stays per-area: Hebrew FIRe flows through knowledge graph edges,
  Memorize FIRe flows through connection graph edges — **never cross-area**

### Phase 7: Within-Area Interleaving (~4h)
- Hebrew: mix `hebrew_letter` + `vocab` + `drill` cards in one session
- Learn: mix `knowledge` + `drill` cards
- Memorize: mix `verse` + `connection` cards
- Each area interleaves its own card types — no cross-area mixing
- Prevent blocking: max 2 consecutive of same type within a session
