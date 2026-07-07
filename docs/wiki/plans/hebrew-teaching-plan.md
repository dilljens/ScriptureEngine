# Hebrew Teaching System

**Inspired by The Math Academy Way** — Using the power of cognitive science to teach Biblical Hebrew.

## Core Philosophy

Hebrew is an ideal domain for Math Academy-style talent development because:

1. **High hierarchical structure**: letters → vowels → syllables → roots → words → grammar → phrases → reading — each level builds directly on the previous
2. **Automaticity is critical**: you cannot read a verse if you must sound out every letter. Recognition must become instantaneous
3. **Massive deliberate practice required**: Hebrew grammar (binyanim, noun patterns, construct chains) requires hundreds of focused repetitions
4. **Prerequisite graph is clear**: the dependency structure is well-understood and unambiguous
5. **Integration with existing scripture engine**: every reading passage comes from Tanakh, and the connection graph enriches each passage

The system builds a **knowledge graph** of ~200 Hebrew topics across 7 levels, implements **mastery learning** (must pass each topic before advancing), **spaced repetition with FIRe** (learning new material implicitly reviews old), and **targeted remediation** (when you stumble, the system pinpoints the exact letter/rule/root causing the issue).

---

## Hebrew Knowledge Graph

### Level 1: Aleph-Bet (22 consonants + 5 final forms)

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Letter recognition (22 letters) | None | Identify each letter by name and sound |
| Final forms (5) | Letter recognition | ך, ם, ן, ף, ץ |
| Letter writing | Letter recognition | Write each letter in block script |
| Letter classification | Letter recognition | Gutturals, begadkefat, vowels letters, etc. |

### Level 2: Vowels (Nikkud)

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Basic vowels (5) | Letter recognition | patah, qamats, segol, tsere, hiriq |
| Full vowel set (13+) | Basic vowels | Holam, shuruq, qubuts, sheva, hatafim |
| Sheva rules | Full vowel set | Vocal vs silent sheva, sheva na vs nah |
| Dagesh | Full vowel set | Dagesh lene vs forte, begadkefat spirantization |
| Qamats qatan/gadol | Full vowel set | Distinguishing the two qamats sounds |
| Meteg and cantillation | Full vowel set | Accent marks and their effect on pronunciation |

### Level 3: Syllables

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Syllable structure (CV, CVC) | Full vowel set | Recognize syllable boundaries |
| Syllable types | Syllable structure | Open, closed, stressed, unstressed |
| Syllabification rules | Syllable types | Divide words into syllables correctly |
| Stress patterns | Syllable types | Ultimate vs penultimate stress |

### Level 4: Words & Roots

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Triconsonantal roots | Letter recognition | Identify the 3-letter core of a word |
| Root families | Triconsonantal roots | Group words sharing the same root |
| Word patterns (mishkalim) | Triconsonantal roots | Noun patterns (qatl, qitl, qutl, etc.) |
| Prefixes | Syllable structure | The 7 inseparable prepositions (ב, כ, ל, מ, ש, ו, ה) |
| Suffixes | Syllable structure | Pronominal suffixes (my, your, his, etc.) |
| Maqqef and word linking | Word patterns | Hyphenated word combinations |

### Level 5: Grammar — Verbs (Binyanim)

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Qal perfect | Roots + syllables | 3ms Qal perfect conjugation |
| Qal imperfect | Qal perfect | 3ms Qal imperfect conjugation |
| Qal imperative | Qal imperfect | Commands |
| Qal infinitive | Qal imperfect | Infinitive construct and absolute |
| Qal participle | Qal imperfect | Active and passive participles |
| Niphal | Qal | Passive/reflexive of Qal |
| Piel | Qal | Intensive active |
| Pual | Qal | Intensive passive |
| Hiphil | Qal | Causative active |
| Hophal | Qal | Causative passive |
| Hithpael | Qal | Reflexive/intensive |
| Weak verbs (I-guttural) | All binyanim | Guttural assimilation rules |
| Weak verbs (I-nun) | All binyanim | Nun dropping |
| Weak verbs (I-yod) | All binyanim | Yod dropping |
| Weak verbs (III-he) | All binyanim | He dropping and vowel changes |
| Weak verbs (II-vav/yod) | All binyanim | "Hollow" verb patterns |
| Weak verbs (double ayin) | All binyanim | Geminate verbs |

