# Memorization Techniques: Comparison & Implementation

How each evidence-based technique maps to a specific feature in the software.

---

## The Core Workflow

A verse goes through four stages — each stage uses different techniques:

```
STAGE 1         STAGE 2           STAGE 3            STAGE 4
UNDERSTAND  →  ENCODE         →  RETAIN          →  EMBED
             
Read the     Create memory     Space-repeated     Recite from
passage.     triggers:         review with        memory in
Study its    images, audio,    progressive        daily life.
meaning.     palace loci.      hint levels.       Track progress.
```

---

## Technique Comparison Table

| # | Technique | Evidence Level | Cognitive Mechanism | Implemented As | Phase | Works Without GPU? |
|---|-----------|---------------|---------------------|----------------|-------|-------------------|
| 1 | **Spaced Repetition** | ⭐⭐⭐ Gold standard (Dunlosky 2013, Cepeda 2006) | Forgetting curve countermeasure — reviewing just before you'd forget strengthens neural trace | **FSRS-5 algorithm** in Go backend. Same engine as Anki 23.10+. Each card gets stability/difficulty scores. Intervals grow: 1d → 3d → 1w → 1mo → 3mo. | P1/P2 | ✅ Yes |
| 2 | **Active Recall** | ⭐⭐⭐ Gold standard (Roediger & Karpicke 2006, Dunlosky 2013) | Retrieval practice — the act of pulling information from memory strengthens it more than any amount of rereading | **6 progressive hint levels** during review. Each card forces retrieval — you never see the answer before attempting recall. | P7 | ✅ Yes |
| 3 | **First-Letter Method** | ⭐⭐ High (Bible Memory App, ScriptureTyper) | Cued recall — first letters act as retrieval cues without giving the full answer | **Hint level 1**: verse shown as `T w h I h i m h, t I m n s a t.` Your brain must fill in every word. | P7 | ✅ Yes |
| 4 | **Production Effect** | ⭐⭐ High (Eghbaria-Ghanamah 2021) | Saying words aloud creates distinct motor + auditory memory traces — more durable than silent reading | **Audio Studio**: record yourself reciting. **Audio card type**: during review, plays your recording as the prompt. You must continue from memory. | P8 | ✅ Yes |
| 5 | **Method of Loci (Memory Palace)** | ⭐⭐ High (Yates 1966, Foer 2011) | Piggybacks abstract verbal info onto evolutionarily ancient spatial memory system | **Palace Builder**: upload a photo of your living room, click to place "loci" (anchors), assign a verse to each. **Palace Walk**: slideshow through loci in order. | P5/P6 | ✅ Yes (no AI needed for palaces themselves) |
| 6 | **Visual Mnemonics** | ⭐⭐ High (imagery-for-text, Dunlosky 2013) | Concrete images are more memorable than abstract words — dual coding theory | **AI-generated concept images**: each verse gets a visual scene. Or **Openverse search**: free CC-licensed biblical art. Or **manual upload**: your own image. | P4 | ✅ Yes (Openverse or upload) |
| 7 | **Dual Coding** | ⭐⭐ High (Paivio 1986) | Information encoded in two formats (verbal + visual) is more retrievable than either alone | **Review cards show BOTH**: verse text + concept image + palace photo (where assigned). Three representations of the same content. | P3/P4/P7 | ✅ Yes |
| 8 | **Chunking** | ⭐⭐ High (Miller 1956) | Working memory holds ~7±2 items. Grouping words into phrases reduces cognitive load. | **Natural chunking**: verses are discrete units. **Palace loci**: each locus holds ~1-3 verses, creating meaningful chunks. **Progressive building**: learn 1 verse → add next → recite together. | P5 | ✅ Yes |
| 9 | **Multi-Sensory Integration** | ⭐⭐ High (multimodal learning) | Engaging multiple senses creates redundant retrieval paths — if one path degrades, others remain | **All channels**: visual (images, text, photos) + auditory (TTS, recordings) + spatial (palace loci) + kinesthetic (clicking ratings, recording audio, tapping through walk). | P3-P8 | ✅ Yes |
| 10 | **Metacognitive Tracking** | ⭐ Moderate (self-regulated learning) | Seeing your weak spots lets you allocate study time effectively | **Analytics dashboard**: streak calendar, accuracy trend line, heat map of weak verses, per-card success rates. | P9 | ✅ Yes |
| 11 | **Elaborative Encoding** | ⭐⭐ High (Craik & Tulving 1975) | Deeper processing at encoding time creates stronger, more distinct memory traces | **ScriptureEngine integration**: before memorizing, user can study verse connections, cross-references, lexicon, gematria. Understanding → better retention. | Built-in (ScriptureEngine) | ✅ Yes |
| 12 | **Distributed Practice** | ⭐⭐⭐ Gold standard (Dunlosky 2013) | Spacing learning across multiple sessions is dramatically more effective than massed practice | **Daily review queue**: FSRS schedules cards across days. **Streak tracking**: Dashboard shows consecutive days. Notification to maintain habit. | P2/P9 | ✅ Yes |
| 13 | **Progressive Scaffolding** | ⭐⭐ High (Vygotsky, Bruner) | Gradually reduce support as competence increases — builds independence | **Hint levels 0→5**: Full text → First letters → Image only → Location only → Audio only → Blank. Each level removes one layer of support. You advance on success, regress on failure. | P7 | ✅ Yes |

