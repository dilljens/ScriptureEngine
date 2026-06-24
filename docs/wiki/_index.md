# Scripture Knowledge Engine — Codebase Wiki

A deeply connected scripture study tool with **1.07M+ typed connections** across **125 types** in 11 layers — linguistic, numerical, structural, intertextual, textual, geographic, chronological, interpretive, frequency, symbolic, and sod (hidden/temple). Hebrew gematria, Greek isopsephy, English text, Septuagint variants, Vulgate Latin variants, DSS variants, STEPBible textual variations, lemma lexicon, semantic domains, temple theology, and Merkabah mysticism — all linked and quality-calibrated.

Live at **https://scriptureengine.org** — Hetzner CX23, 2 workers, Let's Encrypt SSL.

## Quick Reference

```bash
# Start API
./run.sh web              # uvicorn on port 8000 (2 workers by default)

# Database
./run.sh info             # Stats: verses, connections per layer
./run.sh test             # Smoke tests
python3 scripts/precompute_guides.py   # Rebuild passage guide cache

# MCP Server (auto-started by opencode)
python3 mcp_server.py     # Stdio JSON-RPC

# Tools
python3 tools/verse.py '{"book":"gen","chapter":1,"verse":1}'
python3 tools/search.py '{"query":"covenant"}'
python3 tools/gematria.py '{"word":"יהוה"}'
python3 tools/connections.py '{"verse":"gen.1.1"}'
python3 tools/patterns.py '{"book":"isa","chapter":6}'

# Deploy
./scripts/deploy.sh       # Build + rsync to Hetzner

# Tests
cd frontend && npm test   # 45 Playwright E2E tests
```

## Architecture

```
mcp_server.py            ← Stdio JSON-RPC → opencode (MCP client)
     │
     ▼
lib/api/__init__.py      ← Tool registry (52 tools)
     │
     ├── lib/api/verse.py        ├── lib/api/search.py
     ├── lib/api/gematria.py     ├── lib/api/connections.py
     ├── lib/api/graph.py        ├── lib/api/sod.py
     ├── lib/api/study.py        ├── lib/api/info.py
     ├── lib/api/conversations.py ← Chat session persistence
     ├── lib/api/sources.py      ├── lib/api/strongs.py
     ├── lib/api/interlinear.py  ├── lib/api/consensus.py
     ├── lib/api/disagreements.py ├── lib/api/assessment.py
     ├── lib/api/staging.py      ├── lib/api/versions.py
     │
     ▼
lib/db.py                ← SQLite (data/processed/scripture.db)
     │
     ├── generators/      ← 44 connection discovery algorithms
     ├── lib/connections/ ← 125 types in 11 layers
     ├── lib/controls/    ← Anti-hallucination + quality
     ├── lib/gematria.py  ← Hebrew gematria computation
     ├── lib/poetry/      ← Hebrew poetry line splitting
     ├── lib/sod/         ← Hidden patterns (Atbash, acrostics, temurah)
     ├── lib/symbols/     ← Symbol reference + typology
     ├── lib/lexicon/     ← Lemma/lexicon search
     └── lib/api/         ← Shared tool registry

web/server.py            ← FastAPI HTTP (port 8000, 2 workers)
     │
     ├── /api/v1/verses/{ref}          [?context=N]
     ├── /api/v1/verses/{ref}/guide
     ├── /api/v1/verses/{ref}/connections
     ├── /api/v1/verses/{ref}/grammar
     ├── /api/v1/chapter/{ref}
     ├── /api/v1/connections/chapter/{ref}
     ├── /api/v1/parallelism/isaiah/{chapter}
     ├── /api/v1/search
     ├── /api/v1/gematria
     ├── /api/v1/semantic-search
     ├── /api/v1/pardes/{ref}
     ├── /api/v1/footnotes/{ref}
     ├── /api/v1/tsk-crossrefs/{ref}
     ├── /api/v1/grammar/{ref}
     ├── /api/v1/tabs
     ├── /api/v1/books
     ├── /api/v1/tools/{name}
     ├── /api/v1/lexicon/*
     ├── /api/v1/health
     └── /api/v1/info
```

## Data Flow

