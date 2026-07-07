# Implementation Review: Features vs. The Math Academy Way

Audit of our memorization module and assessment engine against the research
and techniques described in *The Math Academy Way* (Skycak, 2026).

---

## 1. FSRS-5 Spaced Repetition

### Math Academy Way Says (Ch 18, Ch 29)

> *"Spaced repetition is like weightlifting where the wait is the weight."*
> *"The spacing effect: reviews should be spaced out over multiple sessions so
>   that memory is not only restored, but also further consolidated into
>   long-term storage."*

### Our Implementation

| Aspect | Research | Our Implementation | Status |
|--------|----------|-------------------|--------|
| **Algorithm** | FSRS-5 (21 params, Anki-compatible) | Ported from `fsrs-rs` Rust crate | ✅ Verified |
| **Forgetting curve** | `R(t) = (t/s * factor + 1)^decay` | `powerForgettingCurve()` matches Rust | ✅ Exact |
| **Stability growth** | After success: `S' = S * f(D, R, I)` | `stabilityAfterSuccess()` matches test vectors | ✅ Exact |
| **Difficulty** | `D' = D + linear_damping + mean_reversion` | `nextDifficulty()` + `meanRevision()` match | ✅ Exact |
| **Initial params** | w[0..3] for ratings 1-4 | Trained from 30M+ reviews | ✅ |
| **Decay** | w[20] = 0.1542 (FSRS6_DEFAULT_DECAY) | Matches fsrs-rs `DEFAULT_PARAMETERS` | ✅ |
| **Short-term stability** | Enabled/disabled via w[17..19] | Disabled (w[17..19]=0 in default) | ✅ Correct |

### Gap: No Student-Topic Learning Speeds

The Math Academy Way calibrates each student on each topic using a
**student ability / topic difficulty ratio** (Ch 29):

> *"Student ability and topic difficulty are competing factors — high student
>   ability speeds up the overall student-topic learning speed, while high
>   topic difficulty slows it down."*

Our FSRS uses global default parameters for all users on all verses.
We should add per-student-per-verse ability tracking.

**✅ Fixed**: XP now scales by hint level and rating, which is a prerequisite
for student-topic speed calibration. Full per-student-per-verse ability
tracking is still pending.

---

## 2. FIRe — Fractional Implicit Repetition

### Math Academy Way Says (Ch 29)

> *"FIRe generalizes spaced repetition to hierarchical knowledge, allowing
>   repetitions on advanced topics to implicitly trickle down to simpler
>   topics through encompassing relationships."*

Three key properties:
1. **Credit flows downward** through encompassing relationships
2. **Penalties flow upward** — failing a simpler topic penalizes advanced ones
3. **Best path wins** — when multiple paths reach the same topic, the strongest chain weight is used

> *"When you pass a review on an advanced topic, the repetition flows backward
>   to simpler topics because you've just shown evidence that you still know
>   how to perform those component skills."*

### Our Implementation

| Aspect | Research | Our Implementation | Status |
|--------|----------|-------------------|--------|
| **Credit direction** | Downward through encompassing graph | DFS ancestor traversal | ✅ Correct |
| **Penalty direction** | Upward (fail simple → penalize advanced) | `ComputePenalties()` + `ApplyFIREPenalties()` | ✅ **Fixed** |
| **Chain weight** | Product of edge weights along path | `chainWeight *= ConnectionWeight(type)` | ✅ Correct |
| **Best path** | MAX credit when multiple paths reach same node | `bestBoost[verseID]` tracks max | ✅ Correct |
| **Rating multiplier** | Good=0.5, Easy=1.0 | Cloned from plcourse (MIT) | ✅ Correct |
| **Minimum threshold** | chainWeight < 0.001 ignored | `if chainWeight < 0.001 { continue }` | ✅ Correct |
| **Credit application** | `stability *= (1 + boost)` | `newStability = stability * (1.0 + b.Boost)` | ✅ Correct |
| **Penalty application** | "Failed repetition flows forward" | `newStability = stability / (1.0 + penalty)` | ✅ **Fixed** |
| **Early discount** | "Discounted if repetition was early" | `EarlyDiscount(boost, retrievability)` = `boost * (1 - R²)` | ✅ **Fixed** |
| **Decay model** | `decay` grows when overdue (summer slide) | ❌ Not implemented | ❌ Pending |

### Fixed Gaps

