# Scripture Knowledge Engine

A deeply connected scripture study tool with **1.36 million typed connections across 11 layers** — linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, and sod (hidden/temple). Hebrew gematria, Greek isopsephy, English text, all linked and quality-calibrated across **8 works**.

## Quick Start

```bash
# Start the API server
./run.sh web
# Open http://localhost:8002/docs
```

## Features

- **70,956 verses** across 8 works: OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha — 330 books
- **23K Hebrew verses** with gematria and morphology
- **8K Greek verses** with isopsephy
- **1,356,667 typed connections** across 11 layers (124 types)
- **392K Hebrew gematria entries** (standard, ordinal, reduced, mispar gadol)
- **137K Greek isopsephy entries** (standard, ordinal, reduced)
- **61 MCP tools** for AI/LLM consumption (project-scoped) + generic tool endpoint
- **103 HTTP API endpoints** with auto-generated OpenAPI docs
- **PaRDeS interpretation levels** — P'shat, Remez, Drash, Sod
- **Anti-hallucination quality controls** — 5-star calibration, p-values, Bonferroni correction, FDR, null-text validation, skeptic mode
- **AI review cleanup** — LLM validates connections before deprecation
- **Study guides** — JSON-first, publishable as shareable URLs, forkable, exportable as HTML/Markdown
- **Connection graph** — typed edges traversable via path-finding, reachable sets, hub detection, entity-aware navigation
- **Hebrew learning** — Full aleph-bet curriculum with FSRS-5 spaced repetition

## The 11 Connection Layers

| Layer | Types | Description |
|-------|-------|-------------|
| **linguistic** | 9 | Word-level language — same lemma, root, morphology, wordplay, cognates |
| **numerical** | 8 | Gematria values, divine name values, numerical relationships |
| **structural** | 16 | Chiasms, parallelisms, inclusios, refrains, acrostics, formula markers |
| **intertextual** | 9 | Quotations, allusions, echoes, type-antitype, midrashic connections |
| **textual** | 9 | Manuscript variants, JST changes, DSS variants, versions differences |
| **geographic** | 8 | Locations, journey paths, temple mount, exile routes |
| **chronological** | 8 | Timelines, genealogies, prophetic timelines, feast cycles |
| **interpretive** | 9 | Rabbinic midrash, patristic readings, Gileadi patterns, LDS readings |
| **frequency** | 11 | Word counts, hapax legomenon, 7/10/12/40-fold patterns |
| **symbolic** | 11 | Shared symbols, apocalyptic imagery, typology (person/event/object) |
| **sod** | 24 | Hidden/temple meanings — ascent, merkabah, divine council, theosis |

## Data Sources

| Source | Description |
|--------|-------------|
| BCBooks scriptures-json | LDS Standard Works (OT, NT, BoM, D&C, PGP) |
| Westminster Leningrad Codex | Hebrew OT with morphology |
| SBL Greek NT (morphgnt) | Greek NT with isopsephy |
| STEPBible | NT/OT manuscript variants |
| Joseph Smith Translation | 403 JST textual changes |
| Avraham Gileadi | Isaiah pseudonyms, 7-part structure, 30 domino events |
| Margaret Barker | Temple theology interpretive connections |
| Farrell & Rhonda Pickering | Daniel numbers, prophetic timelines |
| DSS Textual Archive | Dead Sea Scrolls biblical variants and sectarian texts |
| R.H. Charles | Apocrypha and Pseudepigrapha texts |

## Architecture

```
AI / LLM → MCP tools (56 project-scoped) ─┐
                                           ├─→ SQLite DB ─→ RAM cache
Web UI → FastAPI HTTP API (102 endpoints) ─┘
```

### MCP Tools (56)
All tools are registered in `lib/api/__init__.py` and auto-exposed via:
- **MCP server** (`mcp_server.py`) — stdio JSON-RPC for AI agents
- **HTTP API** generic endpoint — `GET/POST /api/v1/tools/{name}`

Categories: verse lookup, search (FTS5 + cross-lingual), gematria, Strong's lexicon, connections, graph traversal (path, reachable, hubs), entities, PaRDeS levels, sod/hidden patterns, study guides (CRUD + publish/fork/export), interpretive disagreements, ecumenical consensus, adaptive assessment, conversation management, Hebrew learning (lessons, quizzes, SRS), source provenance.

### HTTP API (102 endpoints)
Direct REST endpoints at `/api/v1/` covering: verse/chapter text with guides, gematria, sod patterns, cross-lingual search, footnotes, TSK cross-references, OT-in-NT, genealogy, grammar, connections, lexicon (lemma, root, domain), wiki articles, study guides (CRUD + publish/fork/export/import), conversations, Hebrew learning (FSRS-5 SRS), audio playback, forums, staging, tools, tabs, debug logging.

## Quick Commands

```bash
./run.sh info        # Database stats
./run.sh test        # Smoke tests
./run.sh web         # Start API server on port 8000
./run.sh cleanup     # Connection graph cleanup
./run.sh embed       # Generate vector embeddings
python3 scripts/project_stats.py   # Full project statistics
```

## Name

Working title: **Feasting Upon the Word** — reflecting a focus on deep, connected scripture study.
