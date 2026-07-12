# Scripture Knowledge Engine

Project-level instructions for the scripture knowledge base at `/home/dillon/_code/scriptureengine/`.

This file activates when you're working in this directory. You have access to the scripture tools and database.
Coding-specific instructions are in the global AGENTS.md and do NOT apply here.

## Available Tools

Run tools as Python scripts with JSON arguments:

```bash
# Core lookups
python3 tools/verse.py '{"book": "gen", "chapter": 1, "verse": 1}'
python3 tools/gematria.py '{"word": "יהוה"}'
python3 tools/gematria.py '{"verse": "gen.1.1"}'
python3 tools/search.py '{"query": "covenant"}'
python3 tools/compare.py '{"verse_a": "gen.1.1", "verse_b": "john.1.1"}'

# Patterns
python3 tools/patterns.py '{"book": "isa", "chapter": 6}'
python3 tools/frequency.py '{"word": "covenant"}'

# Connections
python3 tools/connections.py '{"verse": "gen.1.1"}'
python3 tools/intertext.py '{"verse": "isa.6.1"}'

# Chiastic detection (multi-chapter)
python3 tools/word_counts.py '{"book": "gen", "mode": "per_chapter"}'
python3 tools/chiasm_scan.py '{"book": "gen"}'
python3 tools/section_compare.py '{"section_a": {"start":"gen.6.9","end":"gen.8.14"}, "section_b": {"start":"gen.8.15","end":"gen.9.29"}}'
python3 tools/structural_formulas.py '{"book": "gen"}'
python3 tools/keyword_distribution.py '{"book": "gen", "terms": ["יהוה", "אלהים"]}'

# Known patterns
python3 tools/known_patterns.py '{"scholar": "welch"}'
python3 tools/known_patterns.py '{"book": "gen"}'
python3 tools/pattern_ingest.py '{"book":"gen","type":"chiasm","start":"gen.19.1","end":"gen.35.29","confidence":0.75,"notes":"new discovery"}'

# Graph traversal (entity-aware connection paths)
python3 tools/connections.py '{"tool": "scripture_graph_path", "start": "gen.1.1", "end": "john.1.1"}'
python3 tools/connections.py '{"tool": "scripture_graph_reachable", "verse": "gen.1.1", "max_depth": 3}'
python3 tools/connections.py '{"tool": "scripture_graph_hubs", "min_connections": 5}'
python3 tools/connections.py '{"tool": "scripture_graph_entities", "verse": "gen.1.1"}'
python3 tools/connections.py '{"tool": "scripture_graph_shared_entities", "verse": "gen.1.1"}'
python3 tools/connections.py '{"tool": "scripture_graph_entity_network", "entity": "abraham"}'
python3 tools/connections.py '{"tool": "scripture_graph_centrality", "book": "gen"}'

# Study guides (JSON-first, with graph paths)
python3 tools/guided_study.py '{"action": "create", "title": "Why Jesus Died", "seed": "lev.17.11", "theme": "atonement"}'
python3 tools/guided_study.py '{"action": "add_step", "guide_id": 1, "step_number": 1, "verse": "lev.17.11", "title": "The Blood Principle"}'
python3 tools/guided_study.py '{"action": "get", "guide_id": 1}'
python3 tools/guided_study.py '{"action": "export_json", "guide_id": 1}'
python3 tools/guided_study.py '{"action": "publish", "guide_id": 1, "author_name": "user"}'
python3 tools/guided_study.py '{"action": "list"}'
```

## Core Principle: Stick to Truth

This scripture tool has ONE loyalty: **what the text actually says**. The system must distinguish between:
- **The text itself** (what the actual words of scripture say)
- **Interpretive traditions** (what later rabbis, theologians, or commentators said the text means)

When discussing a passage, ALWAYS:
1. Start with what the text says (quote the actual words)
2. Only then explain interpretive traditions, clearly labeling them as such ("Rashi says...", "Calvin interprets...", "The Pharisees taught...")
3. When Jesus and the Pharisees disagreed, understand that Jesus was restoring the ORIGINAL intent of Torah against ADDED traditions — He was not setting Torah aside
4. Note when a common understanding of a passage comes from the text vs. from tradition

The goal is to let the user see the scripture clearly, without the layers of human tradition that may have obscured its original meaning. Distinguish between:
- `linguistic` connections: what the Hebrew/Greek actually says
- `interpretive` connections: how traditions read it
- Clearly label which is which

## What's in the Engine