- **Gap 2a (Penalty Flow)**: ✅ `ComputePenalties()` does DFS through connection graph
  when a verse is failed. Penalty multiplier: Again=1.0, Hard=0.3. Stability reduced by
  dividing by `(1 + penalty)`. Verified: failing Gen 1:1 reduced John 1:1 stability from
  6.02 to 3.34 (factor of 1.8).

- **Gap 2b (Early Discount)**: ✅ `EarlyDiscount(boost, retrievability)` = `boost * (1 - R²)`.
  R=0.0 (forgotten) → full credit. R=0.95 (fresh) → 10% credit. Applied in DB layer.

### Pending Gaps

#### Gap 2c: Decay Model for Overdue Reviews
The Math Academy Way models "summer slide" where overdue reviews cause
faster forgetting. Not implemented.

---

## FIRe Architecture: Knowledge vs Memorization

### The Distinction

The Math Academy Way's FIRe operates on a **knowledge graph** of concepts
(prerequisites, encompassings). Our FIRe implementation operates on a
**connection graph** of scripture verses. These are fundamentally different.

For our system, FIRe needs to support **three distinct modes**:

| Mode | Graph | Edges | What FIRe Tracks |
|------|-------|-------|------------------|
| **Language Learning** | Hebrew concepts (letters → vowels → roots → grammar) | Prerequisite relationships | Understanding of language concepts |
| **Scripture Knowledge** | Story info, themes, theological concepts | Connection layers (linguistic, symbolic, sod) | Understanding of how scriptures connect |
| **Verse Memorization** | Verse-to-verse connections | Same as above, but for recall | Ability to recite verses verbatim |

### Separation of Concerns

Memorization and understanding should be **independent but factorizable**:

```
Student who understands Hebrew can learn faster
         │
         ▼
Hebrew Knowledge ──FIRe──→ Hebrew Concept Mastery
(letters, vowels,         (P knows what ב means)
 grammar rules)           
         │
         │ (when student also memorizes verses in Hebrew)
         ▼
Verse Memorization ──FIRe──→ Verbatim Recall
(Gen 1:1 in Hebrew)         (P can recite from memory)
```

- **Without memorization**: FIRe tracks understanding of connections. P knows
  that Gen 1:1 connects to John 1:1 via direct quotation. This knowledge
  gets FIRe credit when reviewing connected concepts.
- **With memorization**: FIRe additionally tracks verbatim recall of verses.
  Memorizing John 1:1 gives FIRe credit to Gen 1:1 (and vice versa).
- **Factorized**: A user can understand a connection without memorizing the
  verse, and FIRe tracks both independently.

### Current Implementation

Our FIRe engine currently operates on **verse-to-verse connections** only
(memorization mode). To support full knowledge tracking we need:

1. **Abstract the graph**: Make FIRe graph-agnostic — it should work on any
   directed graph with weighted edges, not just verse connections.
2. **Add knowledge tracks**: Language concepts, scripture stories/themes.
3. **Separate state**: Knowledge mastery state is different from memorization
   state, though they can influence each other.

### Plan for Multi-Mode FIRe

```go
type KnowledgeGraph struct {
    Nodes []KnowledgeNode    // could be verses, concepts, grammar rules
    Edges []KnowledgeEdge     // weighted directed edges
}

type KnowledgeNode struct {
    ID        string   // "letter.bet", "gen.1.1", "binyan.qal"
    Type      string   // "hebrew_letter", "verse", "grammar_rule"
    Metadata  map[string]interface{}
}

type KnowledgeEdge struct {
    SourceID string  // advanced concept
    TargetID string  // simpler concept it encompasses
    Weight   float64 // encompassing weight (0.0-1.0)
    Type     string  // "prerequisite", "encompassing", "connection"
}
```

This would allow the same FIRe engine to operate on:
- Hebrew letter → Hebrew vowel (language learning)
- Story → connected story (scripture knowledge)
- Verse → connected verse (memorization)

All three tracks share the same algorithm but maintain separate mastery states.

---

## 3. Interleaving (Mixed Practice)

### Math Academy Way Says (Ch 19)

> *"Interleaving involves spreading minimal effective doses of practice across
>   various skills, in contrast to blocked practice, which involves extensive
>   consecutive repetition of a single skill."*

Key findings:
- Interleaving **doubled test scores** (Taylor & Rohrer, 2010)
- Interleaved practice provided **near immunity against forgetting** (74% vs 80% after delay)
- Blocking creates **illusory fluency** — students feel they know it but don't

