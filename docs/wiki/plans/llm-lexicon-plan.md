# Agent-Driven Connection Expansion + Text-Focused Scripture Lexicon

**Status:** Active  
**Date:** 2026-06-17  
**Method:** The agent reads verse texts directly, judges connections using its own reasoning, and writes judgment files. No external API, no cost.

## Overview

Two-track initiative that builds on the existing scripture knowledge engine (1.02M connections, 34 generators, 10 connection layers):

1. **Agent-driven connection expansion** — filling gaps that algorithms cannot reach by reading the text and judging systematically
2. **Text-focused scripture lexicon** — dictionary + thesaurus + wiki, searchable by users

Both share the same data architecture. The agent is the engine that builds them.

## Architecture

```
                   Agent (reads verses directly, judges connections)
                  /                              \
   ┌──────────────────────┐          ┌─────────────────────────┐
   │ Connection Graph     │          │  Text Lexicon            │
   │ (existing + new)     │          │  (existing tables)       │
   │                      │          │                          │
   │ symbolic.lamb ───────┤          │  lexicon.{lemma}          │
   │ allusion.grade ──────┤  shares  │    definition (agent-written)│
   │ thematic.covenant ───┤  data:   │    domain: sacrifice      │
   │ typology.adam_christ ─┤  gematria│    concordance: 50x      │
   │                      │  entities│                          │
   │ discovered_by:       │  verses  │  semantic_domains         │
   │ 'algorithm' / 'ai'   │          │    covenant_terms         │
   │ 'human'              │          │    sacrifice              │
   └──────────────────────┘          │    temple_vocab           │
            │                        │                          │
            │                        │  text_wiki_articles       │
            ▼                        │    Abraham (entity)       │
   ┌──────────────────────┐          │    Covenant (concept)     │
   │    RAM Cache          │          └──────────────────────────┘
   │ (passage_guides,      │◄─────── both feed into API
   │  verse_cache,         │
   │  entity_cache,        │
   │  lexicon_cache)       │
   └────────┬──────────────┘
            ▼
   ┌────────────────────────────────────────────────────────┐
   │              FastAPI Web Server                         │
   │  Existing: /api/v1/verses/{ref}, /api/v1/search, ...   │
   │  New:      /api/v1/lexicon/*, /api/v1/wiki/*           │
   │  UI:       Everything opens as interactive tabs         │
   └────────────────────────────────────────────────────────┘
```

## Guiding Principle: Stick to What the Text Says

Every piece of data must answer: **what does the text itself say?** Not what later interpreters said about it.

### In Scope (Text-Level Facts)

| Category | Examples |
|----------|----------|
| Lexical definitions | Word meaning derived from contextual usage analysis |
| Concordance | Every occurrence of a word in the canon |
| Authorial cross-references | Explicit quotations, clear allusions where the author signals intent |
| Structural markers | Toledot, formula markers, chiastic structures the author used |
| Entity profiles | What the text says about each person, place, concept |
| Word frequency & distribution | Pure data from the text |
| Root families | Shared triconsonantal roots |
| Semantic domains | Words that belong together conceptually |

### Out of Scope (Interpretive Tradition)

| Category | Examples |
|----------|----------|
| Rabbinic midrash | Talmudic connections not signaled in the text |
| Patristic readings | Early church father interpretations |
| Reformation theology | Lutheran/Calvinist interpretive frameworks |
| LDS prophetic interpretations | Modern prophetic readings |
| Textual criticism | Manuscript variants, JST changes |
| Any "this symbolizes X" | Unless the text itself makes the symbol explicit |

**The boundary rule:** If the connection requires a later interpreter to point it out, it's out. If the author signals it in the text itself, it's in.

---

## Part 1: Agent-Driven Connection Expansion (4 Phases)

Each phase follows the same workflow — no API, no cost:

```
1. Query DB for candidates     ─→ SQL query pre-filters candidates
2. Read verse texts            ─→ examine source + target texts using Read tool
3. Use reasoning to judge      ─→ is this connection real? why?
4. Write judgment JSON file    ─→ data/agent_connections/{type}_judgments.json
5. Apply to DB                 ─→ INSERT INTO connections (discovered_by='ai')
6. Verify counts               ─→ check DB counts
```

### Phase 1: Symbolic vs. Literal Classification

**Work:** ~500 verse batches  
**Generator pattern:** Create `generators/classify_symbolic.py`

The `shared_symbols.py` generator already finds every verse mentioning "lamb", "lion", "fire", etc. But it flags every connection with *"AI review needed to classify symbolic vs literal."*

**Agent task:** Read verses mentioning a symbol one batch at a time, classify each occurrence as SYMBOLIC (represents something beyond itself), LITERAL (actual physical entity), or UNCERTAIN.

**Output:** Updates `symbol_occurrences.is_symbolic` and refines connection `confidence`.

### Phase 2: Allusion Spectrum Grading

**Work:** ~1,500 verse pairs  
**Generator pattern:** Create `generators/grade_allusions.py`

The intertextual generator finds shared rare-word clusters and labels them all "intertextual." The agent grades each one on a spectrum:

```
direct_quotation → modified_quotation → allusion → echo → coincidental
```

**Output:** Proper `subtype` assignment; coincidental connections get deprecated.

### Phase 3: Thematic Connection Discovery

**Work:** ~2,000 verse pairs  
**Generator pattern:** Create `generators/discover_themes.py`

