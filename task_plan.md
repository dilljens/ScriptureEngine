# Scripture Engine — Implementation Plan

> Consolidated from: MASTER_PLAN.md, trigram-fts-plan.md, hebrew-enhancement-plan.md,
> knowledge-assessment-plan.md, rabbinic-kabbalistic-tools.md, llm-lexicon-plan.md,
> macro-analysis-plan.md, progress.md, findings.md
>
> **Total backlog: ~40h | Phases execute sequentially | Tracks within phases run in parallel**

## Goal

Ship the remaining ~40h of Scripture Engine features: polish quick wins (Phase 5), Hebrew language enhancements (Phase 6), and the adaptive knowledge assessment engine (Phase 7). Trigram FTS5 is a standalone track that can interleave with any phase.

---

## Requirements

- [ ] R1: Phase 5 — Infrastructure polish + memorization completion + quick wins
- [ ] R2: Phase 6 — Hebrew teaching enhancements (7 features: cloze, frequency vocab, passage study mode, two-way translation, daily maintenance, audio-first, Hebrew-only visual)
- [ ] R3: Phase 7 — Assessment engine (domain definition → prerequisite graph → adaptive engine → item generation → calibration → FSRS → progress tracking → recommendations)
- [ ] R4: Track 0 — Trigram FTS5 typo-tolerant search (standalone, any phase)
- [ ] R5: All existing tests continue to pass after each phase
- [ ] R6: No new external dependencies beyond what's already installed
- [ ] R7: No regressions in any existing functionality

---

## Pre-resolved Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Plan format | Multi-track within sequential phases | Parallel workstreams where possible, but phases have natural ordering (quick wins → language → assessment) |
| Trigram FTS5 | Standalone track | Zero dependency on other work; can land at any time |
| Assessment engine | API-first, anonymous-first (localStorage) | No auth dependency; React frontend consumes later |
| Assessment items | Auto-generated from connection data | 1,000+ items feasible via templates; hand-curation too slow |
| Assessment model | BKT + KST hybrid | BKT for per-item mastery; KST for prerequisite structure and fringe |
| Hebrew features | No new backend endpoints where reuse possible | Existing CardRenderer/CardQueue + api.js can absorb most features |
| Sefirotic mapping | Seed table algorithmically, then agent refines | Keyword-based seeding is fast; agent reading adds accuracy |
| Multi-mode FIRe | Finish remaining work (penalty flow) from ref'd implementation review | Credit flow already built; penalty flow is the gap |
| Entity links | Algorithmic extraction from verse text | Upgrade from limited hardcoded entities to text-derived ones |
| LLM lexicon | Agent batch-generates definitions | Ongoing work between feature sessions; not a blocking dependency |

---

## Track 0: Trigram FTS5 Search `[ ]`

> **Effort: ~2h | Standalone — any phase, zero external dependencies**
> Source: `trigram-fts-plan.md`

Typo-tolerant FTS5 search using the built-in SQLite trigram tokenizer. Replaces the `LIKE '%...%'` fallback path with real ranked substring matching across English, Hebrew, and Greek.

### Phase 0A: Create Index Script `[ ]`
- [ ] Create `scripts/build_fts_index.py`
  - Creates `verses_fts_trigram` virtual table with `tokenize='trigram'`
  - Single `search_text` column combining English + Hebrew + Greek
  - Supports `--reset` and `--dry-run` flags
  - Reports total indexed + elapsed time (~40K+ rows)
- 📏 Scope: 1 new file, ~80 lines
- ✅ Checkpoint: `python3 scripts/build_fts_index.py` exits cleanly, reports verse count
- ⚙ Fallback: Manual invocation, not part of automated pipeline

### Phase 0B: Wire Into `_keyword_search` `[ ]`
- [ ] Add `_trigram_search(conn, query, limit)` helper in `web/server.py`
- [ ] Escape FTS5 special chars; short queries (<2 chars) fall through to LIKE
- [ ] Simplify `_keyword_search` — try trigram first, fall back to LIKE on exception
- 📏 Scope: 1 file, ~50 lines
- ✅ Checkpoint: `GET /api/v1/semantic-search?q=genis` returns Genesis verses
- ⚙ Fallback: LIKE path still works if trigram table is absent