### Our Implementation

| Aspect | Research | Our Implementation | Status |
|--------|----------|-------------------|--------|
| **Max per passage** | Switch before mastery complete | Max 2 consecutive from same passage | ✅ Correct |
| **Review only** | Blocking for new, interleaving for review | Only affects review queue, not new cards | ✅ Correct |
| **Due-date ordering** | Choose topics whose spaced reps are due | Interleaved on top of FSRS scheduling | ✅ Correct |

### Gap: No Macro-Interleaving

The Math Academy Way describes macro-interleaving as breadth-first
learning across different units, not depth-first (master one unit
completely before moving on). For scripture memorization, this means
not memorizing all of Psalm 23 before starting Romans 8, but mixing them.

Our current system creates cards independently per verse and interleaves
reviews. This is essentially macro-interleaved by design since verses are
added from different passages organically. **No fix needed.**

### Gap: No Repetition Compression

> *"Reviews are specifically chosen to cover as many component skills as
>   possible that you need practice on, so you'll actually get an outsized
>   dose of micro-interleaving compressed into each review."*

When multiple connected verses are due simultaneously, they should be
compressed into a single combined review. Not implemented.

---

## 4. Progressive Hint Levels

### Math Academy Way Says (Ch 20 — Testing Effect)

> *"The testing effect: retrieval is the most effective method of review."*
> *"The benefits of practice testing come from effortful retrieval of
>   information."*

Our progressive hint levels implement the **testing effect** by forcing
retrieval at increasing difficulty levels. This is aligned with:

> *"Desirable difficulties: practice conditions that make the task harder,
>   slowing down the learning process yet improving recall and transfer."*

| Aspect | Research | Our Implementation | Status |
|--------|----------|-------------------|--------|
| **Level 0** | Full text | ✅ | ✅ |
| **Level 1** | First-letter cues | ✅ | ✅ |
| **Level 2** | Image cue | ✅ | ✅ |
| **Level 3** | Reference only | ✅ | ✅ |
| **Level 4** | Connection hint | Basic (search API) | ⚠️ Basic |
| **Level 5** | Blank | ✅ | ✅ |
| **Progression** | Good/Easy → level up, Again → level down | ✅ | ✅ |

### Gap: Connection Hint Quality

Level 4 uses a simple search API query that's unreliable. The Math Academy
Way would use the **prerequisite/encompassing graph** to find the most
informative connected verse. We should use the FIRe connection graph
directly rather than a text search.

---

## 5. Mastery Learning + Assessment Engine

### Math Academy Way Says (Ch 13, Ch 30)

> *"Each individual student needs to demonstrate proficiency on prerequisite
>   topics before moving on to more advanced topics."*

> *"Diagnostic exams select questions that maximize information gain, using
>   Bayesian knowledge tracing to update mastery probabilities."*

### Our Implementation

| Aspect | Research | Our Implementation | Status |
|--------|----------|-------------------|--------|
| **Knowledge items** | All high-quality connections | 713,350 items across 11 layers | ✅ |
| **Prerequisite graph** | DAG of item dependencies | 18,717 cross-layer edges | ✅ DAG-validated |
| **Item selection** | Max information gain + outer fringe | BLIM model with max-info selection | ✅ |
| **Bayesian update** | `P(mastery | response)` | Bayesian BLIM update | ✅ |
| **Termination** | Entropy < threshold or max items | Entropy < 0.1 or max_items reached | ✅ |
| **Outer fringe** | Items at 0.3-0.7 mastery | Fringe boost (1.5× info weight) | ✅ |

### Gap: No Diagnostic Mode

The Math Academy Way describes a diagnostic phase where a new student's
knowledge is assessed before starting. Our assessment engine assumes
the user starts from zero. We should add:

1. **Initial diagnostic**: Present items from broad range of types/layers
2. **Conditional completion**: When confidence in a topic crosses threshold,
   stop asking about it
3. **Supplemental diagnostics**: Periodically probe for newly-mastered items

---

## 6. Gamification

### Math Academy Way Says (Ch 22)

> *"XP-time equivalence: 1 XP ≈ 1 minute of effort."*
> *"Incentivizing quality: bonus XP for perfect performance."*
> *"Closing loopholes: penalties for poor performance prevent gaming."*

### Our Implementation

