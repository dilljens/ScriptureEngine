# Passage-Level Connections — Pericope, Chapter & Book

*Adding macro-structural connection support to ScriptureEngine.*

---

## The Problem

ScriptureEngine has **1.77M connections** — but every single one connects individual verse IDs (`gen.1.1` → `exod.12.2`). There is no way to represent:

- "The Exodus narrative (Exod 1–15) connects to the Isaiah redemption theme (Isa 40–55)"
- "The Sermon on the Mount (Matt 5–7) parallels the Sinai covenant (Exod 19–24)"
- "The book of Revelation draws from Ezekiel 40–48"

Currently, these insights would require hundreds of individual verse-level connections with no way to see the forest for the trees.

**The solution:** A `passage_connections` table that links verse ranges directly, plus aggregation generators that roll up existing verse-level connections into passage-level records, and discovery generators that find macro-structural patterns directly.

---

## Terminology

The most precise term in biblical studies is **pericope-level connections** (a pericope is a self-contained passage unit). More general alternatives:

| Term | Scope | Use |
|------|-------|-----|
| **Pericope-level** | Literary units (3–30 verses) | Passage-to-passage parallelism |
| **Passage-level** | Any verse range | General term for text-block connections |
| **Macro-structural** | Book-level or larger | Chiastic book structures, testament arcs |
| **Section-level** | Chapters or larger sections | Covenant structure matching |

---

## Phase 1: Schema + Aggregation Generators

### 1.1 New Database Table

```sql
CREATE TABLE passage_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_start TEXT NOT NULL,      -- gen.40.1
    source_end TEXT NOT NULL,        -- gen.40.23 (a pericope)
    target_start TEXT NOT NULL,      -- exod.12.1
    target_end TEXT NOT NULL,        -- exod.12.51
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,       -- 0-1: how strong the passage-level connection is
    confidence REAL DEFAULT 0.5,     -- 0-1: how sure we are
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}',      -- JSON: verse_count, overlap_ratio, connection_density
    hermeneutic TEXT DEFAULT NULL,
    quality_version INTEGER DEFAULT 0,
    UNIQUE(source_start, source_end, target_start, target_end, layer, type, subtype)
);

CREATE INDEX idx_pc_source ON passage_connections(source_start, source_end);
CREATE INDEX idx_pc_target ON passage_connections(target_start, target_end);
CREATE INDEX idx_pc_layer ON passage_connections(layer);
CREATE INDEX idx_pc_type ON passage_connections(type);
```

Key design decisions:
- `source_start`/`source_end` instead of `source_verse` — supports ranges of any size
- A single verse is still a valid range: `gen.1.1` → `gen.1.1`
- `metadata` stores aggregation stats: `{"verse_count": 12, "individual_connections": 47, "density": 0.33}`
- Same 11-layer system as verse connections
- Same `discovered_by` authority tracking

### 1.2 New Calibration Types

Add to `TYPE_LR` in `lib/controls/calibration.py`:

```python
# ── Passage-level connections ──
"pericope_parallel": 2.5,         # Systematic passage-level parallel
"section_parallel": 2.0,          # Chapter/section-level structural parallel
"book_thematic": 2.0,             # Thematic connection between books
"quotation_chain": 3.0,           # Quotation traced through intermediate texts
"macro_chiastic": 2.0,            # Book-level chiastic pairing
"narrative_parallel": 2.5,        # Parallel narrative structures across books
"fulfillment_arc": 3.0,           # Law→Gospel or OT→NT arc
"covenant_pattern": 2.5,          # Matched covenant structures
"temple_trajectory": 2.0,         # Temple theme across multiple books
"symbolic_system": 2.0,           # Shared symbolic system across passages
```

### 1.3 Aggregation Generators

These generators scan existing verse-level connections and roll them up into passage-level records.

#### Generator 1: Density Cluster Detector

**File:** `generators/passage/density_cluster.py`

Scans for verse ranges where connection density to another range exceeds a threshold.

