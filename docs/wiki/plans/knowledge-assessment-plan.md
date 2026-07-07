# Knowledge Assessment System & Language/Truth-Seeking Improvements

## Three Tracks

This plan addresses three strategic improvements in parallel:

- **Track A** — Hebrew & Greek language tooling
- **Track B** — Truth-seeking & interpretive bias infrastructure
- **Track C** — Scripture knowledge assessment system (KST-based)

---

## Track A: Hebrew & Greek Language Understanding

### Current State

- Hebrew transliteration engine (`lib/hebrew_util.py`) — handles cantillation stripping, RTL markers, mater lectionis, begadkefat, gemination
- Strong's lemma numbers in gematria table (23,213 Hebrew verses, 7,925 Greek)
- Greek isopsephy computation (`lib/gematria_greek.py`)
- Morphology codes in gematria table (e.g., `HC/Vqw3ms`)
- Lexicon: 11,515 lemma entries, 7,853 roots, 50,216 collocations
- Greek text for NT + Septuagint

### Gaps

| # | Priority | Description |
|---|----------|-------------|
| A1 | High | **No Greek transliteration** — analogous to Hebrew's `lib/hebrew_util.py` |
| A2 | High | **No word-by-word parsing aligned with verses** — gematria table has words but no parse tree or morphological breakdown shown to users |
| A3 | High | **No verb conjugation tables** — morphology codes exist but no system to display parsed meaning ("Qal imperfect 3ms") |
| A4 | Medium | **No Strong's definitions in tool output** — lexicon `definition` field is mostly empty |
| A5 | Medium | **No interlinear display** — no tool showing Hebrew/Greek word + transliteration + Strong's + gloss side-by-side |
| A6 | Low | **No semantic role labeling** — who did what to whom in each verse |

### Plan for Track A

**Phase A1** — Greek transliteration (1-2h)
- New `lib/greek_util.py` with mapping from Greek letters → Latin
- Handle rough/smooth breathings, accents, iota subscript
- Integrate into verse output as `greek_display`

**Phase A2** — Morphological parser (2-3h)
- Create `lib/morphology.py` that translates morphology codes to English
- e.g., `Vqw3ms` → "Verb, Qal, Waw-Consecutive Imperfect, 3rd person masculine singular"
- Add to word-level output in verse display

**Phase A3** — Strong's definitions import (2-3h)
- Import Strong's definitions from StepBible or Open Scriptures
- Populate `lexicon.definition` field
- Add `scripture_strongs` tool for word-level lookup

**Phase A4** — Interlinear tool (3-4h)
- `scripture_interlinear` tool returning aligned word-by-word data
- Each word: Hebrew/Greek, transliteration, Strong's, morphology, gloss
- Combines A1-A3 into a single display

---

## Track B: Truth-Seeking & Interpretive Bias

### Current State

