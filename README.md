# Scripture Knowledge Engine

A deeply connected scripture study tool with 218K+ typed connections across 10 layers — linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, and symbolic. Hebrew gematria, Greek isopsephy, English text, all linked and quality-calibrated.

## Quick Start

```bash
# Start the API server
./run.sh web
# Open http://localhost:8000/docs
```

## Features

- **42K verses** across OT, NT, BoM, D&C, PGP
- **23K Hebrew verses** with gematria and morphology
- **8K Greek verses** with isopsephy
- **218K typed connections** across 10 layers
- **Semantic search** via vector embeddings (sqlite-vec)
- **RAM-cached passage guides** — instant per-verse connection context
- **10 MCP tools** for AI consumption (project-scoped)
- **12 HTTP API endpoints** with OpenAPI docs
- **PaRDeS interpretation levels** — P'shat, Remez, Drash, Sod
- **Anti-hallucination quality controls** — p-values, null-text validation, skeptic mode
- **AI review cleanup** — LLM validates connections before deprecation

## Data Sources

| Source | Description |
|--------|-------------|
| BCBooks scriptures-json | LDS Standard Works |
| Westminster Leningrad Codex | Hebrew OT with morphology |
| SBL Greek NT (morphgnt) | Greek NT with isopsephy |
| STEPBible | NT/OT manuscript variants |
| Joseph Smith Translation | 403 JST textual changes |
| Avraham Gileadi | Isaiah pseudonyms, 7-part structure, 30 domino events |
| Margaret Barker | Temple theology interpretive connections |
| Farrell & Rhonda Pickering | Daniel numbers, prophetic timelines |

## Architecture

```
AI / LLM → MCP tools (project-scoped)  ─┐
                                         ├─→ SQLite DB ─→ RAM cache
Web UI → FastAPI HTTP API /api/v1/ ──────┘
```

## Quick Commands

```bash
./run.sh info        # Database stats
./run.sh test        # Smoke tests
./run.sh web         # Start API server
./run.sh cleanup     # Connection graph cleanup
./run.sh embed       # Generate vector embeddings
```

## Name

Working title: **Feasting Upon the Word** — reflecting a focus on deep, connected scripture study.
