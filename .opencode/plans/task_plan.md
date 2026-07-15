# Scripture Engine Upgrade — Multi-Track Plan

Goal: Make the database more powerful for LLMs (DeepSeek V4 Flash) with enhanced MCP tools, and for humans with Wikipedia-style browsing in the existing React app.

## Pre-resolved Decisions
- Wiki is a layout toggle on the existing ChapterView, not a separate site
- No Obsidian vault (deferred for future user notes feature)
- No local AI — DeepSeek V4 Flash for everything
- Keep SQLite + recursive CTEs — no Neo4j/Kuzu migration
- Enhanced MCP tools are the LLM interface (study_verse, compare, research, graph_context, entity_deep)
- Docs need updating — current numbers are stale (56 tools, 69 endpoints, 11 layers, 1.3M+ connections)

---

## Track A: Document Audit `[x]`

Update all stale documentation to reflect actual project state.

⏱ Timebox: 2.5hrs total

### Phase A1: Stats Verification Script `[x]`
- [x] Create `scripts/project_stats.py` that queries the live DB and prints:
  - Total connections (count), unique source verses
  - Layers + counts per layer
  - Connection types + subtypes counts
  - Total verses by work
  - Entities, gematria entries, passage guides
  - Quality distribution
- [x] Run the script and capture output for doc updates — 1,028,083 connections, 11 layers, 131 types, 42,054 verses, 8 works, 56 tools, 102 endpoints
- ✅ Checkpoint: `python3 scripts/project_stats.py` produces structured output — PASS
- ⚙ Fallback: If DB is not available locally, use CHAT_AGENTS.md numbers and note they're approximate

### Phase A2: README Rewrite `[x]`
- [ ] Rewrite `README.md` with accurate stats:
  - Connection count: 1.3M+ (or exact from Phase A1)
  - Layers: 11
  - MCP tools: 56
  - HTTP endpoints: 69
  - Works: 8 (add DSS, Apocrypha, Pseudepigrapha that are missing)
  - Add connection layer table
- [ ] Update the Architecture diagram
- [ ] Update Features list
- ✅ Checkpoint: README numbers match project_stats.py output
- ⚙ Fallback: Use CHAT_AGENTS.md numbers if DB unavailable

### Phase A3: CHAT_AGENTS.md Update `[ ]`
- [ ] Verify all 56 registered MCP tools are listed
- [ ] Add missing tools with descriptions
- [ ] Ensure tool naming is consistent (`scripture_` prefix)
- ✅ Checkpoint: `grep -c "scripture_" CHAT_AGENTS.md` matches tool count
- ⚙ Fallback: Focus on tool list accuracy

### Phase A4: Server Docstring Fix `[x]`
- [x] Fix `web/server.py` docstring ("826K connections" → actual)
- [x] Update `knowledge/wiki/_index.md` stats
- [x] Update `knowledge/wiki/_standards.md` for 11 layers
- ✅ Checkpoint: No stale number references in docstrings — PASS

---

## Track B: Wiki Browsing Mode (React Frontend) `[x]`

Build a Wikipedia-style layout toggle on the existing ChapterView — two-column layout, connection sidebar, entity infobox, layer badges, quality stars.

⏱ Timebox: 9hrs total

### Phase B1: WikiLayout Component `[x]`
- [x] Create `frontend/src/components/WikiLayout.jsx` — a new component that takes the same chapter data as ChapterView but renders it Wikipedia-style:
  - Two-column grid layout (verse text left, connection sidebar right)
  - Breadcrumb: `Work → Book → Chapter`
  - Book infobox at top (work, chapter count, verse count, stats)
  - Connection sidebar: grouped by layer, expandable/collapsible per layer
  - Entity sidebar: people/places/concepts mentioned in the chapter
  - Inline connection links rendered between verse lines
  - Quality stars (★☆☆☆☆ – ★★★★★) on each connection
  - Layer badges (colored pills: Linguistic, Numerical, Intertextual, etc.)
  - Responsive: sidebar collapses on mobile
- ✅ Checkpoint: `WikiLayout` renders Genesis 1 with two-column layout and connection sidebar
- ⚙ Fallback: Ship with simpler single-column layout first, add sidebar features iteratively

