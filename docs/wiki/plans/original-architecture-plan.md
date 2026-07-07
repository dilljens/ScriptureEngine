# Scripture Knowledge Engine — Architecture & Expansion Plan

## Current Architecture Overview

```
                              ┌─────────────────┐
                              │    Database      │
                              │  (SQLite 43MB)   │
                              └────────┬────────┘
                                       │
     ┌─────────┬──────────┬────────────┼────────────┬──────────┬──────────┐
     │         │          │            │            │          │          │
  ┌──▼──┐  ┌──▼──┐  ┌───▼───┐  ┌────▼────┐  ┌───▼───┐  ┌──▼──┐  ┌──▼──┐
  │Verse│  │Gem- │  │Search │  │Pattern  │  │Sectn │  │Word │  │Known│
  │     │  │atria│  │       │  │Detectors│  │Compare│  │Count│  │Pats │
  └──┬──┘  └──┬──┘  └───┬───┘  └────┬────┘  └───┬───┘  └──┬──┘  └──┬──┘
     │         │          │            │            │          │          │
     └─────────┴──────────┴────────────┼────────────┴──────────┴──────────┘
                                       │
                              ┌────────▼────────┐
                              │   AI (DeepSeek  │
                              │   V4 Flash)     │
                              │   Synthesizes   │
                              └─────────────────┘
```

### Data Layer (`lib/db.py`)
- 8 tables: `works`, `books`, `verses`, `gematria`, `divine_names`, `connections`, `word_frequency`, `patterns`, `known_chiasms`, `structural_formulas`
- 42,054 verses, 305,507 gematria entries
- 302 connections (currently all numerical/gematria-based)

### Pattern Detectors (`lib/patterns/`)
- `chiastic.py` — Word-level chiasm detection within single chapters
- `parallelism.py` — 4 types (synonymous, antithetic, synthetic, step)
- `frequency.py` — Word occurrence counting + sacred number analysis
- `giliadi.py` — Giliadi-style word-count mirroring (3 methods)
- `structural.py` — Formula sequence analysis
- `parallelism_hebrew.py` — Hebrew-specific types (cognate accusative, merismus, etc.)

### Tools (`tools/`)
- 15 tool scripts that feed structured data to the AI
- AI interprets results, discovers patterns, and saves findings

### Connection Types (`lib/connections/types.py`)
- 9 layers, ~80 connection types defined
- `LAYERS` dict + `ALL_TYPES` list + validation functions
- Currently only 2 types populated in the DB (`divine_name_value`, `sacred_number`)

---

## Connection Data Flow

Adding connections follows this pipeline:

```
1. DEFINE the type       → lib/connections/types.py  (add type to LAYERS dict)
2. GENERATE connections  → scripts/ or AI discovers  (algorithmic or AI-driven)
3. STORE connections     → lib/db.py:add_connection  (SQLite INSERT)
4. QUERY connections     → lib/db.py:get_connections, get_connections_by_layer
5. DISPLAY connections   → tools/connections.py       (JSON output)
6. SYNTHESIZE            → AI reads tool output, explains to user
```

---

## How to Add a New Connection Type

**Minimal path** (just define + AI generates):

### Step 1: Add the type to the taxonomy

In `lib/connections/types.py`, add a new entry to the `LAYERS` dict:

```python
LAYERS = {
    ...
    "my_new_layer": {
        "name": "My New Layer",
        "description": "Description of what this tracks",
        "types": [
            "my_type_a",
            "my_type_b",
        ]
    },
    # Or add to an existing layer's 'types' list
}
```

### Step 2: Generate connections

Two approaches:

**A) Algorithmic script** (for determinate patterns):
```python
# scripts/compute_my_connections.py
from lib.db import get_db, add_connection
from lib.connections.types import LAYERS

def generate(conn, book_id):
    # Run analysis, produce connections
    for source, target in my_analysis(conn, book_id):
        add_connection(conn, source, target,
                      layer="my_new_layer",
                      type_name="my_type_a",
                      strength=0.7,
                      discovered_by="algorithm")
```

**B) AI discovery** (for semantic/tacit patterns):
The AI calls `pattern_ingest.py` after discovering a connection through analysis.

### Step 3: Query

The existing `connections.py` tool automatically picks up new layer types — no code changes needed for display. The `get_connections_by_layer()` function groups by layer dynamically.