- **70,956 verses** across 8 works (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha) — 330 books
- **1,356,667 typed connections** in 11 layers (linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, sod)
- **61 MCP/HTTP tools** — 15 of which are study-specific (create, edit, export, publish, fork, import)
- **Connection graph**: typed edges with layer, type, subtype, strength, confidence — traversable via graph_path, reachable, hubs
- **Gematria**: standard, ordinal, reduced — Hebrew and Greek
- **PaRDeS**: four-level interpretation system (P'shat, Remez, Drash, Sod)
- **Hidden patterns**: atbash, acrostics, temurah ciphers, divine name values
- **Study guides**: JSON-first (`scripture-study-v1`), publishable as shareable URLs, forkable, exportable as HTML/Markdown
- **LLM-powered editor**: `<study-action>` JSON blocks for AI-assisted study creation/modification

## How to Work With Scripture

1. **Look up a verse**: Use `verse` tool (supports gen.1.1, isa.6.1, 1ne.1.1, etc.)
2. **Check gematria**: Use `gematria` with a Hebrew word or verse reference
3. **Find patterns**: Use `patterns` for single-chapter literary detection
4. **Discover multi-chapter chiasms**: 
   - Run `chiasm_scan` for algorithmic candidates
   - Verify with `section_compare` for word count and keyword overlap
   - Check `known_patterns` to see if it's already documented
   - Save novel discoveries with `pattern_ingest`
5. **Search across the canon**: Use `search` or `frequency`

## Creating Study Guides (Shareable, LLM-Editable)

When the user asks for a guided exploration of a topic — tracing a theme through scripture — create a **study guide**. Studies are now JSON-first with full graph paths, publishable as shareable URLs.

### Workflow

1. **Create the guide**: `scripture_study_create` with title, seed verse, theme
2. **Explore connections**: Use `scripture_study_suggest` to get graph paths from the seed verse
3. **Add steps**: Each step has a verse, title, explanation, and selected connections (with full graph path data: layer, type, strength, confidence)
4. **Use the LLM editor**: After creating the guide, the user can open it in the StudyEditor tab, ask the LLM to modify it — the LLM returns `<study-action>` JSON blocks (add_step, remove_step, update_step, reorder, set_title, set_description) that the user reviews and applies
5. **Export**: `scripture_study_export_json(guide_id)` or `scripture_study_export_html(guide_id)` for a self-contained page
6. **Publish**: `scripture_study_publish(guide_id)` → returns a slug URL like `/study/why-jesus-died`
7. **Fork**: Anyone can fork a published study → get an editable copy with `forked_from` attribution → publish their own version

### Themes for guided studies (examples):
- `angel_of_the_lord` — Trace the Malach YHWH through the OT
- `zodiac` — Mazzaroth, constellations, Pleiades, Orion in scripture
- `covenant` — The covenant thread from Noah to Abraham to Moses to David to Christ
- `temple` — From Eden to Tabernacle to Temple to the Body of Christ
- `restoration` — The restoration theme from the OT prophets through the D&C
- `dispensations` — Gospel dispensations across scripture
- `atonement` — Why Jesus had to die (the law-based pathway through Torah)

### Example: Full create → publish cycle

```
User: "Create a study tracing the Angel of the Lord through scripture"
→ Create guide with seed "gen.16.7"
→ Suggest path: gen.16.7 → gen.22.11 → exo.3.2 → josh.5.13 → judg.6.11 → judg.13.3
→ Add each step with explanations + graph connections
→ Export as JSON to verify
→ Publish: {"slug": "angel-of-the-lord", "url": "/study/angel-of-the-lord"}
```

### Example: LLM editing (from StudyEditor tab)

```
User asks the LLM: "Add a step about the Red Heifer between steps 3 and 4"
→ LLM returns: <study-action>{"action":"add_step","step_number":4,"verse":"num.19.2","title":"The Red Heifer","explanation":"..."}</study-action>
→ User clicks "Apply" → step is inserted
→ User clicks "Save Changes" → persisted to DB
```

## HTTP API Server

The scripture engine runs as an HTTP API server:

```bash
cd /home/dillon/_code/scriptureengine
./run.sh web                    # Start server on port 8000
# Open http://localhost:8002/docs for interactive API browser
```

API endpoints (all return `{"ok": true, "data": ...}`):

```
# Core scripture
GET /api/v1/verses/{ref}                    # Verse + passage guide
GET /api/v1/verses/{ref}/connections         # Filtered connections
GET /api/v1/search?q=&lang=all              # Cross-lingual search
GET /api/v1/gematria?word=X                 # Gematria lookup
GET /api/v1/sod?verse=X                     # Hidden patterns
GET /api/v1/pardes/{ref}                    # PaRDeS levels

# Study guides (15+ endpoints)
GET    /api/v1/studies                      # List study guides
POST   /api/v1/studies                      # Create study guide
GET    /api/v1/studies/{id}                 # Get with enriched steps + graph paths
PATCH  /api/v1/studies/{id}                 # Update metadata
POST   /api/v1/studies/{id}/steps           # Add step
DELETE /api/v1/studies/{id}/steps/{n}       # Remove step
PUT    /api/v1/studies/{id}/steps           # Bulk replace all steps
GET    /api/v1/studies/{id}/export.json     # Export as JSON with graph paths
GET    /api/v1/studies/{id}/export.html     # Export as self-contained HTML
POST   /api/v1/studies/{id}/publish         # Publish → shareable slug URL
POST   /api/v1/studies/import               # Import from JSON
GET    /api/v1/studies/published            # List published studies
GET    /api/v1/studies/published/{slug}     # Get published study
POST   /api/v1/studies/published/{slug}/fork # Fork a published study

# UI + Chat
GET /api/v1/tabs                            # UI tab state
POST /api/v1/tabs                           # Create a tab
GET /api/v1/info                            # Database statistics
GET /api/v1/tools                           # List all 52 available tools
POST /api/v1/chat                           # LLM chat endpoint
```

### Generic Tool Endpoint

Every MCP tool is also available via HTTP:
```
GET  /api/v1/tools/scripture_graph_path?start=gen.1.1&end=john.1.1
POST /api/v1/tools/scripture_graph_path  {"start": "gen.1.1", "end": "john.1.1"}
GET  /api/v1/tools/scripture_study_publish?guide_id=1&author_name=user
```

All 52 tools are listed at `GET /api/v1/tools` with their schemas.

The API is CORS-enabled and can be called from any web frontend or LLM.

## Quick Reference: Bookmarks

Key files by purpose:
- HTTP API: `web/server.py`
- MCP server: `mcp_server.py`
- Study engine (CRUD, export, publish, fork): `lib/api/study.py`
- Pre-computed guides: `scripts/precompute_guides.py`
- Lexicon builder: `scripts/build_lexicon.py`
- Same-root generator: `generators/same_root.py`
- Formula marker generator: `generators/formula_markers.py`
- Hapax/dislegomenon generator: `generators/hapax_dislegomenon.py`
- Ordinal/reduced gematria generator: `generators/ordinal_reduced_gematria.py`
- Semuchin generator: `generators/semuchin.py`
- Temurah ciphers (Albam, Atbah, Avgad): `lib/sod/temurah.py`
- Milui/Kellali/Kidmi/Boneh gematria: `lib/gematria.py`
- Gematria: `lib/gematria.py`
- Hidden patterns (Sod): `lib/sod/`
- Anti-hallucination: `lib/controls/`
- Connection types: `lib/connections/types.py`
- PaRDeS levels: `lib/connections/pardes.py`
- Interactive study viewer: `frontend/src/components/StudyViewer.jsx`
- LLM-powered study editor: `frontend/src/components/StudyEditor.jsx`
- Deployment: `docs/deployment.md`

## Quick Reference: Book IDs

OT: gen, exo, lev, num, deu, josh, judg, ruth, 1sam, 2sam, 1kgs, 2kgs, 1chr, 2chr, ezra, neh, esth, job, psa, prov, eccl, song, isa, jer, lam, ezek, dan, hos, joel, amos, obad, jonah, mic, nah, hab, zeph, hag, zech, mal

NT: matt, mark, luke, john, acts, rom, 1cor, 2cor, gal, eph, phil, col, 1thes, 2thes, 1tim, 2tim, titus, philem, heb, james, 1pet, 2pet, 1john, 2john, 3john, jude, rev

BoM: 1ne, 2ne, jacob, enos, jarom, omni, wom, mosiah, alma, hel, 3ne, 4ne, morm, ether, moro

D&C: dc1, dc2, ... (section numbers)

PGP: moses, abraham, jsm, jsh, aoff

## Codebase Wiki

The codebase wiki at `docs/wiki/` documents the project architecture, conventions, and development workflow:

- **`_index.md`** — Architecture overview, quick reference, change impact map
- **`_standards.md`** — Coding rules, practices, patterns, enforcement
- **`features/web-api.md`** — FastAPI server, RAM cache, all endpoints
- **`features/lib-core.md`** — Database schema, tool registry, anti-hallucination, PaRDeS
- **`features/generators.md`** — Connection discovery algorithms, how to add new ones
- **`features/mcp-server.md`** — MCP protocol, 52 tools, testing
- **`_glossary.md`** — Project-specific terminology
- **`plans/`** — Architecture proposals and planning docs

For code-level questions about structure, standards, or how to add/modify tools, check the wiki first.