### Phase 0C: Update `lib/api/search.py` `[ ]`
- [ ] Update `search_text()` to try trigram FTS5 before LIKE
- [ ] Update `search_xlingual()` to use trigram for the English branch
- [ ] Keep backward compatibility — LIKE fallback preserved
- 📏 Scope: 1 file, ~30 lines
- ✅ Checkpoint: `python3 tools/search.py '{"query": "covenent"}'` works with typo
- ⚙ Fallback: LIKE fallback preserved

### Phase 0D: Hebrew/Greek Integration `[ ]`
- [ ] Update `_search_hebrew` / `_search_greek` in `web/server.py` to try trigram first
- [ ] Trigram handles Hebrew/Greek naturally via `search_text` column (language prefixes)
- 📏 Scope: 1 file, ~30 lines
- ✅ Checkpoint: `GET /api/v1/semantic-search?q=ברית` finds Hebrew matches
- ⚙ Fallback: Old gematria LIKE path preserved

---

## Phase 5: Polish & Quick Wins `[ ]`

> **Effort: ~5h | Sequential: Phase 5 → Phase 6 → Phase 7**

### Track A: Infrastructure `[ ]`

**Description:** Complete remaining infrastructure items from MASTER_PLAN Phase 0.
**Scope:** ~2 files, ~30 lines

#### Phase A1: ntfy.sh Push Notifications `[ ]`
- [ ] Add ntfy.sh webhook call on health failure to `web/server.py`
- [ ] Load ntfy topic + server URL from env vars (fall back gracefully)
- [ ] Only fires when health check fails (DB unreachable, cache empty)
- ✅ Checkpoint: Health failure triggers ntfy notification (test by toggling env)
- ⚙ Fallback: Graceful no-op if ntfy env vars not set
- **Effort:** 30m

### Track B: Memorization Completion `[ ]`

**Description:** Finish remaining memorization items: sefirotic mapping and multi-mode FIRe penalty flow.
**Scope:** ~4 files, ~200 lines

#### Phase B1: Sefirotic Mapping `[ ]`
- [ ] Create `sefirah_keywords` table (10 sefirot + keyword/concept mappings)
- [ ] Create `generators/sefirot_mapper.py` — algorithmic seed from keyword matching
- [ ] Create passage_connections between verses sharing a sefirah label
- [ ] Create MCP tool `scripture_sefirot(verse_ref)` to look up sefirah mappings
- [ ] Frontend: optional sefirah badge on VerseBlock (display only)
- 📏 Scope: ~3 files, ~150 lines
- ✅ Checkpoint: `GET /api/v1/sefirot/gen.1.1` returns sefirah mappings
- ⚙ Fallback: Agent-driven refinement comes later (keyword seed first)
- **Effort:** 4h

#### Phase B2: Multi-Mode FIRe Penalty Flow `[ ]`
- [ ] When user fails a verse (rating 1 or 2), flow penalty to connected verses
- [ ] Penalty: `stability = stability / (1 + penalty)` on connected verses
- [ ] Penalty direction: from simpler → more complex (failing Gen 1:1 penalizes John 1:1)
- [ ] Deduct `fi_re_credit` on failure: `max(0, credit - penalty)`
- 📏 Scope: ~1 file, ~50 lines
- ✅ Checkpoint: Failing a verse reduces stability of connected verses
- ⚙ Fallback: No penalty flow on errors (graceful skip)
- **Effort:** 30m (follows existing FIRe pattern)

---

## Phase 6: Hebrew & Language Enhancements `[ ]`

> **Effort: ~15h | Sequential after Phase 5**

### Track C: Hebrew Teaching Features `[ ]`