---

## Detailed Breakdown: How Each Technique Works in the App

### 1. Spaced Repetition (FSRS-5)

```
┌─────────────────────────────────────────────────────┐
│  CARD STATE (stored per verse per card_type)          │
│                                                       │
│  stability: 45.2    ← memory strength in days        │
│  difficulty: 0.37   ← 0=easiest, 1=hardest           │
│  elapsed_days: 12   ← days since last review          │
│  retrievability: 0.87 ← probability you'd recall today│
│  next_review: 2026-08-15  ← scheduled due date        │
└─────────────────────────────────────────────────────┘
```

**What the user sees:** A queue of due cards. They rate each one.

**After rating:**
- **Again** → Reset interval, increase difficulty. Card returns later today.
- **Hard** → Short interval, slight difficulty increase.
- **Good** → Normal interval growth. Sweet spot.
- **Easy** → Longer interval, decrease difficulty.

**The math** (implemented in Go):
```
next_stability = stability * (1 + f(difficulty, rating))
next_difficulty = difficulty + g(difficulty, rating)  
next_interval = stability * ln(target_retention) / ln(0.9)
```

### 2. Active Recall — Progressive Hint Levels

During review, each card type progresses through levels independently:

| Level | Text Card | Image Card | Location Card | Audio Card |
|-------|-----------|------------|---------------|------------|
| **0** | Full verse text | Full verse + image | Full verse + photo | Full verse + audio |
| **1** | **First letters only** | Full verse + image | Full verse + photo | Full verse + audio |
| **2** | Image only + reference | **Image only** | Image + photo | Image + audio |
| **3** | Palace photo + ref | Palace photo + ref | **Palace photo only** | Palace photo + audio |
| **4** | Audio prompt | Audio prompt | Audio prompt | **Audio only** |
| **5** | **Reference only (blank)** | **Reference only** | **Reference only** | **Reference only** |

**Bold** = the card type's "signature" level. Other levels borrow from other modalities.

**Rating advances the level:**
- Good/Easy → level += 1 (up to 5)
- Again → level = max(0, level - 1)

### 3. Method of Loci — Memory Palace

```
┌─────────────────────────────────────────────────────────┐
│                    MEMORY PALACE                         │
│                                                          │
│  ┌──────────────────────────────────────┐                │
│  │  📸 YOUR LIVING ROOM PHOTO           │                │
│  │                                      │                │
│  │  🏷️ Couch      ← "John 3:16"       │                │
│  │     (x: 0.2, y: 0.6)                │                │
│  │                                      │                │
│  │  🏷️ Bookshelf  ← "Psalm 23:1-4"    │                │
│  │     (x: 0.7, y: 0.3)                │                │
│  │                                      │                │
│  │  🏷️ Window    ← "Romans 8:28"      │                │
│  │     (x: 0.5, y: 0.2)                │                │
│  └──────────────────────────────────────┘                │
│                                                          │
│  Walk mode: [▶ Play]  → slides through loci in order    │
│  Each stop: shows composite image + verse text           │
└─────────────────────────────────────────────────────────┘
```

**Why it works for verbatim text:**
- **Spatial binding**: your brain remembers where things are. The verse gets attached to a physical location.
- **Serial order**: walking through loci in sequence preserves chapter order.
- **Visual + spatial**: the composite image (concept blended into your room) creates a unique, memorable scene.

### 4. The First-Letter Method

```
Full text:  "Thy word have I hid in mine heart, that I might not sin against thee."
First letters:
             T w h I h i m h, t I m n s a t.
             
Your job:    Fill in every word from these letter cues.
```

**Implementation:** When a card reaches hint level 1, the Go API returns the first-letter string instead of full text. The frontend renders it letter-by-letter. Tapping "Show Answer" reveals the full text for self-checking.