### Level 6: Grammar — Nouns, Particles, Syntax

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Noun gender | Word patterns | Masculine vs feminine markers |
| Noun number | Noun gender | Singular, plural, dual |
| Noun state | Noun number | Absolute vs construct |
| Construct chain | Noun state | Multiple nouns in sequence |
| Definite article | Noun state | Ha- prefix, vowel changes |
| Prepositions | Definite article | Independent and inseparable |
| Vav-consecutive | All binyanim | Conversive vav in narrative |
| Word order | Vav-consecutive | VSO vs SVO, fronting for emphasis |
| Direct object marker | Word order | את and its uses |
| Relative clause | Word order | אשר and its forms |
| Conditional sentences | Relative clause | If-then constructions |

### Level 7: Reading Tanakh

| Topic | Prerequisites | Key Skills |
|-------|--------------|------------|
| Prose reading (Genesis) | All grammar | Read and parse narrative passages |
| Poetic reading (Psalms) | All grammar | Parallelism, terseness |
| Prophetic reading (Isaiah) | All grammar | Prophetic perfect, shifts in tense |
| Law reading (Torah) | All grammar | Legal formulas, casuistic form |
| Textual connections | Reading | Cross-reference detection using scripture engine graph |

---

## Instructional Design

### Lesson Format (per topic)

Each of the ~200 topics follows the **Math Academy lesson template**:

```
┌─────────────────────────────────────────────┐
│  LESSON: [Topic Name]                       │
│                                             │
│  ┌── EXPLANATION ──────────────────────────┐│
│  │  Brief, direct instruction (2-5 min)     ││
│  │  With example table/reference            ││
│  └──────────────────────────────────────────┘│
│                                             │
│  ┌── WORKED EXAMPLE ───────────────────────┐│
│  │  Step-by-step solved problem            ││
│  │  Each step annotated                    ││
│  └──────────────────────────────────────────┘│
│                                             │
│  ┌── PRACTICE ────────────────────────────┐│
│  │  5-10 scaffolded problems              ││
│  │  Levels: recall → apply → transfer     ││
│  │  Immediate feedback on each            ││
│  │  Must pass to advance                  ││
│  └──────────────────────────────────────────┘│
│                                             │
│  (If fail → remedial review on key          │
│   prerequisite topic, retry later)          │
└─────────────────────────────────────────────┘
```

### Practice Question Types

| Type | Description | Example |
|------|-------------|---------|
| **Recognition** | Identify the correct form | "Which letter is bet?" |
| **Production** | Write/speak from memory | "Write the letter lamed" |
| **Transliteration** | Convert script ↔ sound | "Read this word aloud" |
| **Parsing** | Analyze a given form | "What binyan and tense is this verb?" |
| **Translation** | Produce or identify meaning | "Translate this phrase" |
| **Connection** | Find related words/verses | "What root does this word share with Psalm 23?" |

---

## FIRe (Fractional Implicit Repetition) for Hebrew

The most powerful concept from Math Academy Way applied to Hebrew teaching.

### How FIRe Works

When a student reads a Tanakh verse (Level 7), they implicitly practice every lower-level topic that appears in that verse:

```
Verse:  בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים
         │         │       │
         │         │       └── L1: alef, lamed, he, yod, mem
         │         │           L2: qamats, hiriq, holam
         │         │           L4: root אלוהים (divine)
         │         │
         │         └────── L1: bet, resh, alef
         │                  L2: qamats
         │                  L4: root ברא (create)
         │                  L5: Qal perfect 3ms
         │
         └────────── L1: bet, resh, alef, shin, yod, tav
                      L2: sheva, tsere, hiriq
                      L3: 3 syllables
                      L4: root ראשׁ (head/beginning)
```

Each lower-level topic gets **fractional repetition credit** equal to:

```
credit = encompassing_weight × (1.0 / depth_factor)
```

Where:
- `encompassing_weight` = how strongly this advanced topic exercises the prerequisite (0.0-1.0)
- `depth_factor` = how many hops deep the prerequisite is (1.0 for direct, 0.5 for 2 hops, 0.25 for 3)

### FIRe Benefits for Hebrew

| Scenario | Without FIRe | With FIRe |
|----------|-------------|-----------|
| 50 verses memorized, each uses the letter ב | 50 separate reviews for the letter ב | Each verse gives partial credit; letter ב rarely needs explicit review |
| Student masters Qal, now learning Hiphil | Must separately maintain Qal reviews | Every Hiphil exercise implicitly reinforces Qal stem changes |
| Reading Psalm 119 (22 stanzas, all letters) | Would need separate review of each letter | Each stanza reviews a different letter via FIRe |