- 9 connection layers (linguistic separated from interpretive)
- PaRDeS level mapping (P'shat = text, Drash = interpretation)
- 5-signal quality calibration
- Statistical controls: Monte Carlo p-value, Bonferroni, FDR
- Null-text baselines (built but not fully used)
- Method pre-registration (anti-p-hacking)
- 17 agent judgment files
- Interpretive generator (24 hardcoded tradition connections)

### Gaps

| # | Priority | Description |
|---|----------|-------------|
| B1 | **Critical** | **Heuristic p-values, not real null-text tests** — validation uses hardcoded p=0.01/0.05 instead of empirically derived values |
| B2 | High | **No sentiment/bias detection** — can't detect when a connection/generator embeds theological agenda |
| B3 | High | **Tradition disagreement not tracked** — conflicting interpretations are independent nodes with no relation |
| B4 | Medium | **No faith-based vs. historical-critical distinction** — both are "interpretive" layer but are epistemologically different |
| B5 | Medium | **No ecumenical consensus rating** — no way to ask "what do most traditions agree on?" |
| B6 | Low | **No AI prompt/model audit trail** — agent judgments don't record what prompt/model generated them |
| B7 | Low | **No cross-canon null baselines** — null text is gibberish Hebrew, not actual scripture from other traditions |

### Plan for Track B

**Phase B1** — Real null-text testing (4-6h)
- Run each generator against shuffled-word + random-letter null text
- Compute empirical p-values from the null distribution
- Update `scripts/validate_connections.py` to use real values
- This is the single most critical truth-seeking fix

**Phase B2** — Interpretive disagreement model (3-4h)
- New table `interpretive_disagreements`
- Links contradictory connections across traditions
- New `scripture_disagreements` tool
- Seed with 20-30 well-known disagreements (Psalm 110, Isaiah 7:14, etc.)

**Phase B3** — Faith vs. historical-critical labels (2-3h)
- Add `hermeneutic` field to interpretive connections
- `"faith"`, `"historical_critical"`, or `"both"`
- Update calibration weights accordingly

**Phase B4** — Ecumenical consensus scoring (3-4h)
- For each verse, compute how many traditions have connected to it
- Add `consensus` field to connection quality output

---

## Track C: Scripture Knowledge Assessment System

### Core Concept

The 10 connection layers + PaRDeS levels form a natural **knowledge space**:
- Each connection type is an atomic "knowledge item" (you either know it or don't)
- Prerequisites emerge from the layer hierarchy: P'shat → Remez → Drash → Sod
- Simpler connections (same_lemma) are prerequisite to complex ones (chiasm, gematria)

### What to Build

**Phase C1** — Define the knowledge domain (2-3h)
- Extract atomic items from existing high-quality (>=3 stars) connections
- Each item = "The connection between Verse A and Verse B of type T"
- Filter to ~15,000 items initially
- Classify by PaRDeS level, connection type, and quality score

**Phase C2** — Build the prerequisite graph (4-6h)
- Define ~300 prerequisite rules across connection types and PaRDeS levels
- Store in `knowledge_prerequisites` table (DAG)
- Example: `same_lemma` → `same_root` → `same_morphology` within P'shat
- Example: P'shat level → Remez level → Drash level → Sod level

**Phase C3** — Adaptive assessment engine (8-12h)
- `lib/assessment/` module with:
  - Item selection (max information + outer fringe targeting)
  - BLIM response model (difficulty, discrimination, guess, slip)
  - Bayesian state update after each response
  - Termination when knowledge state converges or max items reached

**Phase C4** — Auto-generate assessment items (6-8h)
- For each connection, generate question templates:
  - Multiple choice: "Which verse connects to Gen 1:1 via same_lemma?"
  - True/False: "Is there a direct_quotation from Isa 6 to Matt 13?"
  - Classification: "Which PaRDeS level?"
  - Gematria: "What is the value of this word?"
- Add distractors from other connections of the same type
- Target: 1,000+ items initially, growing automatically

**Phase C5** — IRT calibration (4-6h)
- Assign prior IRT parameters from connection quality
- Higher quality = easier item (lower difficulty)
- Online calibration from user response data
- Track item fit statistics

**Phase C6** — Spaced repetition (4-6h)
- Adapt MathAcademy's FIRe concept for implicit practice
- FSRS-based scheduling (stability, difficulty, retrievability)
- Repetition compression — one question reinforces multiple items

**Phase C7** — User progress tracking (6-8h)
- `user_knowledge`, `assessment_sessions`, `session_items` tables
- Dashboard: mastery by PaRDeS level, by book, fringe items, weak areas
- Start with localStorage-based (anonymous); optional auth later

**Phase C8** — Study recommendations (4-6h)
- Outer fringe targeting → "ready to learn next"
- Weakest prerequisite identification → "here's what's blocking you"
- Integration with existing guided study system
- Reading recommendations based on gaps

---

## Implementation Priority & Timeline

```
Week 1-2:   A1 + A3 + B1   (quick wins + critical truth-seeking fix)
Week 2-4:   A2 + C1 + C2   (foundation for assessment)
Week 3-5:   B2 + C3        (assessment engine + disagreement tracking)
Week 4-6:   A4 + C4        (interlinear + item generation)
Week 5-7:   B3 + B4 + C5   (calibration + ecumenical consensus)
Week 6-8:   C6 + C7        (spaced repetition + user tracking)
Week 7-9:   C8             (study recommendations, integration)
```

### Effort

| Phase | Effort | Impact | Dependencies |
|-------|--------|--------|-------------|
| **A1** Greek transliteration | 2h | Medium | None |
| **A3** Strong's definitions | 3h | Medium | None |
| **B1** Real null-text testing | 6h | **Critical** | None |
| **A2** Morphology parser | 3h | Medium | None |
| **C1** Domain definition | 3h | **High** | None (starts from existing data) |
| **C2** Prerequisite graph | 6h | **High** | C1 |
| **B2** Disagreement model | 4h | Medium | None |
| **C3** Assessment engine | 10h | **High** | C1, C2 |
| **A4** Interlinear display | 4h | Medium | A1, A2, A3 |
| **C4** Item generation | 8h | **High** | C1 |
| **B3** Hermeneutic sub-labels | 3h | Medium | B2 |
| **B4** Ecumenical consensus | 4h | Low | B2 |
| **C5** IRT calibration | 6h | High | C3, C4 |
| **C7** User tracking | 8h | High | C3 |
| **C6** Spaced repetition | 6h | Medium | C5 |
| **C8** Study recommendations | 6h | Medium | C7 |

### Files to Create

```
lib/
├── greek_util.py                NEW  (A1)
├── morphology.py                NEW  (A2)
├── assessment/
│   ├── __init__.py              NEW
│   ├── domain.py                NEW  (C1)
│   ├── prerequisites.py         NEW  (C2)
│   ├── engine.py                NEW  (C3)
│   ├── items.py                 NEW  (C4)
│   ├── irt.py                   NEW  (C5)
│   ├── spaced.py                NEW  (C6)
│   └── user_model.py            NEW  (C7)
├── api/
│   ├── assessment.py            NEW  (C3-C8 MCP tools)
lib/controls/
│   └── null_text.py             MOD  (B1)
tools/
│   ├── assess.py                NEW  (CLI)
```

### Key Design Decisions

1. **BKT + KST hybrid** — BKT for per-item mastery tracking (well-supported by pyBKT), KST for prerequisite structure and fringe computation
2. **Anonymous-first** — localStorage-based progress initially, optional auth later
3. **API-first** — Pure Python module with CLI tool + MCP tool, React frontend can consume later
4. **Auto-generation** — Items generated automatically from connection data (faster than hand-curation, adequate quality for low-stakes)

---

## Open Questions

1. **Assessment scope** — All 10 connection layers, or start with a subset (e.g., linguistic + intertextual)?
2. **User identity** — Anonymous (localStorage) or accounts (DB)? Affects C7.
3. **Item quality** — Auto-generated from connections, or hand-curated? Auto is faster, hand is higher quality.
4. **Assessment stakes** — Low-stakes (self-testing/practice) or high-stakes (certification)?
5. **Language** — English-only UI or multi-lingual?
6. **Min connection quality** — What star rating threshold for items? 2★ (suggested), 3★ (probable), or 4★ (strong)?
7. **PaRDeS depth** — All four levels from start, or P'shat first?
8. **Generated vs. curated study paths** — Fully automated recommendations or human-designed?