**Description:** Seven Hebrew enhancement features, ordered by impact/effort ratio.
**Scope:** ~8 files, ~600 lines

#### Phase C1: Cloze Deletion Card Type `[ ]`
- [ ] Add `cloze` type to CardRenderer
- [ ] Card data: `{text_with_blanks, answer, verse_ref}`
- [ ] Front: verse with `[___]` blanked word(s); Back: complete verse, answer highlighted
- [ ] Generate from existing verses by masking verbs/keywords
- 📏 Scope: 1 file, ~50 lines
- ✅ Checkpoint: CardRenderer renders a cloze card with blanks → reveals on click
- ⚙ Fallback: Stub card type with static test data
- **Effort:** 1h

#### Phase C2: Frequency-Ordered Top 1000 Vocab `[ ]`
- [ ] Query lexicon `ORDER BY frequency DESC LIMIT 1000`
- [ ] Skip function words (prepositions, particles, conjunctions)
- [ ] Create `hebrew_vocab_frequency` table mapping lemma→rank
- [ ] Add "Most Frequent Words" section to HebrewLearnView
- [ ] Allow studying by frequency range (top 100, 100-500, etc.)
- 📏 Scope: 2 files, ~60 lines
- ✅ Checkpoint: HebrewLearnView shows frequency-ordered vocab list
- ⚙ Fallback: Server-side sorting only, no dedicated table
- **Effort:** 1h

#### Phase C3: Passage Study Mode (LingQ-Style) `[ ]`
- [ ] **Critical feature.** Word-by-word parsed passage reader.
- [ ] Backend: `GET /api/v1/passage/{ref}/analyze` — word-by-word breakdown (existing endpoint extend)
- [ ] `PassageReader.jsx` — renders passage with color-coded known/new words
- [ ] Extend existing `WordPopup.jsx` with frequency data + "Add to vocab cards"
- [ ] Click word → popup: lemma, Strong's, root, frequency, +add to FSRS cards
- 📏 Scope: 3 files, ~200 lines
- ✅ Checkpoint: User can select a passage, see it parsed word-by-word, click words for info
- ⚙ Fallback: Use existing HebrewPassageReader as base; incremental enhancement
- **Effort:** 4h

#### Phase C4: Two-Way Translation Cards `[ ]`
- [ ] Add `translation` card type to CardRenderer
- [ ] Front: English text; Back: Hebrew + transliteration + audio
- [ ] Generate pairs from existing bilingual verse data
- [ ] FSRS-5 scheduling on production cards (reuse existing card system)
- 📏 Scope: 1 file, ~40 lines
- ✅ Checkpoint: Card renders English→Hebrew with audio on back
- ⚙ Fallback: Skip audio, just text + transliteration
- **Effort:** 2h

#### Phase C5: Daily Maintenance Mode `[ ]`
- [ ] Backend: `GET /api/v1/hebrew/verse-of-day` — random verse with analysis
- [ ] Frontend: simple component in HebrewLearnView
- [ ] Word-by-word breakdown + audio (from existing infrastructure)
- 📏 Scope: 2 files, ~60 lines
- ✅ Checkpoint: HebrewLearnView shows a verse of the day with analysis
- ⚙ Fallback: Static verse selection (pseudorandom from verse ID)
- **Effort:** 2h

#### Phase C6: Audio-First / Commute Mode `[ ]`
- [ ] `AudioReviewSession` component — eyes-free audio review
- [ ] Hebrew word/phrase → pause for recall → audio gives answer → next
- [ ] Uses existing TTS or pre-recorded audio
- [ ] CardQueue adaptation: no on-screen text, just audio controls
- [ ] Progress tracked via FSRS-5 (same as visual cards)
- 📏 Scope: 2 files, ~120 lines
- ✅ Checkpoint: AudioReviewSession plays Hebrew, pauses, plays answer
- ⚙ Fallback: Skip commute mode; use standard CardQueue with screen on
- **Effort:** 3h

