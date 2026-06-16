# Scripture Knowledge Engine

Project-level instructions for the scripture knowledge base at `/home/dillon/_code/scripture-explorer/`.

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

# Guided studies (AI-led connection graph exploration)
python3 tools/guided_study.py '{"action": "create", "title": "Angel of the Lord", "seed": "gen.16.7", "theme": "angel_of_the_lord"}'
python3 tools/guided_study.py '{"action": "add_step", "guide_id": 1, "step_number": 1, "verse": "gen.16.7", "title": "explanation here", "choices": [{"verse":"gen.22.11","label":"Next step"}]}'
python3 tools/guided_study.py '{"action": "get", "guide_id": 1}'
python3 tools/guided_study.py '{"action": "suggest_path", "seed": "gen.16.7", "theme": "angel_of_the_lord"}'
python3 tools/guided_study.py '{"action": "build_tab", "guide_id": 1, "tab_name": "Angel of the Lord"}'
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

## Creating Guided Studies (AI-Led Topic Exploration)

When the user asks for a guided exploration of a topic — tracing the "Angel of the Lord" through scripture, understanding how the zodiac appears, following the covenant thread, etc. — use the `guided_study` tool:

### Workflow

1. **Create the guide**: `{"action": "create", "title": "...", "seed": "gen.16.7", "theme": "..."}`
2. **Explore the connection graph**: `{"action": "suggest_path", "seed": "gen.16.7", "theme": "angel_of_the_lord"}`
   - This returns direct connections from the seed verse + deeper paths
   - Use the connection data + your own semantic understanding of the theme to select the path
3. **Add each step**: `{"action": "add_step", "guide_id": 1, "step_number": 1, "verse": "gen.16.7", "title": "title", "explanation": "explanation", "choices": [{"verse": "...", "label": "..."}]}`
   - `choices` are branching options the user can take at each step
   - Each choice points to a possible next verse in the exploration
4. **Build a UI tab**: `{"action": "build_tab", "guide_id": 1, "tab_name": "Angel of the Lord"}`
   - Creates a custom tab linked to the study guide
5. **Present the study to the user** with the path and explanations

### Themes for guided studies (examples):
- `angel_of_the_lord` — Trace the Malach YHWH through the OT
- `zodiac` — Mazzaroth, constellations, Pleiades, Orion in scripture
- `covenant` — The covenant thread from Noah to Abraham to Moses to David to Christ
- `temple` — From Eden to Tabernacle to Temple to the Body of Christ
- `restoration` — The restoration theme from the OT prophets through the D&C
- `dispensations` — Gospel dispensations across scripture

### Example

```
User: "Create a guided study tracing the Angel of the Lord through scripture"
→ Create guide with seed "gen.16.7" (first Angel appearance)
→ Suggest path → get connections and deeper paths
→ Select path: gen.16.7 → gen.22.11 → exo.3.2 → josh.5.13 → judg.6.11 → judg.13.3
→ Add each step with explanations
→ Build tab
→ Present to user
```

## Database

```bash
./run.sh info     # show database stats
./run.sh test     # run smoke tests
```

## HTTP API Server

The scripture engine also runs as an HTTP API server:

```bash
cd /home/dillon/_code/scripture-explorer
./run.sh web                    # Start server on port 8000
# Open http://localhost:8000/docs for interactive API browser
```

API endpoints (all return `{"ok": true, "data": ...}`):

```
GET /api/v1/verses/{ref}                    # Verse + passage guide
GET /api/v1/verses/{ref}/connections         # Filtered connections
GET /api/v1/search?q=&lang=all              # Cross-lingual search
GET /api/v1/gematria?word=X                 # Gematria lookup
GET /api/v1/sod?verse=X                     # Hidden patterns
GET /api/v1/pardes/{ref}                    # PaRDeS levels
GET /api/v1/tabs                            # UI tab state
POST /api/v1/tabs                           # Create a tab
GET /api/v1/info                            # DB statistics
```

The API is CORS-enabled and can be called from any web frontend or LLM.

## Quick Reference: Bookmarks

Key files by purpose:
- HTTP API: `web/server.py`
- MCP server: `mcp_server.py`
- Pre-computed guides: `scripts/precompute_guides.py`
- Gematria: `lib/gematria.py`
- Hidden patterns (Sod): `lib/sod/`
- Anti-hallucination: `lib/controls/`
- Connection types: `lib/connections/types.py`
- PaRDeS levels: `lib/connections/pardes.py`

## Quick Reference: Book IDs

OT: gen, exo, lev, num, deu, josh, judg, ruth, 1sam, 2sam, 1kgs, 2kgs, 1chr, 2chr, ezra, neh, esth, job, psa, prov, eccl, song, isa, jer, lam, ezek, dan, hos, joel, amos, obad, jonah, mic, nah, hab, zeph, hag, zech, mal

NT: matt, mark, luke, john, acts, rom, 1cor, 2cor, gal, eph, phil, col, 1thes, 2thes, 1tim, 2tim, titus, philem, heb, james, 1pet, 2pet, 1john, 2john, 3john, jude, rev

BoM: 1ne, 2ne, jacob, enos, jarom, omni, wom, mosiah, alma, hel, 3ne, 4ne, morm, ether, moro

D&C: dc1, dc2, ... (section numbers)

PGP: moses, abraham, jsm, jsh, aoff