### Repetition Compression

When multiple topics are simultaneously due for review, they can be **compressed** into a single combined task if they share enough structural relationship:

**Example**: Due reviews on *Qal perfect 3ms*, *Qal perfect 1cs*, and *Qal perfect 3fs* can be compressed into one task: "Conjugate the Qal perfect for all persons" — which tests all three at once.

---

## Student-Topic Learning Speeds

Each student has an **ability** score (initially estimated from diagnostic). Each topic has a **difficulty** score (calibrated from aggregate performance). Their **ratio** determines:

```
learning_speed = student_ability / topic_difficulty
```

| Ratio | Meaning | Behavior |
|-------|---------|----------|
| > 1.5 | Student excels at this topic | Long spacing, few reviews needed |
| 0.8-1.5 | Typical | Normal FSRS spacing |
| 0.4-0.8 | Struggling | Shorter spacing, more reviews |
| < 0.4 | Likely missing prerequisites | Trigger remedial review of prereqs |

The ratio is **updated after every response** via Bayesian inference. Over time, the system builds a profile of which topics each student finds easy/hard.

---

## Targeted Remediation

When a student fails a lesson, the system follows this protocol:

```
Student fails lesson on "Qal Imperfect"
    │
    ├── (95% of cases) Wait, consolidate, retry later
    │   → Pass rate on retry: 80%
    │
    └── (5%) Fail retry in the same place
        │
        ├── Locate the key prerequisite of the failed knowledge point
        │   (pre-linked during content creation)
        │
        └── Assign remedial review on that prerequisite
            Example: "You're struggling with Qal Imperfect 3ms
                      because the prefix patterns are confusing.
                      Let's review the Qal Perfect first."
```

### Remediation Types

| Type | Trigger | Action |
|------|---------|--------|
| **Corrective** | Fail a question | Give more questions on that specific point |
| **Preventative** | Low learning speed predicted for upcoming topic | Slow down spacing on related prerequisites |
| **Foundational** | Diagnostic detects missing knowledge below course level | Assign lessons on missing foundations, prioritize ones blocking most progress |
| **Content** | >5% of students fail same lesson | Analyze data, add scaffolding, write better worked examples |

---

## Gamification

| Element | Implementation | Purpose |
|---------|---------------|---------|
| **XP** | 1 XP per minute of successful practice | Measure effort |
| **Bonus XP** | 1.5× for first perfect-pass of a lesson | Incentivize quality |
| **Streak** | Consecutive days of ≥15 min practice | Build habit |
| **Leagues** | Weekly ranking in groups of 25 | Competitive motivation |
| **Progress** | % of knowledge graph mastered | Long-term goal visibility |
| **Badges** | Level milestones (10%, 25%, 50%, 75%, 100%) | Celebratory micro-goals |

### XP-Time Equivalence

```
Reading a passage aloud from memory:   ~3 XP
Conjugating a binyan table:            ~5 XP
Parsing a verse's grammar:             ~5 XP
Mastering a new letter:                ~10 XP
Mastering a new binyan:                ~60 XP
```

---

## Integration with Existing ScriptureEngine

The Hebrew teaching system is **not a separate app** — it's a new set of tools, tables, and UI components that integrate into ScriptureEngine:

| Component | What It Provides |
|-----------|-----------------|
| `lib/teaching/` | Knowledge graph, lesson engine, FIRe scheduler, remediation |
| `lib/teaching/graph.py` | ~200 topics with weighted prerequisites and encompassing weights |
| `lib/teaching/lesson.py` | Lesson generator: explanation + worked example + practice problems |
| `lib/teaching/scheduler.py` | FIRe-enhanced FSRS: per-student-per-topic spacing with implicit credit |
| `lib/teaching/remediation.py` | Targeted remediation: detect failure point, find key prerequisite, assign review |
| `lib/teaching/gamification.py` | XP, streaks, leagues, badges |
| `lib/db.py` | New tables: `hebrew_topics`, `hebrew_prerequisites`, `hebrew_lessons`, `hebrew_practice_items`, `hebrew_knowledge_state`, `hebrew_xp_log` |
| `tools/teaching/` | CLI tools for each operation |
| MCP tools | `hebrew_assess`, `hebrew_lesson`, `hebrew_review`, `hebrew_remediate` |
| Frontend | Hebrew tab with lesson view, practice view, progress dashboard |