#### Phase C7: Hebrew-Only Visual Mode `[ ]`
- [ ] Add `hebrewOnly` prop to VocabCardRenderer
- [ ] Toggle: hide English translation, show only Hebrew + transliteration
- [ ] User reveals meaning by clicking/flipping card
- [ ] Per-user setting (localStorage)
- 📏 Scope: 1 file, ~40 lines
- ✅ Checkpoint: VocabCard renders Hebrew-only when toggled
- ⚙ Fallback: No-op toggle (always show English)
- **Effort:** 2h

### Track D: Entity Links Expansion `[ ]`

**Description:** Expand entity coverage from 559 entities toward comprehensive text-derived extraction.
**Scope:** ~2 files, ~200 lines

#### Phase D1: Algorithmic Entity Extraction `[ ]`
- [ ] Create `scripts/expand_entities.py` — extract named entities from verse text
- [ ] Use existing name lists + pattern matching (capitalized names, constructed forms)
- [ ] Insert into `entity_links` + `entities` tables
- [ ] Cross-reference with existing lexicon for Hebrew/Greek name roots
- 📏 Scope: 2 files, ~200 lines
- ✅ Checkpoint: Entity count increases from 559 to 2,000+
- ⚙ Fallback: Manual entity addition scripts
- **Effort:** 4h

### Track E: Agent-Written Lexicon Definitions (Ongoing) `[ ]`

**Description:** Batch-generate definitions for remaining ~11,100 lemmas by agent reading verses.
**Scope:** No code changes — agent reads verse texts and writes to `lexicon.definition` field.

#### Phase E1: First 500 Lemma Definitions `[ ]`
- [ ] Agent reads 20+ verses per lemma, writes contextual definition
- [ ] Priority: high-frequency lemmas first (>100 occurrences)
- [ ] Output: SQL UPDATE statements to `data/agent_connections/lexicon_defs.sql`
- 📏 Scope: SQL output file
- ✅ Checkpoint: 500 definitions added, verifiable via `SELECT count(*) FROM lexicon WHERE definition IS NOT NULL AND definition != ''`
- ⚙ Fallback: Ongoing — 50 definitions per session
- **Effort:** Ongoing between feature sessions

---

## Phase 7: Knowledge Assessment Engine `[ ]`

> **Effort: ~20h | Sequential after Phase 6**

### Track F: Assessment Foundation `[ ]`

**Description:** Define the knowledge domain, build the prerequisite graph, and implement the adaptive assessment engine with item generation. This is a working first version to be enhanced later.
**Scope:** ~7 files, ~700 lines

#### Phase F1: Knowledge Domain Definition `[ ]`
- [ ] Extract atomic items from existing high-quality connections (>=3 stars)
- [ ] Each item = "Connection between Verse A and Verse B of type T"
- [ ] Filter to ~15,000 initial items
- [ ] Classify by PaRDeS level, connection type, layer, quality score
- [ ] Store in `knowledge_items` table
- 📏 Scope: 2 files, ~100 lines
- ✅ Checkpoint: `knowledge_items` populated with 15,000+ items
- ⚙ Fallback: Start with 5,000 items from highest-quality connections only
- **Effort:** 3h