```
Raw JSON scriptures           → scripts/ingest.py     → SQLite
Generated connections          → generators/*.py       → connections table
Symbol/typology seed data     → scripts/seed_*.py     → symbols/typology tables
Passage guides (materialized) → scripts/precompute_guides.py → passage_guides table
RAM cache on startup          → web/server.py         → dict in memory (~500MB)
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.14 |
| API Framework | FastAPI 0.136 + uvicorn 0.46 |
| Database | SQLite (WAL mode, sqlite-vec) |
| MCP Protocol | JSON-RPC over stdio |
| Anti-hallucination | P-values, null-text validation, preregistration |
| Data Generation | Algorithmic generators + agent-driven (read+judge, no API) |
| Vector Search | sqlite-vec (character n-gram hashing) |
| Frontend | React 19 + Vite 6.4.3 + Tailwind 3 |
| E2E Testing | Playwright (23 tests, headless chromium) |

## Key Numbers

| Metric | Value |
|--------|-------|
| Total verses | 42,054 |
| Hebrew verses (gematria) | 23,213 |
| Greek verses (isopsephy) | 7,925 |
| Total connections | **1,065,628** |
| Connection layers | 11 |
| Connection types | **128** (124 populated, 96.9% coverage) |
| Lexicon entries | 11,515 |
| Collocation pairs | 50,216 |
| Unique roots | 7,853 |
| Semantic domains seeded | 15 (372 members) |
| Entity links | 87 |
| Generators registered | 36 (34 auto, 2 manual) |
| Connection judgment files | 14 (agent-generated) |
| JST changes (jst_change + jst_addition) | **8,796** |
| JS teachings corpus | 9 sources, **5,067** scripture cross-refs (incl. STPJS) |
| Textual variants (Vulgate) | 31,077 |
| Passage guides cached | 41,625 |
| MCP/HTTP tools | 23 |
| RAM cache size | ~500 MB |
| Frontend tests | 23 Playwright E2E tests |
| Frontend stack | React 19, Vite 6, Tailwind 3 |

## Connection Layers Breakdown

| Layer | Connections | Types |
|-------|-----------|-------|
| numerical | 275,415 | 8/8 |
| linguistic | 268,816 | 9/9 |
| intertextual | 240,450 | 9/9 |
| structural | 71,764 | 16/16 |
| frequency | 65,902 | 11/11 |
| textual | 37,814 | 3/8 |
| chronological | 24,321 | 8/8 |
| symbolic | 23,424 | 11/11 |
| sod | 26,465 | 30/30 |
| geographic | 14,265 | 8/8 |
| interpretive | 8,196 | 9/9 |

## Change Impact Map

| Change This | Look At |
|-------------|---------|
| Add a new tool | `lib/api/__init__.py` (register) + `lib/api/*.py` (implement) |
| Add a connection type | `lib/connections/types.py` (define) + `generators/*.py` (generate) |
| Add a generator | `generators/__init__.py` (register) + `generators/*.py` (implement) |
| Change API behavior | `web/server.py` |
| Change data model | `lib/db.py` (schema) + `scripts/precompute_guides.py` (cache) |
| Change frontend UI | `frontend/src/components/` (VerseBlock, ChatPanel, etc.) |
| Add E2E test | `frontend/e2e/*.spec.ts` |
| Change test config | `frontend/playwright.config.ts` |
| Add API endpoint | `web/server.py` (route) |
| Add API context param | `web/server.py` `get_verse(..., context=int)` |
| Add a component | `frontend/src/components/*.jsx` |
| Add agent-driven judgments | `data/agent_connections/*.json` + apply script |
| Run agent classification | Read verses → judge → write → `scripts/apply_judgments.py` |
| Add self-referencing cross-canon quotations | `scripts/generate_self_references.py` |
| Ingest variant texts | `scripts/ingest_vulgate.py` → `textual_variants` table |
| Add ingest source | `scripts/ingest.py` |

## PaRDeS Levels

| Level | Name | Meaning |
|-------|------|---------|
| P'shat | פשט | Simple/literal — what the text says |
| Remez | רמז | Hinted — what the text alludes to |
| Drash | דרש | Inquired — how the text connects across the canon |
| Sod | סוד | Hidden — deep structural and numerical patterns |

## Agent-Driven Connections

13 connection types have entries generated by the agent reading the text directly — no external API, no model calls. The agent reads verse pairs, judges whether a genuine connection exists, and writes the reasoning:

| Type | Count | Approach |
|------|-------|----------|
| `prophetic_fulfillment` | 30 | OT→NT fulfillment pairs judged individually |
| `type_antitype` | 20 | Typological patterns across canon |
| `modified_quotation` | 24 | NT intentional changes to OT quotes |
| `wordplay` | 19 | Hebrew paronomasia (adam/adamah, etc.) |
| `nomen_est_omen` | 25 | Name meanings in narrative context |
| `midrashic_connection` | 21 | NT rabbinic hermeneutical methods |
| `summarized` | 20 | OT summarized in later texts |
| `apocalyptic_time` | 33 | Time symbols across Daniel and Revelation |
| `cognate` | 10 | Hebrew↔Aramaic cognate pairs |
| `semantic_domain` | 16 | Conceptual domains across canon |
| `prophetic_quote` | 10 | Modern prophetic use of scripture |
| `lectio_divina` | 5 | Monastic spiritual reading tradition |
| `inspired_revision` | 11 | JST expansions (Moses, Abraham) |

Each connection includes human-readable `reasoning` in metadata. Files in `data/agent_connections/`.

## Self-Referencing Connections

The `scripts/generate_self_references.py` generator catches cross-canonical quotations the automated `intertextual.py` misses:

- **BoM→Isaiah**: 2 Ne 12-24 = Isaiah 2-14 (275 verse pairs), 1 Ne 20-21 = Isaiah 48-49 (48 pairs), Mosiah 14-15 = Isaiah 53-54 (12 pairs)
- **Known cross-references**: D&C↔OT, D&C↔Revelation, Moses↔Genesis, BoM↔NT (22 pairs)
- `direct_quotation` went from **156 → 513** connections

## Latin Vulgate Ingestion

The Clementine Vulgate was ingested into `textual_variants` table:

- **Source**: `yoarikso/latinvulgatebible` (MIT license)
- **Verses stored**: 31,077 (OT + NT, mapped via Psalm/Esther/Daniel numbering)
- **Connections**: 33,082 `vulgate_variant` (per-book hub-and-spoke + 5 curated)

The Vulgate fills the `vulgate_variant` connection type. Remaining textual variant types (`dead_sea_scrolls_variant`, `peshitta_variant`, `inspired_revision`) need text corpora.

## Plans

See [plans/](plans/) for architecture proposals:

- [Agent-Driven Connections](plans/agent-connections.md) — agent reads text directly, no API
- [Lexicon Plan](plans/llm-lexicon-plan.md) — lexicon + connection expansion (agent-driven)
- [Giliadi Methods](plans/giliadi-methods-comparison.md) — Isaiah techniques tracking
- [Rabbinic Tools](plans/rabbinic-kabbalistic-tools.md) — planned agent-driven tools

## Staleness

| Domain | Last Updated | Status |
|--------|-------------|--------|
| Index | 2026-06-21 | UPDATED — Frontend docs, API endpoints, Playwright tests, connection panel |
| Standards | 2026-06-16 | FRESH |
| Features/web | 2026-06-21 | UPDATED — added `?context=N` param, new endpoints |
| Features/lib | 2026-06-17 | FRESH |
| Features/generators | 2026-06-17 | UPDATED — 35 generators, Rabbinic Kal v'Chomer + Mukdam u'Meuchar added |
| Features/frontend | 2026-06-21 | NEW — React app, connection panel, footnote tooltip, VersePreviewCard, Playwright tests |
| Plans | 2026-06-22 | FRESH — completed A+B: JST full text, JS teachings corpus |
| Generators | 2026-06-22 | UPDATED — 36 generators, Temple Themes sod + JST full ingest |
| Connection types | 2026-06-22 | UPDATED — 128 types, 96.9% populated, JST types added |
| JS teachings | 2026-06-22 | NEW — js_sources table, js_scripture_refs, FTS search, tools/js_teachings.py |
