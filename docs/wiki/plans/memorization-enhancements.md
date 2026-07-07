# Memorization Module Enhancements

**Techniques from The Math Academy Way applied to scripture memorization.**

## Overview

Our existing memorization module (P0-P10) already implements FSRS spaced repetition, memory palaces, progressive hint levels, and audio. The Math Academy Way reveals several enhancements that can dramatically improve retention by leveraging the **scripture connection graph** — our unique advantage over standalone memorization apps.

---

## Enhancement 1: FIRe (Fractional Implicit Repetition) Across Verses

### The Concept

When a user memorizes Verse B that shares words, themes, or connections with already-memorized Verse A, Verse A should get **fractional implicit repetition credit**. The connection graph already encodes these relationships — use them.

### How It Works

```
Memorized: Gen 1:1 ("In the beginning God created the heaven and the earth")
    ─── has `same_lemma` connection ───→ Gen 2:4 (לְהִוָּלְדָ֗ם / generations)

When user memorizes Gen 2:4:
    → Gen 1:1 gets fractional credit proportional to shared content
    → credit = encompassing_weight × connection_strength × (1 - time_since_last_review)
    → If enough credit accumulates, the due review for Gen 1:1 is pushed back
```

### Implementation

| Step | Description |
|------|-------------|
| **F1.1** | Add `fi_re_credit` column to the `cards` table (cumulative fractional repetition credit, 0.0-1.0) |
| **F1.2** | On each verse card review, compute FIRe credit for all connected verses: query the graph for `connected_to(verse_id, min_quality=0.5)`, compute credit per connection |
| **F1.3** | When FIRe credit ≥ 1.0 for a card, "knock out" that due review (extend its interval) |
| **F1.4** | Credit decays over time: `fi_re_credit *= 0.9 ^ days_since` (partial credit fades) |

### Connection-to-Credit Mapping

| Connection Type | encompassing_weight | Why |
|----------------|-------------------|-----|
| `direct_quotation` | 0.8 | Nearly identical text — strong reinforcement |
| `same_lemma` | 0.4 | Shared vocabulary — moderate reinforcement |
| `allusion` | 0.3 | Thematic echo — light reinforcement |
| `parallel_synonymous` | 0.5 | Same idea, different words — good reinforcement |
| `chiastic` | 0.6 | Mirror structure — strong structural reinforcement |
| `type_antitype` | 0.4 | Typological pair — moderate conceptual reinforcement |

### Benefit

Without FIRe, a user memorizing 50 verses that all use the word "covenant" would need separate review for each. With FIRe, reviewing any one of those verses gives partial credit to all others containing "covenant." **Estimated 30-50% reduction in total review time** for interconnected passages.

---

## Enhancement 2: Repetition Compression

### The Concept

When multiple cards are simultaneously due for review, they can be **compressed** into a single combined review task if they share enough structural or thematic relationship. This mimics Math Academy's approach of combining related reviews.

### How It Works

```
Due cards: 
  - Psalm 23:1 (text review)
  - Psalm 23:2 (text review) 
  - Psalm 23:3 (text review)
  
  → Compressed into: "Recite Psalm 23:1-3 from memory"
  → Tests all three at once, one rating applies to all
```

### Compression Rules

| Condition | Action |
|-----------|--------|
| Consecutive verses from same chapter | Compress into "recite passage" |
| Verses sharing same theme (connection graph) | Group thematically |
| Palace loci in same palace | Compress into palace walk segment |
| Same card type on same verse | Single review with combined hints |

### Implementation

| Step | Description |
|------|-------------|
| **RC.1** | In review queue query, detect groups of cards eligible for compression |
| **RC.2** | Create combined review session: user sees all verses, rates each or rates overall |
| **RC.3** | Apply the rating to all cards in the compressed group (with slight discount: 0.9× for being combined) |

### Benefit

Fewer discrete review sessions, more natural "recite from memory" flow. The palace walk mode already does this implicitly — this brings it into normal review.

---

## Enhancement 3: Student-Verse Learning Speeds

### The Concept

Not all verses are equally hard to memorize. A short verse like "Jesus wept" (John 11:35) is much easier than Isaiah 53:5. The FSRS algorithm should calibrate per-student-per-verse using a **difficulty estimate** and **student ability** ratio.

### Difficulty Factors

| Factor | Effect | Data Source |
|--------|--------|-------------|
| Verse length (words) | Longer = harder | Verse table |
| Word rarity (hapax legomena) | Rare words = harder | `generators/hapax_dislegomenon.py` |
| Hebrew vs English | Hebrew = harder (non-native) | Language field |
| Connection density | More connections = easier (more cues) | Connection graph |
| Shared vocabulary with known verses | More shared = easier | Lexicon |
| Prior performance on similar verses | Higher ability on similar = easier | Knowledge state |