### Data Sources Already Available

| Need | Source |
|------|--------|
| Aleph-bet | Already in gematria table (23K Hebrew verses) |
| Vowels | `lib/hebrew_util.py` handles all vowel encoding |
| Root families | `lib/lexicon` has 7,853 roots extracted |
| Words | `gematria` table has every word with lemma |
| Grammar morphology | `lib/morphology.py` parses WLC codes |
| Reading passages | 23K Hebrew verses in the DB |
| Connections | 1M+ typed connections for reading enrichment |

---

## Build Order

```
Phase H1 ── Knowledge Graph ──┐
    (~200 topics, prerequisites, encompassing weights)
                               ├── Phase H3 ── Assessment ──┐
Phase H2 ── Content ───────────┘    (practice items,       │
    (explanations, worked              BLIM engine, mastery    │
     examples, practice items)         tracking)               │
                                                               ├── 🚀 HEBREW MVP
Phase H4 ── FIRe SRS ─────────────────────────────────────────┘
    (per-student-per-topic spacing, implicit credit)

Phase H5 ── Gamification ── (XP, streaks, leagues, badges)
    (independent, can start parallel with H3)

Phase H6 ── Targeted Remediation ──
    (key prerequisite linking, corrective/preventative/foundational)

Phase H7 ── Memorization Integration ──
    (Hebrew scripture into the FSRS memorization module,
     verses as reading passages, memory palace with Hebrew)
```

### 🎯 Hebrew MVP v0.1

After H1+H2+H3:
- ~200 topics with full content
- Practice items for each topic (recognition, production, parsing)
- Mastery tracking per student
- Basic linear progression (no SRS yet, no FIRe)
- Student can learn aleph-bet through basic verb conjugation

### 🎯 Hebrew Full v1.0

After H4+H5+H6+H7:
- FIRe-enhanced SRS across all topics
- Gamification with XP, streaks, leagues
- Targeted remediation
- Hebrew scripture memorization integrated with existing FSRS module
- Reading Tanakh passages with full grammar parsing support

---

## Key Techniques from The Math Academy Way Applied

| Technique | How It Maps to Hebrew |
|-----------|----------------------|
| **Knowledge Graph** | 7 levels, ~200 topics, weighted prerequisites |
| **Mastery Learning** | Must pass each topic (≥80% on practice) before advancing |
| **Minimizing Cognitive Load** | Scaffolded lessons: explanation → worked example → guided practice → independent practice |
| **Developing Automaticity** | Timed letter recognition drills, speed targets for each level |
| **Layering** | Each higher level reinforces lower levels; reading a verse practices all levels at once |
| **Non-Interference** | Similar binyanim (Piel/Pual) are spaced apart; similar letters (bet/vet, shin/sin) aren't taught consecutively |
| **Spaced Repetition (FIRe)** | Per-topic scheduling with fractional implicit credit from reading |
| **Interleaving** | Reviews mix different grammar topics; not blocked by binyan |
| **Testing Effect** | All practice is retrieval-based; no passive re-reading of grammar tables |
| **Targeted Remediation** | Pinpoint exact letter/rule/root causing the failure |
| **Gamification** | XP, streaks, leagues, badges |
| **Deliberate Practice** | Practice at edge of ability; struggling is expected and productive |
| **Direct Instruction** | Clear explanations before practice; no discovery learning for grammar rules |
| **Expertise Reversal Effect** | Beginners get worked examples; advanced students get minimal scaffolding |

---

## Files to Create

```
lib/
└── teaching/
    ├── __init__.py           — Module init, exports
    ├── graph.py              — Hebrew knowledge graph (200 topics, prerequisites)
    ├── lesson.py             — Lesson generator and practice item creator
    ├── scheduler.py          — FIRe-enhanced spaced repetition
    ├── remediation.py        — Targeted remediation engine
    └── gamification.py       — XP, streaks, leagues

lib/api/
└── teaching.py               — MCP tools for Hebrew teaching

tools/
└── teaching.py               — CLI tools
```

## Files to Modify

```
lib/db.py                     — New tables (hebrew_topics, hebrew_knowledge_state, etc.)
web/server.py                 — Hebrew API endpoints
frontend/src/components/      — Hebrew lesson view, practice view, dashboard
docs/wiki/_index.md           — Reference this plan
```
