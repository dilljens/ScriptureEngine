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
We should add per-student-per-verse ability tracking:
- Track accuracy per student per verse
- Compute `ability` as weighted moving average of recent ratings
- Compute `difficulty` from aggregate performance across all students
- `learning_speed = ability / difficulty`
- Scale FSRS interval by learning speed

**Fix needed**: Add student ability tracking and topic difficulty calibration.

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
| **Penalty direction** | Upward (fail simple → penalize advanced) | ❌ **Missing** | ❌ **Fix** |
| **Chain weight** | Product of edge weights along path | `chainWeight *= ConnectionWeight(type)` | ✅ Correct |
| **Best path** | MAX credit when multiple paths reach same node | `bestBoost[verseID]` tracks max | ✅ Correct |
| **Rating multiplier** | Good=0.5, Easy=1.0 | Cloned from plcourse (MIT) | ✅ Correct |
| **Minimum threshold** | chainWeight < 0.001 ignored | `if chainWeight < 0.001 { continue }` | ✅ Correct |
| **Credit application** | `stability *= (1 + boost)` | `newStability = stability * (1.0 + b.Boost)` | ✅ Correct |
| **Failures** | "Failed repetition flows forward to penalize" | ❌ **Not implemented** | ❌ **Fix** |
| **Early discount** | "rawDelta discounted if repetition was early" | ❌ **Not implemented** | ❌ **Fix** |
| **Decay model** | `decay` grows when overdue (summer slide) | ❌ **Not implemented** | ❌ **Fix** |

### Critical Gaps

#### Gap 2a: Penalty Flow (Upward)
When a user fails a review on verse A, connected verses that depend on A
should be penalized. For example, failing Gen 1:1 should penalize connected
verses like John 1:1 (which quotes it).

**Fix**: In the FIRe engine, when rating=Again:
1. Find all verses that point TO the failed verse (reverse connections)
2. Reduce their stability by `chain * penaltyMultiplier`
3. Mark them for earlier review (shorten interval)

#### Gap 2b: Early Repetition Discount
When a review happens significantly before the due date (good retention
still high), the FIRe credit should be discounted because the repetition
was "too early." This is described in Ch 29:

> *"The magnitude of rawDelta is also discounted if the repetition was
>   completed early relative to the desired interval, i.e., if memory is
>   sufficiently high."*

**Fix**: In `ApplyFIREBoosts`, discount boost by `(1 - retrievability)`:
```go
retrievability := card.Retrievability(elapsedDays)
discount := 1.0 - retrievability  // 0 when memory fresh, 1 when fully decayed
effectiveBoost := boost * discount
```

#### Gap 2c: Decay Model for Overdue Reviews
The Math Academy Way models "summer slide" where overdue reviews cause
faster forgetting. Not implemented.

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
| **XP** | 1 XP ≈ 1 minute | 10 XP per review (fixed) | ⚠️ Simplistic |
| **Streak** | Consecutive days | ✅ Tracked in user_xp | ✅ |
| **Leagues** | Competitive weekly groups | ❌ Not implemented | ❌ |
| **Badges** | Milestone achievements | ❌ Not implemented | ❌ |
| **Quality bonus** | Bonus for perfect pass | ❌ Not implemented | ❌ |
| **Penalty** | Reduced XP for poor performance | ❌ Not implemented | ❌ |

### Gap: XP Should Reflect Effort

Our system gives a flat 10 XP per review regardless of:
- Hint level (level 5 blank recall is harder than level 0 full text)
- Whether the rating was Easy vs Hard
- Streak multiplier

**Fix**: Scale XP by hint level and rating:
```go
baseXP := 10
hintBonus := hintLevel * 2  // harder hint = more XP
ratingMultiplier := map[int]float64{1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25}
streakMultiplier := 1.0 + float64(streak) * 0.02  // up to 2× at 50 days
xp := int(float64(baseXP+hintBonus) * ratingMultiplier[r] * streakMultiplier)
```

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

| # | Gap | Impact | Effort |
|---|-----|--------|--------|
| 1 | **Student-topic learning speeds** (per-student-per-verse ability) | Medium — better calibration | Medium |
| 2a | **FIRe penalty flow** — failing a verse should penalize connected verses | High — missing half the FIRe model | Medium |
| 2b | **FIRe early discount** — discount credit when review is too early | Medium — prevents over-credit | Small |
| 2c | **FIRe decay model** — overdue review penalty | Low — edge case | Small |
| 3 | **Connection hint quality** — use connection graph instead of search | Low — cosmetic | Small |
| 4 | **Diagnostic mode** — initial assessment + conditional completion | Medium — useful feature | Medium |
| 5 | **XP scaling** — XP should reflect effort (hint level, rating, streak) | Low — nice to have | Small |
| 6 | **Targeted remediation** — detect failure point, suggest connected verses | High — major learning improvement | Large |
| 7 | **Push scheduler** — periodic check for due cards | Low — nice to have | Medium |
| 8 | **Gamification** — leagues, badges, quality bonus | Low — motivational | Medium |