### Implementation

```python
def estimate_difficulty(verse_id, student_ability):
    length = verse.word_count
    rare_words = verse.hapax_count
    connections = verse.connection_count
    vocabulary_overlap = compute_vocab_overlap(verse, student.known_verses)
    
    base = 0.3  # minimum difficulty
    base += length * 0.02  # longer = harder
    base += rare_words * 0.1  # rare words = much harder
    base -= connections * 0.01  # connections = easier
    base -= vocabulary_overlap * 0.05  # familiarity = easier
    
    return max(0.1, min(0.9, base))

def learning_speed(student_ability, verse_difficulty):
    return student_ability / verse_difficulty
```

### FSRS Parameter Calibration

| Parameter | Default | Hebrew-specific |
|-----------|---------|-----------------|
| Initial stability | 1.0 | 0.7 (Hebrew verses harder) |
| Difficulty | 5.0 | 7.0 (verbatim recall harder than gist) |
| Target retention | 0.9 | 0.95 (higher stakes for exact wording) |

### Benefit

Hard verses get shorter intervals and more reviews. Easy verses are not over-practiced. The system adapts to each student's unique strengths (some find poetic passages easier, others find narrative easier).

---

## Enhancement 4: Interleaved Review (Not Blocked)

### The Concept

When reviewing due cards, **blocked review** (all of Psalm 23, then all of Romans 8) is easier but less effective. **Interleaved review** (mix Psalm 23, Romans 8, Genesis 1) forces true retrieval because context-switching requires the brain to regenerate the memory trace from scratch.

### Current vs Enhanced

| Current | Enhanced |
|---------|----------|
| Cards sorted by due date | Cards shuffled by topic |
| Consecutive verses from same passage grouped | Same-passage verses spaced apart |
| User can predict "what's next" | User must identify each verse from cue alone |

### Implementation

```python
def arrange_review_queue(due_cards):
    # Step 1: Group by passage to identify blocks
    blocks = group_by_passage(due_cards)
    
    # Step 2: Interleave within each block — at most 2 from same passage consecutively
    queue = []
    while any(blocks.values()):
        for passage in shuffled(blocks.keys()):
            if blocks[passage]:
                queue.append(blocks[passage].pop(0))
                if len(queue) >= 2 and same_passage(queue[-1], queue[-2]):
                    continue  # skip — already did 2 from this passage
    return queue
```

### Benefit

Research shows interleaving improves retention by **30-50%** compared to blocked practice, particularly for discrimination learning (distinguishing similar passages).

---

## Enhancement 5: Targeted Remediation on Verse Weak Points

### The Concept

When a user fails to recall a verse, don't just show it again. Identify the **specific weak point** in the recall chain and drill that specifically.

### Recall Chain for a Verse

```
Reference cue → First word → Second word → ... → Last word
    │              │             │                │
    └── Failure points:          │                │
        "I know it starts with   │                │
         'In the beginning...'   │                │
         but blank after that"   │                │
                                 └── "I always   │
                                     mix up the  │
                                     middle"     │
                                                 └── "I forget
                                                     the ending"
```

### Remediation by Failure Point

| Failure Pattern | Remediation | Question Type |
|----------------|-------------|---------------|
| Can't start | First-letter cue at increased intensity | "T w h I h i m h..." (first letters only) |
| Get lost mid-verse | Review the transition phrase | "What comes after 'Let there be'?" |
| Mix up similar verses | Contrastive drill | "Which verse says X and which says Y?" |
| Forget ending | End-focused recall | "You have the first half, what finishes it?" |
| Cross-verse interference | Discrimination drill | "Is 'light' from Gen 1:3 or John 1:4?" |

### Implementation

| Step | Description |
|------|-------------|
| **TR.1** | Track failure location in progressive hint system (which hint level were they on? which word did they miss?) |
| **TR.2** | Classify the failure pattern from hint history |
| **TR.3** | Generate a targeted remediation card specific to the failure point |
| **TR.4** | Insert the remediation card into the review queue with high priority |

### Benefit

Instead of re-memorizing the entire verse when only the ending is weak, the student drills only the ending. **Estimated 40% reduction in remediation time.**

---

## Enhancement 6: Gamification Overhaul

### Current Gamification

Our memorization module has no gamification — just raw FSRS intervals and a due count badge.

### Enhanced Gamification

