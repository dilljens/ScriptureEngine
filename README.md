# Scripture Knowledge Engine

A deeply connected scripture study tool with **1.77M typed connections across 11 layers** — linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, and sod (hidden/temple). Hebrew gematria, Greek isopsephy, English text, all linked and quality-calibrated across **9 works** (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha, Expanded Canon).

**Live at [scriptureengine.org](https://scriptureengine.org)**

## Quick Start

```bash
git clone https://github.com/dilljens/ScriptureEngine.git
cd ScriptureEngine
bash scripts/setup.sh         # venv + deps + DB download
./run.sh web                  # Start API server on port 8000
# Open http://localhost:8002/docs
```

## Stats

| Metric | Value |
|--------|-------|
| Verses | **70,956** across 9 works, 330 books |
| Typed connections | **1,769,593** across 11 layers (124 types) |
| Hebrew verses | ~23,000 with gematria + morphology |
| Greek verses | ~8,000 with isopsephy |
| Hebrew gematria entries | 392K (standard, ordinal, reduced, mispar gadol, milui, kellali, kidmi, boneh) |
| Greek isopsephy entries | 137K |
| Biblical entities | **559** (people, places, concepts, divine names) |
| Entity-verse links | **88K** (which entities appear in which verses) |
| HTTP API endpoints | **133** with auto-generated OpenAPI docs |
| MCP tools | **63** for AI/LLM consumption |
| Python tests | **179** (CI-enforced), **153:1 → 179:68 source:test ratio improvement** |
| Lexicon lemmas | 25,813 (411 with LLM-written definitions) |
| Wiki articles | 60 in DB, 427+ generated markdown files |
| Hebrew curriculum | 102 nodes across 7 categories |
| Frontend components | 55 React components |
| Connection generators | 52 discovery scripts |

## Features

### Core Scripture Tools
- **Verse lookup** with full passage guide — connections, gematria, PaRDeS levels, entities, sources
- **Cross-lingual search** — English FTS5 + Hebrew/Greek via trigram FTS5 (typo-tolerant, substring matching)
- **Semantic search** — transformer embeddings (paraphrase-multilingual-MiniLM-L12-v2) with hybrid (vector + BM25 + graph) 3-way RRF fusion
- **Graph-enhanced search** — entity extraction → entity_links match → connection traversal as 3rd search signal
- **Query cache** — SQLite-backed persistent cache eliminates repeated searches (<10ms vs 70ms+)
- **Cross-encoder reranker** — optional reranker for improved result ordering (graceful degradation)
- **Gematria** — standard, ordinal, reduced, mispar gadol, milui, kellali, kidmi, boneh
- **Hebrew/Greek interlinear** — word-by-word with transliteration, Strong's, morphology
- **Hidden patterns (Sod)** — Atbash, acrostics, temurah ciphers (Albam, Atbah, Avgad), notarikon, divine name values

### Connection Graph
- **1.77M typed edges** traversable via path-finding, reachable sets, hub detection, entity-aware navigation
- **11 layers**: linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, sod
- **52 generators** that discover connections algorithmically
- **Quality calibration**: 5-star system, p-values, Bonferroni correction, FDR, null-text validation
- **Truth alignment v2**: Bayesian confidence ensemble, contradiction detection, temporal decay, inter-source agreement

### Study Guides
- JSON-first (`scripture-study-v1`), publishable as shareable URLs
- Full graph path data in each step
- Forkable, exportable as JSON/HTML/Markdown
- Interactive StudyViewer + LLM-powered StudyEditor
- Inline Quick Ask for AI-assisted study

### Wiki
- Wikipedia-style article viewer with sidebar, search, and browse
- Categories: entities, books, doctrines, works, layers, languages
- Alphabetical article index with A-Z filter
- Cross-entity links + key verses + assessment integration

### Hebrew Learning
- Full curriculum: aleph-bet, vowels, words, grammar, phrases, graded reading
- 102 nodes across 7 categories with prerequisite gating
- FSRS-5 spaced repetition per student per topic
- Verb conjugation drills with category selector
- Diagnostic pre-assessment → targeted remediation
- Gamification: XP, streaks, daily goals
- Clickable Hebrew in lessons with transliteration

### Memorization
- FSRS-5 spaced repetition scheduler
- Memory palaces with guided review ordering
- FIRe (Fluency-boosted Interleaved Review) credit propagation
- Repetition compression — connected due cards grouped together
- Graph centrality suggestion
- Macro-interleaving across works
- Connection-aware difficulty estimation

### PaRDeS Four-Level Interpretation
- **P'shat** (פְּשָׁט) — literal, contextual meaning
- **Remez** (רֶמֶז) — allegorical, hinted meaning
- **Drash** (דְּרַשׁ) — comparative, homiletical meaning
- **Sod** (סוֹד) — hidden, mystical meaning

### Anti-Hallucination Controls
- 5-star quality calibration with Bayesian confidence ensemble
- Preregistered hypothesis testing
- Null-text validation with empirical p-values
- Contradiction detection and resolution
- Inter-source agreement scoring
- Temporal decay and revalidation flags

### Cross-Canon Tools
- **Truth Score** — ecumenical consensus scoring across all 9 works
- **Interpretive disagreements** — 140+ seed disagreements with resolution workflow
- **OT-in-NT** — Old Testament quotations/allusions in the New Testament
- **JST diff viewer** — Joseph Smith Translation changes visualized
- **Joseph Smith teachings search**

## Architecture

```
                     ┌──────────────────────┐
                     │   AI / LLM (OpenCode) │
                     │    MCP client         │
                     └───────┬──────────────┘
                             │ stdio JSON-RPC
                     ┌───────▼──────────────┐
                     │   mcp_server.py      │
                     │   63 project-scoped   │
                     │   tools               │
                     └───────┬──────────────┘
                             │
┌────────────────────────────┼──────────────────────────┐
│                    ┌───────▼──────────────┐          │
│                    │   FastAPI HTTP API    │          │
│                    │   (133 endpoints)     │          │
│                    └───────┬──────────────┘          │
│                            │                          │
│                    ┌───────▼──────────────┐          │
│                    │   lib/ (core)        │          │
│                    │   • 20 api modules   │          │
│                    │   • 7 pattern modules│          │
│                    │   • 8 control modules│          │
│                    │   • 5 sod modules    │          │
│                    │   • 4 symbol modules │          │
│                    └───────┬──────────────┘          │
│                            │                          │
│                    ┌───────▼──────────────┐          │
│                    │   SQLite DB            │          │
│                    │   (2.3 GB) + FTS5     │          │
│                    │   + sqlite-vec         │          │
│                    │   + RAM cache          │          │
│                    └────────────────────────┘          │
│                                                        │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │ Frontend     │  │  52 Generators│  │  Go SRS       │ │
│  │ (React/Vite) │  │  (connection  │  │  (FSRS-5)     │ │
│  │ 55 components│  │   discovery)  │  │  + FIRe       │ │
│  └─────────────┘  └──────────────┘  └───────────────┘ │
└────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Backend**: Python 3.14+, FastAPI, SQLite 3.49+ (FTS5, sqlite-vec 0.1.9)
- **Frontend**: React 19, Vite, Tailwind CSS, Cytoscape.js, Playwright (E2E)
- **Embeddings**: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 via fastembed
- **SRS**: Go-based FSRS-5 with FIRe credit flow (backend/go-srs/)
- **CI**: GitHub Actions — frontend build, Go tests, Ruff lint, pytest (179 tests)

### Directory Structure
```
lib/               Core Python library — DB, API, connections, patterns, controls
  api/             20 modules — verse, search, gematria, graph, study, sod, etc.
  controls/        8 modules — calibration, contradiction, temporal, propagation, etc.
  patterns/        7 modules — chiastic, parallelism, frequency, structural, etc.
  sod/             5 modules — atbash, acrostic, temurah, notarikon, hidden_names
  symbols/         4 modules — typology, apocalyptic, shared_symbols, reference
  assessment/      4 modules — engine, items, models
web/               FastAPI server
  server.py        App entry + inline routes (74 endpoints)
  routes/          11 route files — studies, hebrew, memorize, graph, wiki, etc.
  cache.py         RAM cache layer
frontend/          React SPA
  src/components/  55 components — WikiArticleViewer, StudyViewer, ChatPanel, etc.
  src/lib/         scripture-markdown.jsx (unified :verse[]/:entity[] syntax)
generators/        52 connection discovery scripts
scripts/           129 utility scripts — ingest, migration, seeding, deploy
tools/             26 CLI tools — verse, gematria, search, patterns, chiasm, etc.
tests/             179 tests — pytest + Playwright E2E
backend/go-srs/    Go FSRS-5 spaced repetition system
```

### MCP Tools (63)
All tools registered in `lib/api/__init__.py`, auto-exposed via:
- **MCP server** (`mcp_server.py`) — stdio JSON-RPC for AI agents
- **HTTP API** generic endpoint — `GET/POST /api/v1/tools/{name}`

Categories (full listing at `/api/v1/tools`):
- **Verse**: verse, verse_text, passage_guide, compare, interlinear, similar_verses
- **Search**: search, search_xlingual, semantic_search, strongs
- **Gematria**: gematria, sod
- **Graph**: graph_path, graph_reachable, graph_hubs, graph_centrality, graph_entities, graph_shared_entities, graph_entity_network, graph_entity_cooccurrence, graph_stats
- **Entities**: entity_deep, entity_cooccurrence
- **PaRDeS**: pardes
- **Study guides**: study_create, study_get, study_add_step, study_remove_step, study_bulk_update, study_list, study_suggest, study_publish, study_fork, study_export_json, study_export_html, study_import_json, study_get_published, study_list_published
- **Disagreements**: disagreements, consensus, sources, sources_by_scholar, sources_list
- **Assessment**: assess_start, assess_answer, assess_progress, hebrew_quiz, hebrew_lesson, hebrew_lessons
- **Conversations**: conversation_create, conversation_get, conversation_list, conversation_delete, conversation_add_message, conversation_list_connections, conversation_promote_connection
- **Info**: info, versions

## Data Sources

| Source | Description |
|--------|-------------|
| BCBooks scriptures-json | LDS Standard Works (OT, NT, BoM, D&C, PGP) |
| Westminster Leningrad Codex | Hebrew OT with morphology |
| SBL Greek NT (morphgnt) | Greek NT with isopsephy |
| STEPBible | NT/OT manuscript variants |
| Joseph Smith Translation | 8,895 JST↔KJV diff connections |
| Avraham Gileadi | Isaiah pseudonyms, 7-part structure, 30 domino events |
| Margaret Barker | Temple theology interpretive connections |
| Farrell & Rhonda Pickering | Daniel numbers, prophetic timelines |
| DSS Textual Archive | Dead Sea Scrolls biblical variants and sectarian texts |
| R.H. Charles | Apocrypha and Pseudepigrapha texts |
| Emanuel Tov | Textual criticism connections |
| Crispin Fletcher-Louis | Divine council connections |

## Quick Commands

```bash
./run.sh info              # Database stats
./run.sh test              # Run test suite
./run.sh web               # Start API server on port 8000
./run.sh cleanup           # Connection graph cleanup
./run.sh embed             # Generate vector embeddings

# CLI tools
python3 tools/verse.py '{"book": "gen", "chapter": 1, "verse": 1}'
python3 tools/gematria.py '{"word": "יהוה"}'
python3 tools/search.py '{"query": "covenant"}'
python3 tools/connections.py '{"tool": "scripture_graph_path", "start": "gen.1.1", "end": "john.1.1"}'
python3 tools/guided_study.py '{"action": "create", "title": "Why Jesus Died", "seed": "lev.17.11"}'

# Build search index
python3 scripts/build_fts_index.py
python3 scripts/embed_verses.py
```

## Name

Working title: **Feasting Upon the Word** — reflecting a focus on deep, connected scripture study.