#### Phase F2: Prerequisite Graph `[ ]`
- [ ] Define ~300 prerequisite rules across connection types + PaRDeS levels
- [ ] Store in `knowledge_prerequisites` table (DAG)
- [ ] Rules: `same_lemma` → `same_root` → `same_morphology` (within P'shat)
- [ ] Rules: P'shat → Remez → Drash → Sod (across layers)
- [ ] Rules: simpler connections (linguistic) → complex (sod, interpretive)
- 📏 Scope: 2 files, ~150 lines
- ✅ Checkpoint: Prerequisite DAG is acyclic and covers all major connection types
- ⚙ Fallback: Flat prerequisite map (no hierarchy) for initial phase
- **Effort:** 6h

#### Phase F3: Adaptive Assessment Engine `[ ]`
- [ ] `lib/assessment/engine.py` — BLIM + Bayesian state update
- [ ] Item selection: max information + outer fringe targeting
- [ ] After each response, update user knowledge state
- [ ] Termination: knowledge state converges OR max items reached
- [ ] New MCP tool: `scripture_assessment_start`, `scripture_assessment_answer`
- 📏 Scope: 2 files, ~300 lines
- ✅ Checkpoint: Assessment session runs 10+ items, converges on knowledge state
- ⚙ Fallback: Simple item selection (random) instead of information-theoretic
- **Effort:** 10h

#### Phase F4: Auto-Generate Assessment Items `[ ]`
- [ ] For each `knowledge_item`, generate question templates:
  - Multiple Choice: "Which verse connects to Gen 1:1 via same_lemma?"
  - True/False: "Is there a direct_quotation from Isa 6 to Matt 13?"
  - Classification: "Which PaRDeS level?"
  - Gematria: "What is the value of this word?"
- [ ] Add distractors from other connections of same type
- [ ] Target: 1,000+ items initially, growing automatically
- 📏 Scope: 1 file, ~150 lines
- ✅ Checkpoint: `knowledge_assessment_items` populated with 1,000+ items
- ⚙ Fallback: Start with 200 items, auto-generate more during idle time
- **Effort:** 6h (overlaps with F3 time; net new effort ~6h)

#### Phase F5: Assessment Frontend `[ ]`
- [ ] New `AssessmentSession.jsx` component (or extend existing AssessmentView)
- [ ] Multiple choice + true/false card types
- [ ] Progress bar, question counter, final score display
- [ ] Show knowledge state after session (PaRDeS level mastery, weak areas)
- 📏 Scope: 1 file, ~100 lines
- ✅ Checkpoint: User can complete an assessment session and see results
- ⚙ Fallback: CLI-only assessment via `tools/assess.py`
- **Effort:** 2h

### Track G: IRT & FSRS Calibration `[ ]`

**Description:** Calibrate item difficulty/discrimination and add spaced repetition for assessment items.

#### Phase G1: IRT Calibration `[ ]`
- [ ] Assign prior IRT parameters from connection quality (higher quality = easier)
- [ ] Online calibration from user response data
- [ ] Track item fit statistics
- 📏 Scope: 1 file, ~100 lines
- ✅ Checkpoint: IRT parameters are computed and stored per item
- ⚙ Fallback: Uniform priors for all items
- **Effort:** 4h (moved to Track G to keep Track F focused)

#### Phase G2: FSRS Assessment Spacing `[ ]`
- [ ] Apply FSRS-5 to assessment items (reuse Go SRS or implement lightweight Python)
- [ ] Repetition compression: one question reinforces multiple items
- [ ] Integrate with existing review queue
- 📏 Scope: 1 file, ~100 lines
- ✅ Checkpoint: Assessment items are scheduled with FSRS intervals
- ⚙ Fallback: Simple Ebbinghaus intervals for assessment items
- **Effort:** 4h (moved to Track G)

### Track H: Progress & Recommendations `[ ]`

**Description:** User progress tracking, dashboards, and study recommendations from gap analysis.

#### Phase H1: User Progress Tracking `[ ]`
- [ ] `user_knowledge`, `assessment_sessions`, `session_items` tables (or localStorage)
- [ ] Dashboard: mastery by PaRDeS level, by book, fringe items, weak areas
- [ ] Anonymous-first: localStorage initially, optional auth later
- 📏 Scope: 2 files, ~120 lines
- ✅ Checkpoint: User sees mastery dashboard after completing an assessment
- ⚙ Fallback: Raw JSON output in browser console
- **Effort:** 4h

#### Phase H2: Study Recommendations `[ ]`
- [ ] Outer fringe targeting → "ready to learn next"
- [ ] Weakest prerequisite identification → "here's what's blocking you"
- [ ] Integration with existing guided study system
- [ ] Reading recommendations based on gaps
- 📏 Scope: 2 files, ~100 lines
- ✅ Checkpoint: After assessment, user sees 3+ study recommendations
- ⚙ Fallback: Show top 5 weakest PaRDeS levels, no specific recommendations
- **Effort:** 4h

---

## Acceptance Criteria

### Project-Level
- [ ] All existing tests pass (pytest + Go + Playwright)
- [ ] 0 new convention violations
- [ ] No regressions in existing API endpoints (verified by test suite)

### Track 0 — Trigram FTS5
- [ ] `scripts/build_fts_index.py` creates `verses_fts_trigram` with 40K+ rows
- [ ] `"genis"` returns Genesis verses
- [ ] `"covenent"` (typo) returns covenant verses
- [ ] Hebrew search `"ברית"` works via trigram
- [ ] All 3 search paths use trigram with LIKE fallback

### Phase 5 — Polish & Quick Wins
- [ ] ntfy.sh fires on health failure
- [ ] Sefirot endpoint returns mappings for any verse with keyword matches
- [ ] FIRe penalty flow reduces stability on failed connected verses

### Phase 6 — Hebrew & Language
- [ ] Cloze cards render, blank → reveal on click
- [ ] Frequency vocab list in HebrewLearnView
- [ ] Passage study mode: word-by-word parsed, click for popup
- [ ] Two-way translation cards: English → Hebrew
- [ ] Verse of the day component
- [ ] Audio-first review session
- [ ] Hebrew-only toggle on vocab cards
- [ ] Entity count > 2,000 (from algorithmic extraction)

### Phase 7 — Assessment Engine
- [ ] `knowledge_items` table with 15,000+ items
- [ ] Prerequisite DAG with 300+ rules, acyclic
- [ ] Assessment engine runs an adaptive session (10+ items)
- [ ] 1,000+ auto-generated assessment items
- [ ] User can complete a session and see results

---

## File Change Summary

| Phase | Track | File | Lines |
|-------|-------|------|-------|
| 0 | Trigram | `scripts/build_fts_index.py` | **NEW** +80 |
| 0 | Trigram | `web/server.py` | +80 |
| 0 | Trigram | `lib/api/search.py` | +30 |
| 5A | Infra | `web/server.py` | +20 |
| 5B | Memorization | `generators/sefirot_mapper.py` | **NEW** +80 |
| 5B | Memorization | `lib/api/sefirot.py` | **NEW** +40 |
| 5B | Memorization | `web/routes/sefirot.py` | **NEW** +30 |
| 5B | Memorization | `lib/api/fire_unified.py` | +50 |
| 6C | Hebrew | `frontend/src/components/CardRenderer.jsx` | +50 |
| 6C | Hebrew | `frontend/src/components/PassageReader.jsx` | **NEW** +120 |
| 6C | Hebrew | `frontend/src/components/AudioReviewSession.jsx` | **NEW** +120 |
| 6C | Hebrew | `frontend/src/components/HebrewLearnView.jsx` | +120 |
| 6C | Hebrew | `web/routes/hebrew.py` | +60 |
| 6D | Entities | `scripts/expand_entities.py` | **NEW** +200 |
| 7F | Assessment | `lib/assessment/domain.py` | **NEW** +100 |
| 7F | Assessment | `lib/assessment/prerequisites.py` | **NEW** +150 |
| 7F | Assessment | `lib/assessment/engine.py` | **NEW** +300 |
| 7F | Assessment | `lib/assessment/items.py` | **NEW** +150 |
| 7F | Assessment | `lib/api/assessment.py` | **NEW** +80 |
| 7F | Assessment | `frontend/src/components/AssessmentSession.jsx` | **NEW** +100 |
| 7G | IRT | `lib/assessment/irt.py` | **NEW** +100 |
| 7G | FSRS | `lib/assessment/spaced.py` | **NEW** +100 |
| 7H | Tracking | `lib/assessment/user_model.py` | **NEW** +120 |
| 7H | Tracking | `frontend/.../MasteryDashboard.jsx` | **NEW** +80 |
| | | **Total** | **~2,400 lines** |