---

## The Expansion Problem

Currently **9 layers defined but only 2 populated** (numerical/gematria). The remaining 7 layers are empty. The challenge is: **each layer needs its own generation strategy**.

| Layer | Populated | Generation Strategy |
|-------|-----------|-------------------|
| Linguistic | ❌ | Hebrew morphology matching (Strong's numbers, roots) |
| Numerical | ✅ (302) | Gematria value matching (algorithmic) |
| Structural | ❌ | Formula sequences, chiastic overlap |
| Intertextual | ❌ | Quotation/allusion detection (AI + keyword overlap) |
| Textual | ❌ | Import from JST/DSS/LXX data sources |
| Geographic | ❌ | Location name matching (gazetteer) |
| Chronological | ❌ | Timeline + genealogy data |
| Interpretive | ❌ | Import from scholarly references |
| Frequency | ❌ | Distribution statistics (partially built in frequency.py) |

---

## Infrastructure for Scaling

### Problem 1: No connection generation pipeline

Currently `build_initial_connections()` in `scripts/ingest.py` only generates 302 numerical connections. There's no unified system for running all generators.

**Solution**: A connection generation runner that discovers and runs all generators:

```python
# scripts/generate_all_connections.py

# Each generator is a module in generators/ that exports:
#   name: str
#   description: str  
#   layers: [str]  # which layers it populates
#   run(conn, progress_callback) -> int  # returns count

GENERATORS = [
    generators.numerical_value_matching,
    generators.structural_formula_mirror,
    generators.intertextual_quotation,
    generators.hebrew_cognate_accusative,
    generators.geographic_location,
    generators.chronological_same_period,
    generators.frequency_distribution,
]
```

Running this once populates all populated layers. Running it again skips existing connections (ON CONFLICT DO UPDATE).

### Problem 2: No pluggable generator interface

Each generator is currently ad-hoc (`build_initial_connections`, `detect_chiasm_in_book`, etc.). There's no standard interface.

**Solution**: A `BaseConnectionGenerator` that each generator extends:

```python
class BaseConnectionGenerator:
    name = ""                  # Unique name
    description = ""           # Human readable
    version = 1                # Increment for regeneration
    batch_size = 100           # For progress reporting
    
    def run(self, conn, book_ids=None) -> int:
        """Generate connections, return count."""
        raise NotImplementedError
    
    def validate(self, conn) -> [str]:
        """Check if preconditions are met (data exists, etc.)."""
        return []
```

### Problem 3: No idempotency or versioning

Adding the same connections twice creates duplicates. There's no way to know which generation pass a connection came from.

**Solution**: Connection metadata already supports this (the `metadata` JSON field), but adding a `generator_version` field would help:

```sql
-- In the connections table or a new tracking table
CREATE TABLE IF NOT EXISTS generator_runs (
    generator_name TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    last_run TEXT NOT NULL,     -- ISO timestamp
    count_generated INTEGER,
    book_ids_processed TEXT      -- JSON array
);
```

### Problem 4: No incremental/selective generation

Currently you can't say "just generate connections for Genesis." The whole DB or nothing.

**Solution**: All generators accept `book_ids=None` (all books) or a list of specific books. When a new book is added, you regenerate its connections.

### Problem 5: No connection quality scoring

All connections have the same weight. A "certain" connection (direct quotation) and a "speculative" connection (possible echo) are indistinguishable.

**Solution**: The existing `strength` and `confidence` fields handle this, but they need consistent calibration across generators. A standard rubric:

| Strength | Meaning |
|----------|---------|
| 1.0 | Certain — textual fact (same verse in two versions) |
| 0.8–0.9 | Strong — scholarly consensus |
| 0.6–0.7 | Moderate — multiple lines of evidence |
| 0.4–0.5 | Suggested — single line of evidence |
| 0.1–0.3 | Speculative — AI-proposed, unverified |

---

## New Connection Generators to Build

### Phase 1: Structural + Intertextual (highest value, most feasible)

**Structural — Chiastic Linking** (`generators/structural_chiasm.py`):
- When a chiasm is detected or known, connect A↔A', B↔B', C↔C' pairs
- Each matched pair gets a `chiastic` connection in the structural layer
- Sources: algorithmic detections + known patterns

**Structural — Inclusio Detection** (`generators/structural_inclusio.py`):
- Scan for repeated phrases at the beginning and end of passages
- Uses the structural formula data already computed
- Connect the opening and closing verses

**Intertextual — Quotation Detection** (`generators/intertextual_quotation.py`):
- Find long common substrings between verses across the canon
- Classify by length: >50% match = direct quotation, 25-50% = modified quotation
- Start with OT↔NT, then extend to BoM↔Bible

**Intertextual — Parallel Phrase Detection** (`generators/intertextual_parallel.py`):
- Use AI to identify parallel phrasing even when words differ
- AI reviews algorithmic candidates and classifies as quotation/allusion/echo

### Phase 2: Linguistic + Geographic (medium effort)

**Linguistic — Same Lemma** (`generators/linguistic_lemma.py`):
- Connect all verses that share a rare Hebrew lemma
- "Rare" = appears fewer than 10 times in the canon
- Skip common words (and, the, etc.)
- Use Strong's numbers from gematria table

**Linguistic — Cognate Accusative** (`generators/linguistic_cognate.py`):
- Uses the existing `parallelism_hebrew.py` detector
- For each cognate accusative found, connect the verse to the root lemma

**Geographic — Location Matching** (`generators/geographic_location.py`):
- Build a location gazetteer from the text (place names)
- Connect all verses mentioning the same location
- Subtype: "wilderness" locations, "temple" locations, etc.

### Phase 3: Chronological + Textual (requires new data)

**Chronological — Same Time Period** (`generators/chronological_period.py`):
- Requires timeline data (event dates, reign lengths)
- Connect events happening in the same era
- Need: external timeline data source

**Textual — JST Connections** (`generators/textual_jst.py`):
- Map Joseph Smith Translation changes to original verses
- Connect JST verse → original verse
- Need: JST data (copyrighted, need to source carefully)

### Phase 4: Mass-scale numerical connections (computationally cheap)

**Numerical — Full Gematria Matching** (`generators/numerical_full.py`):
- Currently only matches divine name values (26, 86, etc.)
- Expand to: match EVERY Hebrew word value against EVERY other
- But: 305,507 words → 46 billion pairs. Need optimization.
- Solution: bucket by value and only connect ^rare^ values (< 100 occurrences)
- Also: connect verse totals that match sacred numbers

---

## Dependency Graph for Generators

```
Layer              Depends On                  Priority
─────────────────────────────────────────────────────────
Numerical          gematria table (done)       DONE (302)
Numerical (full)   gematria table (done)       HIGH
Structural chiastic  known_chiasms (done)      HIGH
Structural inclusio  structural_formulas (done) HIGH
Intertextual       verses table (done)         HIGH
Linguistic         gematria.lemma (done)        MED
Geographic         gazetteer (needs building)   MED
Chronological      timeline data (new source)   LOW
Textual            JST/LXX/DSS data (new src)  LOW
Interpretive       research data (manual)       ONGOING
```

---

## The Generator Registry

The centerpiece of the expansion architecture — a single file that discovers and runs all generators:

```python
# generators/__init__.py
# Generator registry pattern

from . import numerical_value
from . import structural_chiasm
from . import intertextual
from . import linguistic
from . import geographic
from . import chronological
from . import textual
from . import interpretive
from . import frequency

REGISTRY = {
    "numerical": {
        "name": "Numerical Gematria Matching",
        "module": numerical_value,
        "layers": ["numerical"],
        "automatic": True,
    },
    "structural_chiasm": {
        "name": "Chiastic Structure Linking",
        "module": structural_chiasm,
        "layers": ["structural"],
        "automatic": True,
    },
    "intertextual": {
        "name": "Intertextual Quotation Detection", 
        "module": intertextual,
        "layers": ["intertextual"],
        "automatic": False,  # requires AI review
    },
    ...
}

def run_all(conn, book_ids=None, automatic_only=True):
    """Run all generators and return stats."""
    results = {}
    for key, gen in REGISTRY.items():
        if automatic_only and not gen["automatic"]:
            continue
        count = gen["module"].run(conn, book_ids)
        results[key] = count
    return results
```

---

## File Map for Expansion

```
NEW DIRECTORIES:
  generators/               — Connection generators (one per module)
    __init__.py             — Registry + runner
    numerical_value.py      — Expand gematria matching
    numerical_full.py       — Full gematria value network
    structural_chiasm.py    — Chiasm-based verse pairing
    structural_inclusio.py  — Inclusio detection
    intertextual.py         — Quotation/allusion detection
    intertextual_parallel.py— AI-assisted parallel detection
    linguistic_lemma.py     — Same-lemma connections
    geographic.py           — Location matching
    chronological.py        — Timeline connections
    textual.py              — Textual variant connections
    frequency.py            — Distribution-based connections

MODIFIED FILES:
  lib/db.py                 — Generator tracking table
  lib/connections/types.py  — (already extensible, no changes needed)
  scripts/ingest.py         — Add generator run at end
  knowledge/wiki/_index.md  — Update with new generator info
  
NEW SCRIPTS:
  scripts/generate_connections.py  — Run all generators
  scripts/connection_stats.py      — Stats per layer/generator

NO CHANGES NEEDED FOR:
  lib/connections/graph.py — Already layer-agnostic
  tools/connections.py     — Already layer-agnostic
  tools/known_patterns.py  — Already works
  tools/pattern_ingest.py  — Already works
```

---

## Key Design Principle: Scattered Code, Centralized Registry

Each connection generator lives in its own module (`generators/foo.py`). The registry in `generators/__init__.py` is the only place that knows about all of them. Adding a new generator means:

1. Create `generators/new_type.py`
2. Add one entry to `generators/__init__.py`
3. Run `scripts/generate_connections.py`

That's it. No other files need to change. The type definition in `lib/connections/types.py` is optional — if the generator uses an existing type, nothing changes. Only if you're adding an entirely new layer do you also update `types.py`.

---

## Current State vs. Target

| Metric | Current | Target (Phase 1) | Target (Full) |
|--------|---------|-------------------|---------------|
| Populated layers | 1 of 9 | 5 of 9 | 9 of 9 |
| Total connections | 302 | 10,000+ | 100,000+ |
| Verse coverage | ~0.7% | 25% | 60%+ |
| Generators | 0 (ad-hoc) | 5 | 10 |
| Connection types used | 2 | 25 | 80 |

---

## UI Architecture — The Scripture Browser

### Vision

A web application that lets you explore scripture with **all connection layers visible and interactive**. The text is the primary interface — connections manifest as visual formatting on the text itself.

### Two-Layer Tab Navigation

```
┌──────────────────────────────────────────────────────────────────┐
│  [Topic Tabs — Layer 1]                                          │
│  ┌────────┬────────┬────────┬────────┬────────┬────────┬────────┐│
│  │ Torah  │Prophets│Writings│Gospels │ Last   │  Flood │Temple  ││
│  │        │        │        │        │ Days   │        │        ││
│  └────────┴────────┴────────┴────────┴────────┴────────┴────────┘│
│  ┌──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐│
│  │ Gen  │ Exo  │ Lev  │ Num  │ Deut │      │      │      │      ││
│  └──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘│
│           [Subtopic Tabs — Layer 2]                               │
├──────────────────────────────────────────────────────────────────┤
│  [Verse display area — connections visible as formatting]         │
│                                                                    │
│  בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ│
│                                                                    │
│  In the beginning God created the heaven and the earth.           │
│                                                                    │
│  [Connection highlights active on this verse]                     │
│  ┌──────────────────────────────────────────────────┐             │
│  │ 🔗 Gematria: 2701 (7 words, 28 letters)          │             │
│  │ 🔗 Divine name: Elohim = 86                     │             │
│  │ 🔗 John 1:1 — direct quotation                   │             │
│  └──────────────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────────────┘
```

**Layer 1 tabs** are high-level topics:
- Canonical divisions: Torah, Prophets, Writings, Gospels, Epistles, etc.
- Theological themes: Last Days, Flood, Temple, Covenant, Creation, etc.
- Each tab loads a set of scriptures and subtopic tabs

**Layer 2 tabs** are the sub-groupings within a topic:
- Under "Torah": Genesis, Exodus, Leviticus, Numbers, Deuteronomy
- Under "Last Days": Olivet Discourse, Revelation, Daniel, D&C prophecies
- Under "Flood": Genesis 6-9, Moses 7, 3 Nephi parallels
- These tabs switch the main content view

### Topic Management (User-Creatable Collections)

Users define topics that group related scriptures across the canon:

```sql
-- Already added to DB schema:
-- topics, topic_verses tables

-- Example: "Flood Related"
topic: "Flood Related"
  subtopics:
    - "Noah's Flood" → Gen 6:9–9:29, Moses 7:32–43, 1 Ne 19:10
    - "Flood Typology" → 1 Pet 3:18–22, 2 Pet 2:5, Heb 11:7
    - "Baptism as Flood" → Rom 6:3–5, Col 2:12, D&C 76:51–52

-- Example: "Last Days"
topic: "Last Days"
  subtopics:
    - "Olivet Discourse" → Matt 24, Mark 13, Luke 21
    - "Book of Revelation" → Rev 1–22
    - "D&C End-time" → D&C 29, D&C 43, D&C 45, D&C 101
    - "Isaiah Apocalyptic" → Isa 24–27, Isa 66
    - "BoM End-time" → 1 Ne 14, 2 Ne 28–30, 3 Ne 26–29
```

The AI (DeepSeek V4 Flash) helps build these topics — you say "create a topic for flood-related scriptures" and it queries the connections database to find relevant verses, suggests groupings, and populates the `topics` and `topic_verses` tables.

### Connection Layer Visibility Toggles

A collapsible control panel lets you toggle which connection layers are visible:

```
┌──────────────────────────────────────┐
│ 🔍 Connections                      │
│                                      │
│ ☑ Linguistic (12)         👁️ [on]  │
│ ☑ Numerical (302)         👁️ [on]  │
│ ☐ Structural (8)          👁️ [off] │
│ ☑ Intertextual (45)       👁️ [on]  │
│ ☐ Textual (0)             👁️ [off] │
│ ☐ Geographic (0)          👁️ [off] │
│ ☐ Chronological (0)       👁️ [off] │
│ ☐ Interpretive (0)        👁️ [off] │
│ ☐ Frequency (0)           👁️ [off] │
│                                      │
│ Show: [All ▲] [Strong only] [Custom]│
│                                      │
│ Strength filter: ═══●═══ 0.55       │
└──────────────────────────────────────┘
```

When a layer is toggled ON:
- Its connections become visually highlighted on the text
- The sidebar shows the active connections for the current verse
- Text formatting adapts (see below)

When a layer is toggled OFF:
- Its connections are hidden from the display
- The text returns to its default formatting

Additionally, per-layer toggles for **subtypes** (e.g., within Intertextual: show quotations but hide echoes):

```
☑ Intertextual
   ☑ direct_quotation
   ☑ modified_quotation
   ☑ allusion
   ☐ echo
   ☑ type_antitype
```

### Chiastic Formatting — Text Rendered as Chiasm

When the **Structural** layer is enabled and a verse has chiastic connections, the text reformats to show the mirror structure:

```
Default view:
  And God said, Let there be light: and there was light.

Chiasm view (with Structural layer ON):
  ┌── A ── And God said,
  │  ┌─ B ── Let there be light:
  │  └─ B'── and there was light.
  └── A'── (And God saw the light, that it was good)

For multi-verse chiasms (e.g., Flood narrative):
  ┌ A  Gen 6:9-12  ── Corruption and violence
  │  ┌ B  6:13-22  ── Build the ark
  │  │  ┌ C  7:1-24  ── Enter the flood
  │  │  │  └ D  8:1  ── GOD REMEMBERS NOAH (pivot)
  │  │  └ C' 8:2-14  ── Waters recede
  │  └ B' 8:15-22  ── Exit the ark
  └ A' 9:1-29  ── Covenant established
```

The formatting uses indentation + connector lines + letter labels (A/A', B/B') to show the mirror pairing. The user can click any pair to see the specific mirrored words highlighted.

Implementation approach for chiasm formatting:
```
text_chiasm.py — utility module that takes a chiasm definition
(layers with verse ranges) and returns a formatted string with:
- Proper indentation for each nesting level
- Connector characters (┌ ┐ └ ┘ │ ─) for the structure
- Color/weight coding for mirror pairs (A=red, B=blue, C=green, etc.)
- Clickable verse references that scroll to the location
```

### Poetic Formatting for Isaiah and Hebrew Poetry

When the **Structural** layer is enabled, Hebrew poetic text reformats to show its parallelistic structure:

```
Default view:
  The grass withereth, the flower fadeth: but the word of our God shall stand for ever.

Parallelism view (with Structural layer ON):
  The grass withereth, the flower fadeth:          │ synonymous
  but the word of our God shall stand for ever.     │ antithetic

For full poetic passages like Psalm 1 or Isaiah 40:
  ┌────────────────────────────────────────────┬──────────────┐
  │ Comfort ye, comfort ye my people,          │              │
  │           saith your God.                  │ synonymous   │
  │ Speak ye comfortably to Jerusalem,         │              │
  │           and cry unto her,                │ synonymous   │
  │ That her warfare is accomplished,          │              │
  │           that her iniquity is pardoned:   │ antithetic   │
  │ For she hath received of the Lord's hand   │              │
  │           double for all her sins.         │ synthetic    │
  └────────────────────────────────────────────┴──────────────┘
```

The format includes:
- **Stanza breaks** (blank line between thought units)
- **Parallelism type label** in the right margin (synonymous/antithetic/synthetic)
- **Indented second lines** for Hebrew poetic bicolon structure
- **Color pairing** for matched elements across lines
- **Detection**: uses existing `lib/patterns/parallelism.py` detectors

### Visual Marking of Active Connections

When connection layers are enabled, specific words/phrases in the text get visual indicators:

```
┌──────────────────────────────────────────────────────────┐
│  In the BEGINNING God created the HEAVEN and the EARTH.  │
│        └──┬──┘                           └──┬──┘         │
│      John 1:1                            Gen 21:33       │
│      "In the beginning was the Word"      "everlasting   │
│                                           God"           │
│                                                           │
│  [hover or click a marked word → tooltip shows all       │
│   connections anchored at that word/verse]                │
└──────────────────────────────────────────────────────────┘
```

Marking behavior:
- **Underline color** = connection layer (blue=intertextual, green=numerical, etc.)
- **Underline style** = connection type (solid=quotation, dashed=allusion, dotted=echo)
- **Hover** shows a tooltip with the connection details
- **Click** opens the connected verse in a split-pane
- **Double-click** follows the connection path (hops through the graph)

The `ui_preferences` table stores which layers/types are active so the state persists across sessions.

### UI Tech Stack (Future)

```
Frontend:    React + TypeScript
State:       Zustand (lightweight, stores layer toggles + active verse)
Text engine: Custom React component that processes verse text
             and applies connection-aware formatting
Backend:     FastAPI (same SQLite DB)
Topics API:  CRUD for topics, topic_verses, subtopics
Connections: Already built in tools/ + lib/
Formatting:  text_chiasm.py, text_parallelism.py utility modules
```

### Summary: What Gets Built

| Feature | DB Table | UI Component | Depends On |
|---------|----------|-------------|------------|
| Topic tabs | `topics`, `topic_verses` | TopicNav (two-layer) | topic data populated |
| Subtopic grouping | `topics.parent_id` | SubtopicBar | topics exist |
| Layer visibility toggles | `ui_preferences` | LayerPanel | connections exist |
| Chiastic formatting | connections(layer=structural) | ChiasmRenderer | structural layer |
| Poetic formatting | patterns(parallelism) | ParallelismRenderer | parallelism detected |
| Word-level marking | connections(any layer) | VerseHighlighter | connections exist |
| Strength filtering | connections.strength | StrengthSlider | connections exist |
| Persistent prefs | `ui_preferences` | auto-save | prefs table exists |
| Custom tabs | `custom_tabs`, `tab_content` | TabCreator | — |
| Guided AI studies | `study_guides`, `study_guide_steps` | StudyGuidePlayer | connection graph populated |

---

## Custom User-Created Tabs

Users can create their own **top-level tabs** with arbitrary **subtab groupings** beneath them.

### How Custom Tabs Work

```
┌─ Tab Bar ─────────────────────────────────────────────────────┐
│ [Torah] [Prophets] [Last Days] [My Study] [+] ← create tab  │
│                                     ┌───────┐                 │
│                                     │New Tab│                 │
│                                     │Name:  │                 │
│                                     │[Angel of the Lord]     │
│                                     │Icon:  │[👼]             │
│                                     │[Create]                │
│                                     └───────┘                 │
├─ Subtabs ─────────────────────────────────────────────────────┤
│ [Gen 16:7] [Gen 22:11] [Ex 3:2] [Josh 5:13] [+] ← add sub  │
│                                                                │
│ (Then the user adds verses or study guides to each subtab)    │
└────────────────────────────────────────────────────────────────┘
```

**User flow:**
1. Click "+" → name the tab → creates a top-level `custom_tabs` entry with `parent_id=NULL`
2. Click "+" within that tab → name a subtab → creates a child `custom_tabs` entry with `parent_id` set
3. Add content to subtabs — either individual verses, search queries, or linked study guides
4. The tab tree is stored in `custom_tabs` + `tab_content` and persists across sessions

**AI-assisted creation:**
- User says "create a tab for everything about the flood"
- AI calls `create_custom_tab` for the parent, then `add_tab_content` for each verse range
- Result: a "Flood" tab with subtabs "Genesis 6-9", "Moses 7", "3 Nephi Flood parallels"
- The AI can also suggest subtabs and populate them from the connection graph

---

## AI-Guided Topics (Graph Exploration)

The most powerful feature: **an AI leads the user through a chain of connections** through the scripture connection graph.

### How Guided Studies Work

```
┌─ Study Guide: "The Angel of the Lord" ───────────────────────┐
│                                                               │
│  Step 1 of 7 ◉══════════○═════○═════○═════○═══○═══○          │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Gen 16:7                                                │   │
│  │ And the angel of the LORD found her by a fountain of   │   │
│  │ water in the wilderness...                             │   │
│  ├────────────────────────────────────────────────────────┤   │
│  │ 💡 The Angel of the Lord (Malach YHWH) appears here   │   │
│  │ for the first time. Notice the Angel speaks as God     │   │
│  │ ("I will multiply thy seed"). This is a theophany —    │   │
│  │ a visible manifestation of God himself.               │   │
│  │                                                        │   │
│  │ 🔗 Connection: This is the first "angel of the Lord"   │   │
│  │   appearance. The same figure appears next when...     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  Where to go next:                                            │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ● Gen 22:11 — Angel stops Abraham from sacrificing   │    │
│  │   Isaac — the Angel speaks as God again              │    │
│  │ ○ Ex 3:2 — Angel appears in the burning bush —       │    │
│  │   identified as YHWH                                  │    │
│  │ ○ Josh 5:13 — Captain of the Lord's host — Joshua    │    │
│  │   worships him                                        │    │
│  │ ○ Judg 6:11 — Angel appears to Gideon — "The Lord    │    │
│  │   is with thee"                                       │    │
│  │ ○ Branch off → Create a new study from here           │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

**AI generates the study path:**

1. **Seed**: Start from a seed verse (e.g., "gen.16.7" — first Angel of the Lord appearance)
2. **Explore**: Query the connection graph — `find_all_paths(seed, max_depth=3)` finds all reachable verses through any connection layer
3. **Select**: AI selects the most interesting/thematically relevant path (e.g., "all verses where `connection_type = 'angel_of_the_lord_appearance'` or matching the theme through semantic understanding)
4. **Explain**: For each step, the AI generates an explanation — what's happening, what the connection is, why it matters
5. **Branch**: At each step, the AI suggests 2-5 possible next moves — the user chooses their path
6. **Save**: The path is saved as a `study_guide` with `study_guide_steps`, preserving the user's choices

### Under the Hood: How the AI Finds the Path

The AI (DeepSeek V4 Flash) uses the `guided_study.py` tool:

```python
# Step 1: AI creates the guide
guide_id = tool_create_guide(
    title="The Angel of the Lord",
    seed="gen.16.7",
    theme="angel_of_the_lord"
)

# Step 2: AI explores the connection graph from the seed
paths = tool_suggest_path(seed="gen.16.7", theme="angel_of_the_lord")
# Returns: direct connections from Gen 16:7, deeper paths up to 2 hops

# Step 3: AI selects the most interesting path
# The AI reads the connection types, destination verses, etc.
# and selects a coherent thematic path

# Step 4: AI adds each step with explanation
for i, verse in enumerate(selected_path):
    tool_add_step(
        guide_id=guide_id,
        step_number=i+1,
        verse=verse,
        title=ai_generated_title,
        explanation=ai_generated_explanation,
        choices=next_steps,  # from suggest_path
    )

# Step 5: AI creates a custom tab linked to the guide
tool_build_tab(guide_id=guide_id, tab_name="Angel of the Lord")
```

### Example Guided Studies the AI Could Build

| Theme | Seed Verse | Exploration Path |
|-------|-----------|-----------------|
| **Angel of the Lord** | Gen 16:7 | Gen 22:11 → Ex 3:2 → Josh 5:13 → Judg 6:11 → Judg 13:3 → 1 Kgs 19:5 → Zech 1:11 |
| **Zodiac / Mazzaroth** | Job 38:31-32 | Gen 1:14 → Ps 19 → Ps 147:4 → Isa 40:26 → Amos 5:8 → D&C 88:45-47 |
| **Covenant** | Gen 9:8-17 | Gen 15:18 → Gen 17 → Ex 19-24 → 2 Sam 7 → Jer 31:31 → D&C 84 → Rev 21 |
| **Temple** | Ex 25:8-9 | 1 Kgs 5-8 → Ezek 40-48 → John 2:19-21 → 1 Cor 3:16 → Rev 21:22 |
| **Restoration** | Acts 3:19-21 | D&C 1 → D&C 110 → D&C 128:18-21 → JS-H 1 → Mal 4:5-6 |

### Data Flow

```
User: "Create a guided study about the zodiac in scripture"
        │
        ▼
AI (DeepSeek V4 Flash)
        │
        ├── 1. Create the study guide via guided_study.py
        │
        ├── 2. Analyze theme → determine seed verses
        │     "Job 38:31-32 is the key zodiac passage:
        │      Canst thou bind the sweet influences of Pleiades?
        │      Canst thou loose the bands of Orion?"
        │
        ├── 3. Query connections from each seed verse
        │     → calls suggest_path(seed) for each seed
        │     → reads connection graph data
        │     → applies semantic understanding of theme
        │
        ├── 4. Build the path — select verses, write explanations
        │     → calls add_step for each verse
        │     → explains each connection
        │
        ├── 5. Create a custom tab linked to the guide
        │     → calls build_tab
        │
        └── 6. Present to user:
              "I've created a guided study on the zodiac in scripture.
               Start at Job 38:31-32 where God challenges Job with the
               constellations. Then follow the thread through..."
```

### Database Integration

The `study_guides` and `study_guide_steps` tables store the entire exploration path. The `custom_tabs` table links guides to the UI. The `tab_content` table connects tabs to their content (be it verses, queries, or study guides).

This means:
- **The user can return to a study later** — steps and choices are persisted
- **Studies can be shared** — `is_public` flag enables community studies
- **The AI can resume a study** — picks up where the user left off
- **Multiple branches** — the `choices_json` field stores branching points for later exploration

---

## Core Design Principle: Stick to Truth

The engine must ALWAYS distinguish between what the text actually says and later interpretive traditions. This is fundamental to the project's integrity.

### The Principle

| Category | What It Is | How It's Labeled |
|----------|-----------|-----------------|
| **Text** | The actual words of scripture (Hebrew, Greek, English) | `linguistic`, `textual` layers |
| **Historical context** | What the text meant in its original setting | `chronological` layer |
| **Interpretive tradition** | How later readers understood the text | `interpretive` layer |
| **Human additions** | Traditions added that may obscure the text | Must be explicitly flagged |

### How This Applies

**When Jesus and the Pharisees disagreed**, the system should note: Jesus was restoring the original intent of Torah against added traditions. He quotes Torah itself ("Have ye not read?") to correct their misinterpretations. This is not Jesus vs. Torah — it is Jesus vs. human additions to Torah.

**When Paul discusses the law**, the system should distinguish between:
- Paul opposing self-justification through law-works (human addition)
- Paul affirming the law as holy, just, and good (the text itself)
- The covenant relationship Torah was always meant to establish

**In guided studies** (like "Torah in All Scripture"), each step should note whether a connection comes from:
- What the text actually says (`linguistic`/`textual`/`structural`)
- What interpretive tradition claims it means (`interpretive`)

### Database Implementation

The `connections` table's `layer` field already supports this:
```python
# Text-based connection
add_connection(layer="linguistic", type="same_lemma", ...)

# Interpretive tradition  
add_connection(layer="interpretive", type="rabbinic_midrash", ...)

# Human addition flagged
add_connection(layer="interpretive", type="tradition_added", 
               strength=0.3, # Lower = more speculative
               confidence=0.4)
```

The `study_guide_steps` table's `connection_layer` field also tracks this per step.
The AI (DeepSeek V4 Flash) applies semantic understanding to make the distinction.