| Aspect | Research | Our Implementation | Status |
|--------|----------|-------------------|--------|
| **XP** | 1 XP ≈ 1 minute | 10 XP per review (fixed) | ⚠️ **Fixed** |
| **XP scaling** | By effort and quality | `baseXP=10+ hintLevel×2`, `× ratingMult(0.5-1.25)` | ✅ **Fixed** |
| **Streak** | Consecutive days | ✅ Tracked in user_xp | ✅ |
| **Leagues** | Competitive weekly groups | ❌ Not implemented | ❌ |
| **Badges** | Milestone achievements | ❌ Not implemented | ❌ |
| **Quality bonus** | Bonus for perfect pass | ❌ Not implemented | ❌ |
| **Penalty** | Reduced XP for poor performance | ✅ Lower rating = less XP (0.5× for Again) | ✅ |

### XP Scaling (Fixed)

XP now scales with effort:
- Base: `10 + hintLevel × 2` (harder hints = more XP, range 10-20)
- Rating multiplier: Again=0.5, Hard=0.75, Good=1.0, Easy=1.25
- Streak multiplier: `1.0 + streakDays × 0.02` (cap at 2.0)
- Formula: `XP = base × ratingMult × streakMult`

---

## 7. Targeted Remediation

### Math Academy Way Says (Ch 21)

> *"When a student struggles, we don't lower the bar. Instead, we provide
>   automated, precise support targeted to individual students on individual
>   topics — and often even more precisely to the individual component skills."*

Four types:
1. **Corrective**: More chances to practice the specific point of failure
2. **Preventative**: Slow down spacing on prerequisites predicted to cause trouble
3. **Foundational**: Fill missing prerequisites below course level
4. **Content**: Improve the lesson itself when >5% fail

### Our Implementation

None of these are implemented. The closest we have is:

| Type | Status | Notes |
|------|--------|-------|
| **Corrective** | ⚠️ Partial | ReviewSession just shows the card again |
| **Preventative** | ❌ Missing | No prediction of which verses will be hard |
| **Foundational** | ❌ Missing | No concept of prerequisite verses |
| **Content** | ❌ Missing | No analytics on which verses users fail most |

### Fix Needed
When a user fails (Again) a verse review:
1. Look up the connection graph for related verses the user has memorized
2. If the failure is on Level 4-5 (blank/connection hint), drop to a lower level
3. If the failure is on Level 0-1 (full text/first letters), suggest reviewing
   connected verses first

---

## 8. PWA + Push Notifications

### Math Academy Way Says

The Math Academy Way doesn't specifically discuss PWA/push, but the
principles of **habit formation** (Ch 26) apply:

> *"Habit is the strongest predictor of future behavior."*
> *"Habit overcomes limited self-control, just as automaticity overcomes
>   limited working memory."*

### Our Implementation

| Feature | Status |
|---------|--------|
| manifest.json | ✅ |
| Service worker (cache-first) | ✅ |
| Push notification handler | ✅ |
| Push subscribe endpoint | ✅ |
| Push unsubscribe endpoint | ✅ |
| VAPID key generator | ✅ |
| Push scheduler (check due cards every N min) | ❌ Missing |
| Settings toggle for notifications | ❌ Missing |

Push is wired but the scheduler that fires notifications when cards are
due hasn't been built yet.

---

## Summary: Gaps Needing Fixes

| # | Gap | Impact | Effort | Status |
|---|-----|--------|--------|--------|
| 1 | **Student-topic learning speeds** | Medium | Medium | ⏳ Pending |
| 2a | **FIRe penalty flow** | High | Medium | ✅ Fixed |
| 2b | **FIRe early discount** | Medium | Small | ✅ Fixed |
| 2c | **FIRe decay model** | Low | Small | ⏳ Pending |
| 3 | **Connection hint quality** | Low | Small | ⏳ Pending |
| 4 | **Diagnostic mode** | Medium | Medium | ⏳ Pending |
| 5 | **XP scaling** | Low | Small | ✅ Fixed |
| 6 | **Targeted remediation** | High | Large | ⏳ Pending |
| 7 | **Push scheduler** | Low | Medium | ⏳ Pending |
| 8 | **Gamification** (leagues, badges) | Low | Medium | ⏳ Pending |
| 9 | **FIRe multi-mode** (knowledge + language) | High | Large | 🔍 Planned |

### Legend
- ✅ Fixed — implemented and verified
- ⏳ Pending — not yet implemented
- 🔍 Planned — design complete, not started
