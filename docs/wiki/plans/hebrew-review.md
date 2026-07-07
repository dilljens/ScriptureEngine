# Hebrew Teaching System: Research Review

Review of the H2-H7 implementation against best language learning techniques,
The Math Academy Way cognitive science, and the FSRS spaced repetition research.

---

## 1. Curriculum Design vs Language Learning Research

### The Hierarchical Approach

Our 7-level Hebrew curriculum (Letters → Vowels → Syllables → Roots →
Words → Grammar → Reading) is aligned with research on **structured literacy**
and **systematic phonics instruction**.

| Principle | Research | Our Implementation | Status |
|-----------|----------|-------------------|--------|
| **Grapheme-phoneme correspondence** | Moats (2010), Ehri (2005) | Level 1: Each letter taught with sound + name | ✅ |
| **Systematic phonics** | National Reading Panel (2000) | Letters → syllables → words (sequential) | ✅ |
| **Morphological awareness** | Carlisle (2003), Goodwin & Ahn (2013) | Level 4: Root extraction, noun patterns | ✅ |
| **Decoding automaticity** | LaBerge & Samuels (1974) | Practice items target rapid recognition | ✅ |
| **Grammar in context** | Ellis (2006), Larsen-Freeman (2015) | Level 7: Reading Tanakh passages | ✅ |

### Gaps vs Language Learning Research

| Gap | Research | What's Missing |
|-----|----------|----------------|
| **Input flooding** | Krashen (1985), Ellis (2008) | No extensive exposure to comprehensible Hebrew input |
| **Spaced retrieval** | Cepeda et al. (2006) | H4 FIRe integration exists but no content-based retrieval schedule |
| **Elaborative rehearsal** | Craik & Tulving (1975) | Practice items are recognition-based, no deep processing prompts |
| **Contrastive analysis** | Lado (1957), Odlin (1989) | No English-Hebrew contrastive drills for grammar |
| **Cross-linguistic influence** | Jarvis & Pavlenko (2008) | No connection to learner's L1 (English) |
| **Communicative competence** | Canale & Swain (1980) | No free production tasks |

### Alignment with Math Academy Way

| Technique | Math Academy Way (Ch) | Hebrew Implementation | Status |
|-----------|----------------------|---------------------|--------|
| **Knowledge Graph** | Ch 4 | 102 nodes, 7 levels, 178 edges | ✅ |
| **Mastery Learning** | Ch 13 | Per-topic progress tracking | ✅ |
| **Minimizing Cognitive Load** | Ch 14 | Scaffolded lessons: exp → example → practice | ✅ |
| **Developing Automaticity** | Ch 15 | Letter recognition drills, speed targets planned | ⚠️ Not calibrated |
| **FIRe** | Ch 29 | Full credit + penalty + early discount | ✅ |
| **Interleaving** | Ch 19 | Reviews mix grammar topics | ⚠️ Review queue non-discriminating |
| **Testing Effect** | Ch 20 | All practice is retrieval-based | ✅ |
| **Targeted Remediation** | Ch 21 | H6 — linked key prerequisites | ✅ |
| **Non-Interference** | Ch 17 | Similar binyanim spaced | ⚠️ Not enforced in scheduling |

---

## 2. Lesson Content Quality

### Coverage by Topic Type

| Category | Nodes | Lessons | Practice Items | Avg Items |
|----------|-------|---------|---------------|-----------|
| **Consonants** | 28 | 28 | 84 | 3.0 |
| **Vowels** | 19 | 19 | 38 | 2.0 |
| **Syllables** | 5 | 5 | 10 | 2.0 |
| **Words & Roots** | 18 | 18 | 36 | 2.0 |
| **Verbs (Binyanim)** | 17 | 17 | 51 | 3.0 |
| **Nouns & Syntax** | 10 | 10 | 20 | 2.0 |
| **Reading** | 5 | 5 | 10 | 2.0 |

**Total: 102 lessons, 194 practice items**

### Lesson Structure Quality

Each lesson contains:
- **Explanation**: Direct instruction (2-5 min reading) — aligned with
  Math Academy Way's "direct instruction is needed" principle (Ch 8)
- **Worked examples**: Step-by-step practice — aligned with the
  **worked-example effect** (Sweller & Cooper, 1985)
- **Key points**: Summary for review — aligned with **advance organizers**
  (Ausubel, 1968)

### Practice Item Types

| Type | Count | Cognitive Level | Bloom's Taxonomy |
|------|-------|----------------|------------------|
| **True/False** | 102 | Recognition | Remember |
| **Multiple Choice** | 92 | Identification | Remember/Understand |

### Gap: No Production Items

The current practice items are all recognition-based (True/False, Multiple Choice).
Research shows **production effects** enhance memory (Eghbaria-Ghanamah et al. 2021).
We need:

- **Typing practice**: Type the letter from memory
- **Transliteration**: Write the Hebrew word from an English prompt
- **Conjugation tables**: Fill in verb conjugation charts
- **Translation**: Translate verses from Hebrew to English and vice versa
- **Reading aloud**: Audio recording of verse recitation

---

## 3. Spaced Repetition & FIRe Integration

### Current State