### Phase B2: Mode Toggle `[x]`
- [x] Add a "Simple ↔ Wiki" toggle button to the ChapterView toolbar
- [x] Default stays in Simple mode
- [x] Toggle persists in localStorage (`scriptureengine.wikiMode`)
- [x] Both modes use the same API data — just different renderers
- ✅ Checkpoint: Toggle between Simple and Wiki modes on the same chapter without data reload — PASS
- ⚙ Fallback: Query parameter toggle if localStorage is complex

### Phase B3: Graph Panel in Wiki Mode `[x]`
- [ ] Add an expandable graph panel in the Wiki layout
- [ ] Shows the local connection graph for the current chapter/verse
- [ ] Reuses existing Cytoscape.js integration
- [ ] Panel is collapsible (default: collapsed)
- ✅ Checkpoint: Expand graph panel in Wiki mode, see chapter-level connection graph
- ⚙ Fallback: Link to existing ConnectionGraph component instead

### Phase B4: Browse-by-Layer View `[x]`
- [ ] Add "Browse Layers" subsection in Wiki mode
- [ ] Pick a layer tab (linguistic, numerical, etc.)
- [ ] See all connections of that type in the current chapter, organized by type
- [ ] Each connection links to the related verse (can click to navigate)
- ✅ Checkpoint: Clicking "numerical" shows all gematria connections for the current chapter
- ⚙ Fallback: Single-level list without nested type grouping

---

## Track C: Enhanced MCP Tools for DeepSeek `[x]`

Give the LLM everything it needs in one call. New tools that replace multiple chained calls.

⏱ Timebox: 11hrs total

### Phase C1: `scripture_study_verse` `[ ]`
- [ ] Add tool to `lib/api/verse.py` that returns a complete verse study package:
  - Verse text in all available languages
  - All connections (sorted by PaRDeS level, with quality stars and stars visual)
  - Gematria values for all Hebrew words
  - All entities (people, places, concepts)
  - Quality assessment (5-star calibration)
  - Scholar provenance
  - 1-hop reachable verses with texts
- [ ] Register in `lib/api/__init__.py`
- [ ] Replaces: scripture_verse + scripture_connections + scripture_gematria + scripture_graph_entities + scripture_sources + scripture_graph_reachable
- ✅ Checkpoint: `call_tool("scripture_study_verse", conn, verse="gen.1.1")` returns a complete profile in one response
- ⚙ Fallback: Start with connections + gematria, add entities/sources iteratively

### Phase C2: `scripture_compare` `[ ]`
- [ ] Add tool to `lib/api/connections.py` that compares two verses:
  - Shortest connection path between them
  - Shared entities
  - Overlapping connection types
  - Side-by-side text comparison
  - PaRDeS level summary for both
- [ ] Register in `lib/api/__init__.py`
- ✅ Checkpoint: `scripture_compare("gen.1.1", "john.1.1")` returns path, shared entities, and text comparison
- ⚙ Fallback: Compare connections list and entities only, skip path finding

### Phase C3: `scripture_research` `[ ]`
- [ ] Add multi-hop server-side research tool in `lib/api/connections.py`:
  - Accept theme/topic + seed verse + max depth + layer filter
  - Walk the connection graph following relevant layers
  - Collect connected verses with texts and connection metadata
  - Deduplicate and rank by relevance
  - Return structured "research brief" with all findings
- [ ] Register in `lib/api/__init__.py`
- ✅ Checkpoint: `scripture_research("Covenant", "gen.12.1", max_depth=3)` returns verses across OT+NT connected to covenant theology
- ⚙ Fallback: Single-hop only (depth=1), add multi-hop iteratively

### Phase C4: `scripture_graph_context` `[ ]`
- [ ] Add tool to `lib/api/graph.py` that returns N-hop neighborhood as structured LLM context:
  - Verse text
  - N-hop neighborhood with typed relationships explicitly labeled
  - Formatted as structured text (not JSON — LLMs read structured text better)
