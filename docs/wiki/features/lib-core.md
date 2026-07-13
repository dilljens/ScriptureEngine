# Core Library — lib/

The `lib/` directory contains all shared logic: database, connection types, gematria, PaRDeS, symbols, anti-hallucination controls, the tool registry, conversation sessions, Hebrew curriculum, and assessment engine.

## Architecture

```
  lib/
  ├── db.py                 — SQLite schema + operations
  ├── gematria.py           — Hebrew gematria computation (standard, ordinal, reduced, milui, kellali, kidmi, boneh)
  ├── gematria_greek.py     — Greek isopsephy computation
  ├── poetry/               — Hebrew poetry line splitting
  │
  ├── api/                   — Shared tool registry
  │   ├── __init__.py       — TOOL_REGISTRY (60 tools) + register() + list_tools() + call_tool()
  │   ├── verse.py          — lookup_verse, passage_guide, verse_text
  │   ├── search.py         — search_text, search_xlingual
  │   ├── gematria.py       — gematria_lookup
  │   ├── connections.py    — get_connections, get_intertext, get_pardes, get_compare
  │   ├── graph.py          — graph_path, graph_reachable, graph_hubs, graph_entities,
  │   │                       graph_entity_network, graph_shared_entities, graph_centrality, graph_stats, graph_context
  │   ├── sod.py            — hidden_patterns
  │   ├── study.py          — create, add_step, get, list, suggest, update, remove_step,
  │   │                       export_json, export_html, publish, import_json, fork, bulk_update
  │   ├── info.py           — get_stats, get_versions, get_tools
  │   ├── conversations.py  — Chat session persistence (create, get, list, delete, add_message, list_connections, promote_connection)
  │   ├── sources.py        — Source provenance (by_verse, by_scholar, list_scholars)
  │   ├── strongs.py        — Strong's definition lookup
  │   ├── interlinear.py    — Word-by-word interlinear analysis
  │   ├── consensus.py      — Ecumenical consensus data
  │   ├── disagreements.py  — Contradictory readings across traditions
  │   ├── assessment.py     — Adaptive quiz (start, answer, progress)
  │   ├── research.py       — Multi-hop thematic research
  │   ├── entity.py         — Deep entity dive
  │   └── staging.py        — Staging/approval tools
  │   └── versions.py       — List available Bible text versions
  │
  ├── lexicon/
  │   └── __init__.py       — Lexicon builder, search, root families, concordance, collocations
  │
  ├── connections/
  │   ├── types.py          — Layer definitions (11 layers, 128 types)
  │   └── pardes.py         — PaRDeS level mapping (P'shat, Remez, Drash, Sod)
  │
  ├── controls/
  │   ├── calibration.py    — Quality levels + emoji mapping
  │   ├── null_text.py      — Null-text validation
  │   ├── preregistration.py — Pre-registration of hypotheses
  │   └── stats.py          — Statistical tests
  │
  ├── sod/
  │   ├── atbash.py         — Atbash cipher decoding
  │   ├── acrostic.py       — Acrostic detection
  │   ├── gematria_advanced.py — Advanced gematria patterns
  │   ├── hidden_names.py   — Hidden name detection
  │   ├── notarikon.py      — Notarikon (acronym) extraction
  │   └── temurah.py        — Temurah ciphers (Albam, Atbah, Avgad)
  │
  ├── symbols/
  │   ├── reference.py      — Symbol seed data (~80 symbols) + typology
  │   ├── shared_symbols.py — Symbol occurrence matching
  │   └── typology.py       — Type/antitype connection generator
  │
  ├── sefaria/               — Jewish tradition (Sefaria) integration
  │   └── mapper.py         — Sefaria reference mapping (387K+ connections: Rashi, Ramban, Talmud, Zohar, Midrash)
  │
  └── assessment/
      ├── engine.py         — Adaptive assessment engine (IRT-style)
      └── grading.py        — LLM-graded open-ended question evaluation
```

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `get_db()` | `db.py:14` | Connect to SQLite with WAL |
| `add_connection()` | `db.py` | Insert/upsert a connection |
| `get_connections()` | `db.py` | Get connections for a verse |
| `compute_all()` | `gematria.py` | Compute standard/ordinal/reduced gematria |
| `list_tools()` | `api/__init__.py` | List all 60 MCP/HTTP tools |
| `call_tool()` | `api/__init__.py` | Dispatch to any registered tool |
| `get_pardes_level()` | `connections/pardes.py` | Map layer+type to PaRDeS level |
| `build_lexicon()` | `lexicon/__init__.py` | Build lexicon table from gematria data |
| `search_lexicon()` | `lexicon/__init__.py` | Search by lemma, Hebrew, or English |
| `get_lexicon_entry()` | `lexicon/__init__.py` | Full entry with collocations |
| `get_root_family()` | `lexicon/__init__.py` | All lemmas sharing a root |
| `get_concordance()` | `lexicon/__init__.py` | All verses containing a lemma |