| Aspect | Status | Details |
|--------|--------|---------|
| **Knowledge Graph** | ✅ | 102 nodes, 178 edges, prerequisite types |
| **FIRe Credit** | ✅ | Mastery of advanced topics gives credit to prerequisites |
| **FIRe Penalty** | ✅ | Failing a prerequisite penalizes advanced topics |
| **FIRe Early Discount** | ✅ | Credit discounted when retrievability is high |
| **FSRS Algorithm** | ✅ | 21-parameter model verified against Rust reference |
| **Per-student progress** | ⚠️ | Tracked but not calibrated per student |

### Gap: Student-Topic Learning Speeds

Math Academy Way (Ch 29) calibrates each student on each topic:

```
learning_speed = student_ability / topic_difficulty
```

We don't compute this ratio. Currently all students have the same default parameters.

### Gap: No Content-Based Retrieval Schedule

The FSRS algorithm handles review timing, but the content itself doesn't
have a spaced retrieval curriculum. Language learning research recommends:

- **Gradual interval expansion**: 1 day → 3 days → 1 week → 1 month → 3 months
- **Massed practice for initial learning** → **spaced for retention**
- **Interleaved review** across grammar topics

Our system supports all of these via FSRS, but they aren't specifically
calibrated for language learning (different parameters may be optimal).

---

## 4. Gamification & Motivation

### Current State

| Element | Status | Notes |
|---------|--------|-------|
| **XP** | ✅ | Scales by hint level × rating |
| **Streak** | ✅ | Tracked, multiplier applied |
| **Progress by layer** | ✅ | Mastery by PaRDeS layer |
| **Leagues** | ❌ | Not implemented |
| **Badges** | ❌ | Not implemented |
| **Goals** | ❌ | No learning path goals |

### Language Learning Motivation Research

| Factor | Research | Recommendation |
|--------|----------|---------------|
| **Intrinsic motivation** | Deci & Ryan (2000) | Connect Hebrew to scripture study goals |
| **Self-efficacy** | Bandura (1997) | Show progress through levels |
| **Goal-setting** | Locke & Latham (2002) | Set daily/weekly XP goals |
| **Social learning** | Bandura (1977) | Community features |
| **Flow state** | Csikszentmihalyi (1990) | Balance challenge vs skill |

---

## 5. Comparison to Leading Language Platforms

| Feature | Duolingo | Rosetta Stone | Pimsleur | Our System |
|---------|----------|---------------|----------|------------|
| **Spaced repetition** | SM-2 | Proprietary | Interval-based | ✅ FSRS-5 |
| **FIRe (implicit credit)** | ❌ | ❌ | ❌ | ✅ |
| **Knowledge graph** | ❌ | ❌ | ❌ | ✅ 102 nodes |
| **Biblical Hebrew focus** | ❌ | ❌ | ❌ | ✅ |
| **Integrated scripture** | ❌ | ❌ | ❌ | ✅ 42K verse corpus |
| **Connection graph** | ❌ | ❌ | ❌ | ✅ 1M+ connections |
| **Memory palaces** | ❌ | ❌ | ❌ | ✅ |
| **Adaptive difficulty** | ✅ | ⚠️ | ❌ | ✅ BLIM engine |
| **Pronunciation** | ✅ | ✅ | ✅ TTS | ❌ Audio not built |
| **Writing practice** | ✅ | ⚠️ | ❌ | ❌ |
| **Community/social** | ✅ | ❌ | ❌ | ❌ |

---

## 6. Critical Gaps to Address

| # | Gap | Impact | Implements |
|---|-----|--------|------------|
| 1 | **Production practice items** (typing, transliteration, free recall) | High | Language learning best practice |
| 2 | **Student-topic learning speeds** (ability/difficulty ratio) | High | Math Academy Way Ch 29 |
| 3 | **Pronunciation/audio** — recording + playback of Hebrew recitation | High | Language learning best practice |
| 4 | **Comprehensible input** — graded Hebrew reading passages | High | Krashen's Input Hypothesis |
| 5 | **Contrastive analysis drills** — English vs Hebrew grammar comparison | Medium | Lado (1957) |
| 6 | **Review queue discrimination** — differentiate Hebrew from verse review | Medium | Currently both in same queue |
| 7 | **Non-Interference enforcement** — space similar letters/grammar | Medium | Math Academy Way Ch 17 |
| 8 | **Goal setting + progress dashboard** | Low | Motivation research |

---

## 7. Summary

### ✅ Strong Points

1. **Knowledge graph with FIRe** — no other language learning platform has this
2. **FSRS-5 verified algorithm** — state-of-the-art spaced repetition
3. **Integration with scripture corpus** — 42K verses of authentic reading material
4. **Scaffolded lesson structure** — explanation → worked example → practice
5. **102 topics across 7 levels** — comprehensive coverage

### ⚠️ Needs Work

1. **Production-focused practice** — current items are all recognition
2. **Student-topic calibration** — ability/difficulty ratio not computed
3. **Audio/pronunciation** — critical for language learning
4. **Comprehensible input** — graded reading passages from 42K verse corpus

### Next Steps for Hebrew Full v1.0

```
Priority 1: Production practice items (typing, transliteration, free recall)
Priority 2: Student-topic learning speeds (ability/difficulty ratio)
Priority 3: Audio recording + playback
Priority 4: Graded reading passages from Tanakh corpus
```