- [ ] Register in `lib/api/__init__.py`
- ✅ Checkpoint: Tool returns a structured context window the LLM can reason over directly
- ⚙ Fallback: Return JSON with rich text formatting instructions

### Phase C5: `scripture_entity_deep` `[ ]`
- [ ] Add tool to `lib/api/graph.py` for entity deep dive:
  - Entity metadata (Hebrew/Greek names, Strong's numbers)
  - All verses where entity appears (with text)
  - All connections involving the entity across the graph
  - Other entities connected to it (relationship network)
- [ ] Register in `lib/api/__init__.py`
- ✅ Checkpoint: `scripture_entity_deep("Melchizedek")` returns all verses, connections, and related entities
- ⚙ Fallback: Return verses + connections without related entity graph

### Phase C6: Tool Naming Audit `[ ]`
- [ ] Review all 56 tool names for consistency
- [ ] Rename conversation_* tools to scripture_conversation_* prefix
- [ ] Ensure all tools have clear descriptions for LLM autocomplete
- [ ] Update CHAT_AGENTS.md with final tool list
- ✅ Checkpoint: All 56 tools follow `scripture_` prefix pattern
- ⚙ Fallback: Add aliases instead of breaking renames

---

## Track D: Advanced Graph Visualization `[x]`

**ARCHIVED.** Not needed — the existing wiki layout (connection sidebar, browse-by-layer, collapsible graph panel) already serves connection exploration better than a force-directed graph would. The Cytoscape.js panel in wiki mode handles the local graph view. (Decision made 2026-07-15.)

---

## Track E: Structured Data & Interop `[ ]`

Export the graph for external consumption via JSON-LD and GraphQL.

⏱ Timebox: 5hrs total

### Phase E1: JSON-LD Export `[ ]`
- [ ] Write `generators/export_jsonld.py`
- [ ] Map connection graph to schema.org/Bible types
- [ ] Include `schema:Quotation`, `schema:CrossReference`, etc.
- [ ] Export as downloadable `.jsonld` file
- ✅ Checkpoint: Generated JSON-LD validates against schema.org/Bible schema
- ⚙ Fallback: Export as plain JSON with semantic labels

### Phase E2: GraphQL Endpoint `[ ]`
- [ ] Add `strawberry-graphql` or `ariadne` to FastAPI
- [ ] Schema: `Query { verse(ref) { text connections { type target quality } } }`
- [ ] Schema: `Query { entity(name) { verses connections } }`
- [ ] Schema: `Query { search(query, layer) { results } }`
- ✅ Checkpoint: `query { verse(ref: "gen.1.1") { text connections { type } } }` returns data
- ⚙ Fallback: GraphQL with limited schema (verse + connections only)

---

## Track Dependencies

```
Track A (Docs) ─── no deps, start first for accuracy
    ↓
Track B (Wiki UI) ── independent of other tracks
Track C (MCP Tools) ── independent, can start immediately
Track D (Viz) ─── independent
Track E (Interop) ─── independent
```

All tracks can run in parallel. A should start first so subsequent work references correct numbers.

## Acceptance Criteria

The project is complete when:
1. [ ] `README.md`, `CHAT_AGENTS.md`, and all docs reflect actual project state (56 tools, 69 endpoints, 11 layers, 1.3M+ connections, 8 works)
2. [ ] ChapterView has a "Simple ↔ Wiki" toggle that shows a Wikipedia-style two-column layout with connection sidebar, entity infobox, layer badges, and quality stars
3. [ ] `scripture_study_verse` returns a complete verse profile in one MCP call (text + connections + gematria + entities + quality + sources)
4. [ ] `scripture_compare` compares two verses and returns path, shared entities, and connection overlap in one call
5. [ ] `scripture_research` walks the connection graph multi-hop and returns a structured research brief
6. [ ] `scripture_graph_context` returns a structured N-hop neighborhood formatted for LLM consumption
7. [ ] `scripture_entity_deep` returns all verses, connections, and related entities for any entity in one call
8. [ ] Graph renders 10K+ edges at 60fps in the browser
9. [ ] GraphQL endpoint serves verse, connection, and search queries
10. [ ] JSON-LD export produces valid schema.org/Bible output
