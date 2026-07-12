# The Math Academy Way — Reference for Scripture Engine Implementation

> Based on *The Math Academy Way* (Skycak, 2026), 7,936 lines, ~30 chapters.
> Full text: `/home/dillon/Downloads/The Math Academy Way.md`
>
> This document maps Math Academy's evidence-based cognitive learning strategies
> to our scripture engine implementation. For each strategy, we note:
> - What Math Academy says
> - How we implement it
> - What's missing

---

## 1. Knowledge Graph (Ch 4)

### Math Academy
> *"Math Academy utilizes a knowledge graph, an interconnected structure of thousands of topics...to organize its curriculum and facilitate algorithmic decision-making."*

### Our Implementation
- ✅ 1.77M typed connections across 11 layers in a directed graph
- ✅ 8 works, 330 books, 70K+ verses as nodes
- ✅ Connection types: linguistic, intertextual, structural, numerical, sod, etc.
- ✅ Entity network (57K verse-entity links)
- ✅ `ENCOMPASSING` edges exist via prerequisite relationships (hebrew_edges table)

### Gaps
- ❌ No `encompassing_weights` on edges (partial encompassings are not numerically quantified)
- ❌ No cross-domain edges (Hebrew knowledge → Verse memorization is disconnected)

---

## 2. Spaced Repetition / FSRS-5 (Ch 18, 29)

### Math Academy
> *"The more reviews are completed with appropriate spacing, the longer the memory will be retained, and the longer one can wait until the next review is needed."*
> *"FIRe generalizes spaced repetition to hierarchical knowledge, allowing repetitions on advanced topics to implicitly trickle down to simpler topics."*

### Our Implementation
- ✅ FSRS-5 algorithm with 21 params (identical to fsrs-rs Rust crate)
- ✅ `stability`, `difficulty`, `retrievability` computed per card
- ✅ `mastery` tracking (0.0-1.0)
- ✅ `attempts`, `correct`, `last_review`, `next_review` stored per card

### Missing FIRe Components
- ❌ **Penalty flow upward** — failing a prerequisite/simpler verse should penalize advanced verses that depend on it
- ❌ **Summer slide / overdue acceleration** — `decay` should grow as card becomes more overdue
- ❌ **Student-topic learning speeds** — per-user, per-verse speed calibration
- ❌ **Partial encompassings** — fractional weights on edges

---

## 3. FIRe — Fractional Implicit Repetition (Ch 29)

### Math Academy Algorithm

```
repNum → max(0, repNum + speed · decay^failed · rawDelta)
memory → max(0, memory + rawDelta) · (0.5)^(days / interval)
```

Where:
- `repNum` = accumulated successful repetitions
- `speed` = student-topic learning speed (per-user, per-topic)
- `decay` = backwards speed when failing (grows with overdueness)
- `rawDelta` = credit earned, positive for pass, negative for fail
- `memory` = how well student remembers (decays over time)

### Our Implementation

```python
# Credit flow (rating >= 3):
for each connected verse:
    credit = conn_strength * rating_factor * 0.3
    new_credit = min(1.0, existing_credit + credit)
    if new_credit >= 1.0: skip due review (knock-out)
    decay: existing *= 0.9^days_since
```

### Gaps
- ❌ **No penalty flow**: `rating < 3` does nothing to connected verses
- ❌ **No `speed` factor**: global defaults, not per-user
- ❌ **No `decay` acceleration**: our 0.9^days is constant, should grow
- ❌ **No `rawDelta` magnitude**: our rating_factor is fixed, not quality-scaled

### Penalty Flow — What to Build

When a user fails a verse (rating 1 or 2):
```
for each connected ADVERSARIAL verse (connected via higher-stability verses):
    penalty = conn_strength * failure_penalty(1.0 for Again, 0.3 for Hard)
    stability = stability / (1 + penalty)  # Reduce stability
    fi_re_credit = max(0, fi_re_credit - penalty)  # Reduce credit
```

The direction is CRITICAL: failing Gen 1:1 should penalize John 1:1 (which quotes it),
NOT the other way around. Penalty flows from simpler → more complex.

---

## 4. Interleaving / Mixed Practice (Ch 19)

### Math Academy
> *"Interleaving involves spreading minimal effective doses of practice across various skills...doubled test scores and provided near immunity against forgetting."*
> *"Blocked practice allows students to settle into a robotic rhythm of mindlessly applying one type of solution."*
> *"No more than 2 consecutive problems of the same type."*

### Our Implementation
- ✅ Hebrew interleaving: `interleaveCards()` mixes `hebrew_letter` + `vocab` + `drill` with max 2 consecutive same-type
- ✅ CardQueue prevents blocking implicitly (ratings advance to next card)

### Gaps
- ❌ **No macro-interleaving**: Hebrew, Learn, and Memorize are completely separate queues. Math Academy interleaves across ALL topics.
- ❌ **No non-interference**: confusable pairs (similar verses, same lemma) can appear consecutively

### Macro-Interleaving — What to Build

A combined `/api/v1/review/interleaved` endpoint that:
1. Pulls due cards from ALL areas (Hebrew vocab, Learn questions, Memorize verses)
2. Interleaves them: no more than 2 consecutive from same area
3. Returns a mixed session

---

## 5. Non-Interference (Ch 17)

### Math Academy
> *"Non-interference ensures that similar topics are not scheduled too close to each other."*
> *"When confusable pairs are learned near each other, they interfere and reduce retention."*

### Our Implementation
- ❌ Nothing. No non-interference logic exists.