### 5. Production Effect — Audio

```
┌───────────────────────────────────────────────┐
│  AUDIO STUDIO                                  │
│                                                │
│  Verse: "I am the good shepherd" (John 10:11)  │
│                                                │
│  [🔴 Record]  [⏹ Stop]  [▶ Playback]         │
│                                                │
│  🎤 Recorded: 2026-07-06  |  0:12             │
│                                                │
│  During review: audio card plays recording     │
│  and you must continue from memory.            │
└───────────────────────────────────────────────┘
```

**Why saying aloud > silent reading:**
- Motor cortex activation (mouth/tongue movements)
- Auditory cortex activation (hearing your own voice)
- Self-reference effect (your voice > stranger's voice)
- The Eghbaria-Ghanamah (2021) study found recitation produced measurable retention gains at 6 months vs. passive listening.

### 6. Visual Mnemonics — Image Pipeline

```
┌───────────────────────────────────────────────┐
│  IMAGE SOURCES                                 │
│                                                │
│  Verse: "I am the good shepherd"               │
│                                                │
│  1. 🎨 AI Generation (ComfyUI)  [if GPU]      │
│     → "A glowing shepherd with staff,          │
│        surrounded by sheep, oil painting"      │
│     → ~5 seconds                              │
│                                                │
│  2. 🔍 Openverse Search  [always works]       │
│     → "good shepherd bible"                    │
│     → Picks best CC-licensed image            │
│     → ~1 second                               │
│                                                │
│  3. 📁 Upload  [always works]                 │
│     → Pick any image from your device          │
│     → Instant                                 │
└───────────────────────────────────────────────┘
```

### 7. Dual Coding

Every verse gets stored with multiple representations:

```
VERSE: "I am the good shepherd" (John 10:11)
  ├── 📝 Text: "I am the good shepherd..."
  ├── 🖼️ Concept image: [shepherd with sheep]
  ├── 📍 Palace photo: [living room, locus: bookshelf]
  └── 🎵 Audio: [user's recording]

During review, any ONE of these can serve as the retrieval cue
for recalling the others.
```

If you forget the text, the image might trigger it. If the image fails, the location might trigger it. **Redundant encoding = resilient memory.**

---

## Implementation Timeline

| Phase | Techniques Implemented | What Ships |
|-------|----------------------|------------|
| **P1** | Spaced Repetition (FSRS core) | Go backend, DB schema, FSRS algorithm |
| **P2** | Spaced Repetition (review queue) | Card creation, review queue, rating endpoints |
| **P3** | Active Recall (basic), Progressive Scaffolding | Memorize dashboard, review session UI |
| **P4** | Visual Mnemonics, Dual Coding (images) | ComfyUI + Openverse + upload, concept images |
| **P5** | Method of Loci, Chunking | Palace builder, loci, verse assignment |
| **P6** | Dual Coding (composites), Method of Loci (walk) | Composite images, Palace Walk slideshow |
| **P7** | Active Recall (full), First-Letter Method, Progressive Scaffolding | 6 hint levels, adaptive progression |
| **P8** | Production Effect, Multi-Sensory | Audio recording, audio card type |
| **P9** | Metacognitive Tracking, Distributed Practice | Analytics, streak tracking, heat maps |

---

## Summary: Why This Combination

**No single technique is sufficient.** The best memorizers use multiple techniques together:

| If you only use... | You get... |
|--------------------|------------|
| Spaced repetition alone | Good retention, but slow — no mnemonics to accelerate encoding |
| Memory palace alone | Great serial recall, but imprecise wording — loses verbatim accuracy |
| First-letter alone | Good verbatim accuracy, but no long-term schedule — fades without SRS |
| Audio alone | Strong auditory memory, but no visual backup — single point of failure |
| Images alone | Memorable concepts, but no retrieval practice — passive, not active |

| This system combines... | Result |
|------------------------|--------|
| SRS + Active Recall + First-Letter + Palace + Images + Audio | **All retrieval paths covered. Verbatim accuracy. Long-term durability. Daily habit enforced.** |

---

## Caveats & Limitations

1. **Discipline required** — the best SRS algorithm won't help if you don't do the reviews. The streak tracker and notifications help, but it's on you.
2. **Verbatim memory is hard** — even with all these techniques, word-perfect recall of long passages takes months of consistent work. The research says ~2 years for a book-length passage at 1 new verse/day.
3. **Palace builder has a learning curve** — the Method of Loci feels unnatural at first. It gets faster with practice.
4. **AI images are a bonus, not a requirement** — the system works completely with Openverse (free, no GPU). AI adds specificity but isn't needed.