```python
def run(conn, book_ids=None) -> int:
    """Find passage pairs with high connection density.
    
    Algorithm:
    1. For each book, slide a window (default 10 verses, step 5)
    2. For each window, count connections to every other book's windows
    3. If density > 0.5 (50% of verses in window A connect to window B),
       create a passage_connection record
    4. Merge adjacent windows with same target into larger passages
    
    Returns count of passage connections created.
    """
```

Parameters:
- Window size: default 10 verses
- Step: default 5 verses (50% overlap)
- Density threshold: default 0.5 (50% of verses in range connect to target range)
- Minimum passage size: 5 verses (ignore small clusters)
- Layers to consider: all (or filter by specific layers)

Output per cluster:
```json
{
  "verse_count": 12,
  "individual_connections": 47,
  "density": 0.33,
  "top_types": ["same_lemma", "direct_quotation"],
  "avg_confidence": 0.72
}
```

#### Generator 2: Chiastic Structure Promoter

**File:** `generators/passage/chiastic_promoter.py`

The `known_chiasms` table already has `start_verse`/`end_verse` for chiastic sections with labeled roles (A, A', B, B', C). This generator:

1. Reads known chiasms from the `known_chiasms` table
2. Creates passage-level connections between paired sections (A↔A', B↔B')
3. Sets type to `macro_chiastic` with subtype matching the chiastic label
4. Stores the chiastic center (C) as metadata

#### Generator 3: Quotation Chain Builder

**File:** `generators/passage/quote_chain.py`

Traces `direct_quotation` connections through intermediate texts:

```
Source (Isa 40:3) → quoted_in → Gospel (Matt 3:3) → quoted_in → later text
```

Creates a passage-level chain record linking the source pericope to the final target, with intermediate steps as metadata:

```json
{
  "chain_length": 3,
  "intermediaries": ["matt.3.3"],
  "chain_types": ["direct_quotation", "allusion"]
}
```

#### Generator 4: Book Coherence Scanner

**File:** `generators/passage/book_coherence.py`

For each book, aggregates all connection data:
- Total connections involving this book
- Top 10 connected books
- Per-layer distribution
- Connection density heatmap (per chapter)
- Most connected chapters within the book

Outputs `book_thematic` passage connections between whole books. These are higher-level (less precise but more navigable).

### 1.4 Passage API Endpoints

**File:** `web/routes/passage.py`

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/passage/{start}-{end}/connections` | All verse-level + passage-level connections involving any verse in the range |
| `GET /api/v1/passage/{start}-{end}/passage-connections` | Only passage-level connections (not individual verses) |
| `GET /api/v1/chapter/{book}/{chapter}/connections` | Chapter-level roll-up with density stats |
| `GET /api/v1/book/{book}/connection-summary` | Book-level stats: totals, top connected books, density heatmap |
| `GET /api/v1/connections/density?book=X&min_density=Y` | Find all passage clusters above a density threshold |

All endpoints return structured JSON with:
- `source_range`, `target_range` — passage boundaries
- `connection_counts` — how many individual verse connections are aggregated
- `density` — what fraction of verses have connections
- `top_types` — most common connection types within this passage pair
- `confidence` — aggregated from underlying connections

**MCP tools** (in `lib/api/passage.py`):

| Tool | Description |
|------|-------------|
| `scripture_passage_connections(start, end)` | Get connections for a verse range |
| `scripture_passage_density(start, end)` | Get density stats for a range |
| `scripture_book_connections(book)` | Get book-level connection summary |

---

## Phase 2: Discovery Generators

These generators find passage-level patterns directly from the text, rather than aggregating from verse-level connections.

### 2.1 Parallel Narrative Detector

**File:** `generators/passage/narrative_parallel.py`

Compares narrative structures between books. Detects patterns like:

```
Genesis 12-50 (Abraham → Isaac → Jacob → Joseph)
  └── Covenant pattern: call → promise → sign → test → blessing
Exodus 1-15 (Moses narrative)
  └── Same covenant pattern: call → promise → sign → test → deliverance