### What to Build
- Define confusable pairs: verses sharing rare words, similar themes, or known confusable lemma pairs
- When scheduling reviews, ensure confusable pairs are at least N cards apart (or in different sessions)
- Hebrew already has `hebrew_confusability` table — reuse this pattern

---

## 6. Mastery Learning (Ch 13)

### Math Academy
> *"Each individual student needs to demonstrate proficiency on prerequisite topics before moving on to more advanced topics."*

### Our Implementation
- ✅ Hebrew: prerequisite graph with `hebrew_edges`, unlocked/locked states
- ✅ LearnView: modules can be mastered (mastery >= 0.8)
- ✅ Memorize: `mastery` field, 0.8 = mastered

### Gaps
- ❌ No cross-area prerequisites (e.g., must complete Hebrew vowel lesson before memorizing verses containing those vowels)
- ❌ No enforced prerequisite chains in Memorize (you can memorize any verse regardless of understanding)

---

## 7. Targeted Remediation (Ch 21)

### Math Academy
> *"When a student struggles on a topic, the system identifies the specific weak area and targets review there."*

### Our Implementation
- ❌ Nothing systematic. The review queue orders by retrievability but doesn't target specific weak areas.

### What to Build
- Track per-verse accuracy rate
- For verses below 60% accuracy, increase their review frequency (reduce interval)
- Group weak verses into targeted mini-sessions

---

## 8. The Testing Effect / Retrieval Practice (Ch 20)

### Math Academy
> *"To maximize memory extension, avoid looking back at reference material unless totally stuck."*  
> *"Quiz questions are timed, no scaffolding, no reference to lessons."*

### Our Implementation
- ✅ CardQueue requires recall before showing answer (click to reveal, then rate)
- ✅ No option to "peek" at answer before rating
- ✅ Rating is based on retrieval difficulty (Again/Hard/Good/Easy)

### Gaps
- ❌ No timed quizzes (all reviews are self-paced)
- ❌ No "quiz mode" that hides references

---

## 9. Developing Automaticity (Ch 15)

### Math Academy
> *"Automaticity is critical — if a student cannot perform a skill automatically, the cognitive load of higher skills becomes overwhelming."*

### Our Implementation
- ✅ Hebrew letter recognition → vowel recognition → syllable → word → grammar (builds automaticity hierarchically)
- ✅ HebrewVerbDrill reinforces verb conjugation until automatic

### Gaps
- ❌ No speed/accuracy tracking per card (how fast did the user recall?)
- ❌ No automaticity threshold (recall within N seconds = mastered)

---

## 10. Gamification (Ch 22)

### Math Academy
> *"Gamification should be meaningful — XP, streaks, badges tied to learning milestones, not cosmetic rewards."*

### Our Implementation
- ✅ Hebrew: XP, streaks, badges, gamification table with `insight_xp`
- ✅ Memorize: not gamified beyond mastery tracking

### Gaps
- ❌ Memorize has no XP, streaks, or badges
- ❌ No cross-area gamification (total XP across all areas)

---

## 11. Layering (Ch 16)

### Math Academy
> *"Layering involves teaching a concept at surface level, then revisiting it more deeply later."*

### Our Implementation
- ✅ PaRDeS levels (P'shat → Remez → Drash → Sod) naturally layer understanding
- ✅ Connection layers (linguistic → structural → interpretive → sod) progress from factual to hidden

### Gaps
- ❌ No explicit "layering" in the card review schedule (cards don't progress from easy → hard connections)

---

## 12. Desirable Difficulty (Ch 8, 19)

### Math Academy
> *"A practice condition that makes the task harder yet improves recall is a desirable difficulty."*

### Our Implementation
- ✅ Click-to-reveal before rating (creates retrieval effort)
- ✅ Interleaving (mixing types increases cognitive load)
- ✅ FSRS intervals (spacing creates desirable difficulty)

### Gaps
- ❌ No adaptive difficulty: we don't increase card difficulty when user performs well (should add "progressive hint levels" for verse recall)

---

## Implementation Priority

| # | Strategy | Current Status | Effort | Impact |
|---|----------|---------------|--------|--------|
| 1 | **Penalty flow upward** | ❌ Missing | 2h | **High** |
| 2 | **Macro-interleaving** | ⚠️ Hebrew only | 4h | **High** |
| 3 | **Non-interference** | ❌ Missing | 3h | Medium |
| 4 | **Targeted remediation** | ❌ Missing | 4h | Medium |
| 5 | **Summer slide decay** | ❌ Missing | 2h | Medium |
| 6 | **Student-topic speeds** | ⚠️ Columns exist | 4h | Low |
| 7 | **Partial encompassings** | ❌ Missing | 3h | Low |
| 8 | **Timed quizzes** | ❌ Missing | 2h | Medium |
| 9 | **Cross-area prerequisites** | ❌ Missing | 3h | Low |
| 10 | **Memorize gamification** | ❌ Missing | 2h | Low |

---

## Key Reference URLs

| Resource | URL |
|----------|-----|
| Full TMAW document | `/home/dillon/Downloads/The Math Academy Way.md` |
| Spaced repetition (Ch 18) | Lines 4060-4312 |
| Interleaving (Ch 19) | Lines 4313-4534 |
| Testing effect (Ch 20) | Lines 4535-4728 |
| FIRe deep dive (Ch 29) | Lines 5522-5702 |
| Diagnostic deep dive (Ch 30) | Lines 5703-5810 |
| Learning efficiency (Ch 31) | Lines 5811-5921 |
| Prioritizing core topics (Ch 32) | Lines 5922- |
