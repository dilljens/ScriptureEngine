# Truth-Seeking Framework — Multi-Canon Pattern Consensus

## The Problem

Given multiple canons (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha)
and multiple traditions (Jewish, Christian, LDS, Critical), how do we determine
which interpretations are actually supported by the text vs. which are later
additions?

## The Approach

### Layer 0: Linguistic Ground Truth

The Hebrew and Greek text is the foundation. Everything else builds on this.

- `linguistic` layer connections (same_lemma, same_root, keyword_linking) are
  textual facts — they exist regardless of interpretation
- Gematria values are mathematical facts
- Strong's definitions are lexical facts

**These never change.** They are the anchor.

### Layer 1: Structural Patterns

Chiastic structures, parallelisms, formula markers, and inclusios are patterns
in the text itself. They can be detected algorithmically.

- Neural embedding-based chiastic detection (McGovern et al., NAACL 2025)
- PoS-tag inversion detection (Schneider et al., ACL 2021)
- Existing keyword_distribution, word_counts, structural_formulas tools

**These are discoverable facts** — they either exist in the text or they don't.

### Layer 2: Cross-Canon Consensus

When the same pattern appears across multiple canons, it strengthens the case
that the pattern is intentional.

Examples:
- Creation-temple connection: OT (Gen 1-2, Ex 25-40) + BoM (1 Ne 1) + D&C (D&C 88)
  + Pseudepigrapha (1 Enoch) → strong consensus
- Ex nihilo creation: OT Hebrew (bara + tohu wa-bohu suggests ordering, not
  ex nihilo) + D&C (D&C 29:31-33, 93:29-30 suggests ex nihilo) → mixed signal

**The consensus engine:**
```
For each pattern P:
    For each canon C:
        Count occurrences of P in C
        Score: frequency × significance × layer_weight
    Cross-canon score = agreement across canons
    Label: "supported across N canons" or "unique to one canon"
```

### Layer 3: Tradition Labels

Each connection in the graph already carries a `tradition` field:
- `jewish` — Jewish interpretive tradition
- `christian` — Christian interpretive tradition  
- `lds` — Latter-day Saint tradition
- `critical_scholarship` — Historical-critical scholarship
- `none` — Textual/linguistic (no interpretation)

When a claim appears in only one tradition's connections, it's flagged as
"interpretive — not textually grounded."

## Implementation Phases

### Phase A: JST as Bible Version (current)
- Import JST text from awerkamp markdown as version='JST'
- Store in text_resources table alongside KJV, LSV, etc.
- Build JST diff viewer (KJV ↔ JST side-by-side)

### Phase B: Neural Chiastic Detection
- Clone McGovern et al. (NAACL 2025) approach
- Vectorize verses using existing vec_verses embeddings
- Sliding-window cosine similarity across all works
- Detect chiasms in OT, NT, BoM, D&C, PGP, DSS, Apocrypha
- Store in known_chiasms table with discovered_by='algorithm'

### Phase C: Cross-Canon Pattern Mining
- Run same_lemma, same_root, keyword_linking across works
- Build pattern occurrence matrix: pattern × canon
- Flag patterns with high cross-canon consensus vs. low

### Phase D: Truth Score API
- For any topic/claim:
  - Collect all relevant verses across all canons
  - Show Hebrew/Greek text + gloss
  - Show connection graph paths
  - Show tradition distribution
  - Compute consensus score: "supported by X of Y canons"
  - Flag unsupported interpretations

### Phase E: JS Discourses
- Import from Restoration Archives PDFs
- Store as searchable text in verses table
- Build entity network for Joseph Smith
- Connect JS teachings to biblical passages

---

## Future Pattern Types (Not Yet Implemented)

### 1. Leitwort / Leading Word Repetition (Robert Alter)
Detect key root words repeated throughout a passage to signal its theme.
- Detect by: frequency analysis of root words per passage, flag peaks
- Example: Gen 1 — "bless" (*barak*), Judges — "right in his own eyes"
- Effort: 2h — build on existing word frequency tools

### 2. Type-Scenes (Recurring Narrative Templates)
Standardized narrative situations that recur with intentional variation:
- **Annunciation to barren wife**: Sarah, Rebekah, Rachel, Hannah, Elizabeth
- **Betrothal at a well**: Abraham's servant/Rebecca, Jacob/Rachel, Moses/Zipporah
- **Wife-sister episodes**: Abraham (Gen 12, 20), Isaac (Gen 26)
- **Call narratives**: Moses, Gideon, Isaiah, Jeremiah
- Detect by: template matching with shared keywords + narrative structure
- Effort: 3h

### 3. Gileadi's Servant-Tyrant Parallelism (21 Pairs)
21 specific antithetical verse pairs linking Isaiah 14 (King of Babylon) 
and Isaiah 52-53 (King of Zion). The King of Babylon is exalted then
humiliated; the King of Zion is humbled then exalted.
- Already partially in engine — could be formalized as a pattern type
- Effort: 1h — add explicit pair mapping

### 4. Covenant Formula Pattern
Standard ancient Near Eastern covenant structure:
Preamble → Historical Prologue → Stipulations → Blessings/Curses → Witnesses
- Detectable in Deuteronomy, Joshua 24
- Effort: 2h

### 5. Tabernacle / Temple Pattern (Margaret Barker)
Creation → Tabernacle → Temple → Christ typology.
Shared keywords: cherubim, veil, mercy seat, holy of holies, lampstand
- Engine already has 75 Barker connections
- Effort: 2h — keyword-based pattern detection

### 6. Numerical Patterns (Extended)
The frequency.py module detects some but could be extended:
- The '7' structure in creation, feasts, seals, trumpets
- The '40' pattern in flood, wilderness, testing
- The '12' pattern in tribes, apostles, months
- Effort: 1h

### 7. Janus Parallelism
A pivot word that reads two ways — backward to the previous line,
forward to the next. Song 2:12 *zamir* = "pruning" + "song".
- Requires Hebrew lexical database with multiple meanings
- Effort: 3h

### 8. Whole-Book Macro-Chiasmus (Section-Level)
The 1 Nephi whole-book chiasm (22 chapters) operates at section level,
not verse level. Current detector max_window=100 is too small.
- Fix: add section-level detection that groups verses into thematic units
  then runs chiasm detection on those units
- Effort: 4h