```

Uses the existing narrative structure data (formula markers, structural patterns) and compares sequence patterns.

### 2.2 Macro-Chiasm Detector

**File:** `generators/passage/macro_chiasm.py`

Detects book-level chiastic structures independently of the `known_chiasms` table. Uses:
- Thematic keyword density across book sections
- Parallel phrase detection at chapter scale
- Connection symmetry analysis (if A connects to A' and B to B', a chiasm is plausible)

### 2.3 Covenant Structure Matcher

**File:** `generators/passage/covenant_structure.py`

Passages are classified by covenant type (grant covenant, suzerain-vassal treaty, covenant renewal). Passages sharing the same covenant pattern get linked.

---

## Phase 3: Frontend

### 3.1 Connection Density Heatmap

**File:** `frontend/src/components/ConnectionHeatmap.jsx`

A grid visualization where:
- Rows = chapters of the current book
- Columns = chapters of the connected book
- Cell color = connection density (white = none, dark red = dense)
- Click on a cell → opens the passage-level connection detail

### 3.2 Passage Nodes in KnowledgeGraphView

**File:** update `frontend/src/components/KnowledgeGraphView.jsx`

- Passage-level connections appear as **rectangular nodes** (vs. circular verse nodes)
- Rectangles span the verse range visually
- Edges between passage nodes are labeled with the connection type
- Click on a passage node → expand to show internal verse-level connections

### 3.3 Passage-Level Sidebar in WikiLayout

**File:** update `frontend/src/components/WikiLayout.jsx`

When viewing a chapter, the connection sidebar shows a new section at the top:

```
┌─────────────────────────────┐
│ Passage-Level Connections   │
│                             │
│ This chapter is part of a  │
│ cluster: Isa 40-55 ↔ Exod  │
│ 12 (47 links, 70% density) │
│                             │
│ [Explore] [View heatmap]    │
└─────────────────────────────┘
│ Verse Connections (below)   │
│ ...                         │
```

### 3.4 Book Overview Tab

New tab showing:
- Connection density heatmap (book vs. all other books)
- Top 10 most connected chapters
- Top 5 passage-level connections
- Connection timeline (which chapters connect to which testaments)

---

## File Change Summary

| File | What | Lines |
|------|------|-------|
| `lib/db.py` | `passage_connections` table schema | +30 |
| `lib/controls/calibration.py` | 10 new TYPE_LR entries | +10 |
| `generators/passage/__init__.py` | Generator registry for passage generators | +20 |
| `generators/passage/density_cluster.py` | Density cluster detector | +150 |
| `generators/passage/chiastic_promoter.py` | Chiastic structure promoter | +80 |
| `generators/passage/quote_chain.py` | Quotation chain builder | +100 |
| `generators/passage/book_coherence.py` | Book coherence scanner | +80 |
| `generators/passage/narrative_parallel.py` | Parallel narrative detector (Phase 2) | +120 |
| `generators/passage/macro_chiasm.py` | Macro-chiasm detector (Phase 2) | +100 |
| `generators/passage/covenant_structure.py` | Covenant structure matcher (Phase 2) | +80 |
| `scripts/build_passage_connections.py` | Runner for all passage generators | +50 |
| `lib/api/passage.py` | Passage API + MCP tools | +150 |
| `web/routes/passage.py` | 5 API endpoints | +200 |
| `web/server.py` | Register new routes | +5 |
| `frontend/src/components/ConnectionHeatmap.jsx` | New heatmap component | +200 |
| `frontend/src/components/KnowledgeGraphView.jsx` | Passage node rendering | +100 |
| `frontend/src/components/WikiLayout.jsx` | Passage-level sidebar section | +80 |
| **Total** | | **~1,560 lines** |

---

## Priority

| What | Why |
|------|-----|
| 🔴 Schema + density cluster generator | Core infrastructure — everything else builds on this |
| 🔴 Book coherence scanner | Lowest effort for highest insight — connects whole books instantly |
| 🟠 API endpoints | Makes passage data accessible to MCP and frontend |
| 🟠 Chiastic promoter | Builds on existing data (known_chiasms table) |
| 🟡 Frontend heatmap | Best visualization for exploration |
| 🟡 Narrative parallel detector | Higher effort, domain-specific |
| 🟢 Quotation chain builder | Requires multiple layers of data |
| 🟢 Macro-chiasm detector | Experimental — needs validation |