| Element | Implementation |
|---------|---------------|
| **XP** | 1 XP per card reviewed, 3× bonus for perfect streak |
| **Verses Mastered** | Count of verses with stability > 30 days |
| **Streak** | Consecutive days with ≥1 review, resets on miss |
| **Streak Bonus** | XP multiplier: 7-day (1.5×), 30-day (2×), 365-day (3×) |
| **Badges** | Milestones: 10, 50, 100, 500, 1000 verses |
| **Leagues** | Weekly comparison with other users (if accounts exist) |
| **Heatmap** | GitHub-style contribution graph for daily reviews |
| **Mastery Map** | Visual knowledge graph showing how much of each book/passage is memorized |

### Implementation

| Step | Description |
|------|-------------|
| **G.1** | Add `xp`, `streak_count`, `last_review_date` to user state |
| **G.2** | Update XP on each review: award based on card type × performance |
| **G.3** | Calculate streak from consecutive daily reviews |
| **G.4** | Add badges table and check for new badges after each review |
| **G.5** | Build heatmap component for dashboard |

---

## Enhancement 7: Scripture Connection Graph as Memory Cues

### The Concept

Every verse in the Bible is connected to others via the connection graph. These connections serve as **natural mnemonic cues**. When stuck recalling a verse, the brain can "walk" along a connection to retrieve it.

### How It Works

```
User stuck on: "In the beginning was the Word..." (John 1:1)
    │
    ├── John 1:1 ──direct_quotation──→ Gen 1:1 ("In the beginning God created...")
    │   ↑ User knows Gen 1:1 — use it as retrieval cue
    │
    └── "Oh! 'In the beginning' in John is quoting Genesis!
         From there: 'was the Word, and the Word was with God...'"
```

### Implementation

During review, when the user requests a hint, the system can show:
1. **First-letter hint** (existing)
2. **Connection cue**: "This verse is connected to [known verse] via [connection type]"
3. If user still stuck, show the connected verse text as a prompt

### Connection Cue Priority

| Cue Type | Example | When to Use |
|----------|---------|-------------|
| Direct quotation | "This quotes Gen 1:1" | First connection cue |
| Same lemma | "This shares the word 'light' with Gen 1:3" | If direct quote not available |
| Allusion | "This echoes Isaiah's language" | Deeper cue |
| Type-antitype | "This is the fulfillment of the Passover type" | Thematic connection |

---

## Integration: Hebrew Scripture Memorization

Since the Hebrew teaching system teaches how to read Hebrew, and the memorization module memorizes verses, the two systems naturally integrate:

### Path from "Learning Hebrew" to "Memorizing Hebrew Scripture"

```
Learn aleph-bet ─→ Read words ─→ Understand grammar ─→ Read verse ─→ Memorize verse
      │                │                │                    │              │
      │                │                │                    │   ┌──┐    ┌──┘
      │                │                │                    └──►│H7│───►│M0│
      │                │                │                        │  │    │  │
      │                │                └───────────────────────►│H6│    │M1│
      │                └──────────────────────────────────────►│H5│    │M2│
      └──────────────────────────────────────────────────────►│H1│    │M3│
                                                                └──┘    └──┘
  Hebrew Teaching System (H1-H7)                  Memorization Module (M0-M3)
```

### Shared Data

| Data | Source | Used By |
|------|--------|---------|
| Hebrew word list | `gematria` table | Both |
| Connection graph | `connections` table | Memorization (FIRe credit, cues) |
| Morphology parsing | `lib/morphology.py` | Hebrew teaching (grammar practice) |
| Transliteration | `lib/hebrew_util.py` (via `biblical-transliteration`) | Hebrew teaching (reading practice) |
| FSRS parameters | Memorization module | Both (shared SRS engine) |

---

## Build Order

```
Week 1-2:  F1 (FIRe) + TR (Remediation)     ── Core engine enhancements
Week 2-3:  E3 (Learning Speeds) + E4 (Interleaving)  ── SRS calibration
Week 3-4:  G (Gamification) + E7 (Graph Cues) ── User-facing features
Week 4-5:  RC (Repetition Compression)        ── Optimization
```

All enhancements are independent and can be worked on in any order. Each has its own clear checkpoint.

---

## Summary: Before vs After

| Dimension | Before (Current) | After (Enhanced) |
|-----------|-----------------|------------------|
| Review triggering | FSRS on individual cards | FSRS + FIRe implicit credit from connected verses |
| Review ordering | Chronological (by due date) | Interleaved (mixed passages) |
| Difficulty calibration | None (all verses equal) | Per-student-per-verse learning speed ratios |
| Remediation | Show full verse again | Targeted to exact failure point (starting, middle, transition, ending) |
| Gamification | Due count badge only | XP, streaks, leagues, heatmap, badges |
| Mnemonic support | First-letter hints only | Connection graph as retrieval cues |
| Compression | None | Consecutive same-passage verses compressed into "recite passage" |
| Hebrew integration | None | Direct path from learning Hebrew to memorizing Hebrew verses |