## Vulgate & Textual Variants

The Latin Vulgate was ingested into the `textual_variants` table (31,077 verses, mapped via Psalm/Esther/Daniel numbering), generating 33,082 `vulgate_variant` connections per-book hub-and-spoke + 5 curated pairs. See `scripts/ingest_vulgate.py`.

## Lexicon Module

`lib/lexicon/__init__.py` builds a word dictionary entirely from the gematria table:

- **Dictionary**: 11,515 unique lemmas with Hebrew, root extraction, frequency, morphology
- **Word families**: 7,853 unique roots extracted, 50,216 collocation pairs (co-occurring lemmas within verses)
- **Concordance**: Full verse list per lemma via gematria table JOIN
- **Semantic domains**: 15 seeded algorithmically (372 members); agent can expand by reading domain keywords

## Anti-Hallucination System

Located in `lib/controls/`:

- **Calibration**: Quality levels from `certain` (green) to `rejected` (red), mapped to emoji
- **Null-text validation**: Compares against statistically expected baselines
- **Pre-registration**: Hypotheses registered before testing to prevent p-hacking
- **P-values**: Statistical significance on algorithmic connections

## Tool Registry Pattern

The `lib/api/__init__.py` `TOOL_REGISTRY` is the **single source of truth** for all **60 tools**:
- Both MCP server (`mcp_server.py`) and HTTP API (`web/server.py`) consume it
- Adding a new tool = one registration + one function
- Each tool has: `name`, `description`, `inputSchema` (JSON Schema)
- Tools are discovered from `lib/api/*.py` modules, not manually listed

## Hebrew Assessment Engine

`lib/assessment/` contains the adaptive assessment system:
- **engine.py**: IRT-style adaptive quiz (start → question → answer → next)
- **grading.py**: LLM-graded open-ended questions with 4-dimension rubric
- Integrates with `web/routes/assessment.py` for HTTP API

## Sefaria Integration

`lib/sefaria/mapper.py` maps connections between scripture verses and Jewish tradition sources:
- **387K+ connections** from Rashi, Ramban, Talmud, Zohar, Midrash
- Each connection tagged with `tradition: jewish` and `tradition: multiple` where applicable

## Path Scope

- `lib/db.py` — schema + all DB operations
- `lib/api/` — tool registry (consumed by MCP + HTTP), 60 tools
- `lib/lexicon/` — word dictionary, roots, collocations, concordance
- `lib/connections/` — type definitions (11 layers, 128 types) + PaRDeS
- `lib/controls/` — anti-hallucination
- `lib/sod/` — hidden pattern detection (atbash, acrostics, temurah, notarikon)
- `lib/symbols/` — symbol data + typology
- `lib/gematria.py` / `lib/gematria_greek.py` — numerical computation
- `lib/assessment/` — adaptive engine + LLM grading
- `lib/sefaria/` — Jewish tradition integration
- `lib/poetry/` — Hebrew poetry splitting
- `scripts/ingest_vulgate.py` — Latin Vulgate textual variant ingestion