The system has algorithmic linguistic/numerical/structural connections but **no systematic thematic connections**. This phase creates entirely new connections between verses sharing a theme with zero word overlap — the agent reads both verses and judges whether they share a theme.

**Curated theme list (first 10, expandable to 50+):**

- covenant
- restoration
- temple_presence
- mountain_of_god
- water_of_life
- exodus_pattern
- wilderness_testing
- new_creation
- judgment_and_mercy
- shepherd_flock

**Output:** New connections with `discovered_by='ai'`, `quality_level='speculative'`, `confidence=0.3-0.5`. Promoted through the existing hit-count + confirmation system.

### Phase 4: Typology Discovery

**Work:** ~200 verse pairs  
**Generator pattern:** Create `generators/discover_typology.py`

Current typology is entirely hand-curated (~25 pairs). The agent proposes new type/antitype pairs, but only where the text itself signals the connection (e.g., "as X, so also Y" patterns or explicit NT re-reading of OT figures).

**Output:** New `typology` table rows + symbolic connections at low confidence (0.3).

---

## Part 2: Text-Focused Scripture Lexicon

Three interconnected resources:

### Dictionary (`lexicon` table)

One entry per unique lemma (11,515 currently in the lexicon table):

| Column | Source | Example |
|--------|--------|---------|
| `lemma` | gematria table | `H7716` |
| `hebrew` | gematria table | `שֶׂה` |
| `transliteration` | algorithmic | `seh` |
| `part_of_speech` | algorithmic from morph | `noun` |
| `root` | algorithmic | `שׂ-ה-ה` |
| `definition` | **agent-written from 20+ verses** | Written from contextual usage |
| `semantic_domain` | algorithmically seeded | `sacrifice` |
| `frequency_total` | algorithmic | 50 |
| `frequency_books` | algorithmic | `{"gen": 5, "exo": 20, ...}` |

### Thesaurus (`semantic_domains` + `domain_members`)

15 domains algorithmically seeded (372 members). The agent can expand by reading domain keywords and assigning additional lemmas.

Seeded domains: sacrifice, temple, covenant, judgment, kingship, warfare, agriculture, wisdom, prophecy, praise, repentance, creation, exile, tribulation, redemption.

### Wiki (`text_wiki_articles`)

**Entity articles** (~87 from `entity_links`): Abraham, Bethel, Moses, Zion, etc.
**Concept articles** (from thematic analysis): Covenant, Temple, Restoration, Exodus Pattern, etc.

Each article: auto-summarized by the agent from all verses mentioning the entity/concept, with occurrence list and cross-references.

---

## Build Order

| Sprint | Deliverable | Method | Status |
|--------|-------------|--------|--------|
| **1** | Lexicon table + algorithmic builder | Algorithmic | ✅ DONE (11,515 entries, 7,853 roots, 50,216 collocations) |
| **2** | Lexicon search API (`/api/v1/lexicon/*`) | Implementation | ✅ DONE (5 endpoints: search, lemma, root, domain, concordance, domains) |
| **3** | Agent-written definitions for all lemmas | Agent reads 20+ verses per lemma, writes definitions | ❌ PENDING |
| **4** | Symbolic vs. literal classification | Agent reads symbol verses, classifies | ❌ PENDING |
| **5** | Semantic domains + thesaurus | Algorithmic seed + agent refinement | ⚠️ PARTIAL (15 domains with 372 members algorithmically; agent expansion pending) |
| **6** | Allusion spectrum grading | Agent reads verse pairs, grades spectrum | ❌ PENDING |
| **7** | Thematic connection discovery (10 themes) | Agent reads verse pairs, judges thematic links | ❌ PENDING |
| **8** | Wiki articles (entities + concepts) + `/api/v1/wiki/*` | Agent reads all verses per entity, writes summary | ❌ PENDING |
| **9** | Typology discovery | Agent reads OT→NT pairs, judges type/antitype | ❌ PENDING |
| **10** | Rebuild passage_guides cache + tab integration | Automated | ✅ DONE |

## Workflow for Agent-Driven Sprints

Each sprint follows the same pattern used for the existing agent connections (`data/agent_connections/`):

```
1. Pre-filter with SQL to get candidates
2. Read verse texts using the Read tool
3. Judge each pair: is this connection real? why?
4. Write judgment to data/agent_connections/{type}_judgments.json
5. Apply to DB
```

No API calls. No cost. The agent's own reading and reasoning is the engine.

## API Endpoints (New)

```
# Lexicon
GET /api/v1/lexicon/search?q=lamb          # Search words + definitions
GET /api/v1/lexicon/lemma/H7716            # Full word entry
GET /api/v1/lexicon/root/שׂ-ה-ה            # All words sharing a root
GET /api/v1/lexicon/domain/sacrifice       # Browse a domain (thesaurus)
GET /api/v1/lexicon/domains                # List all domains

# Wiki
GET /api/v1/wiki/abraham                   # Entity article
GET /api/v1/wiki/covenant                  # Concept article
GET /api/v1/wiki/browse?type=person        # List all people
GET /api/v1/wiki/concordance/H7716         # Raw occurrence list
```

## MCP Protocol Fix

The MCP server (`mcp_server.py`) was updated to support both old (`list_tools`/`call_tool`) and new (`tools/list`/`tools/call`) MCP protocol versions. OpenCode 1.17.7 uses the newer method names and was failing to enumerate tools. The server now dispatches both to the same logic.
