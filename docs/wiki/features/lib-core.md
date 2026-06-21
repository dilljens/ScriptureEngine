# Core Library — lib/

The `lib/` directory contains all shared logic: database, connection types, gematria, PaRDeS, symbols, ant-hallucination controls, and the tool registry.

## Architecture

```
  lib/
  ├── db.py                 — SQLite schema + operations
  ├── gematria.py           — Hebrew gematria computation
  ├── gematria_greek.py     — Greek isopsephy computation
  │
  ├── api/                   — Shared tool registry
  │   ├── __init__.py       — TOOL_REGISTRY + register() + list_tools() + call_tool()
  │   ├── verse.py          — lookup_verse, passage_guide
  │   ├── search.py         — search_text, search_xlingual
  │   ├── gematria.py       — gematria_lookup
  │   ├── connections.py    — get_connections, get_intertext, get_pardes
  │   ├── graph.py          — graph_path, graph_reachable, graph_hubs, ...
  │   ├── sod.py            — hidden_patterns
  │   ├── study.py          — create_guide, add_step, get_guide, suggest_path
  │   └── info.py           — get_stats
  │
  ├── lexicon/
  │   └── __init__.py       — Lexicon builder, search, root families, concordance, collocations
  │
  ├── connections/
  │   ├── types.py          — Layer definitions (10 layers, 88 types)
  │   └── pardes.py         — PaRDeS level mapping
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
  │   └── notarikon.py      — Notarikon (acronym) extraction
  │
  └── symbols/
      ├── reference.py      — Symbol seed data (~80 symbols) + typology
      ├── shared_symbols.py — Symbol occurrence matching
      └── typology.py       — Type/antitype connection generator
```

## Key Functions

| Function | File | Purpose |
|----------|------|---------|
| `get_db()` | `db.py:14` | Connect to SQLite with WAL |
| `add_connection()` | `db.py` | Insert/upsert a connection |
| `get_connections()` | `db.py` | Get connections for a verse |
| `compute_all()` | `gematria.py` | Compute standard/ordinal/reduced gematria |
| `list_tools()` | `api/__init__.py` | List all MCP/HTTP tools |
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

The `lib/api/__init__.py` `TOOL_REGISTRY` is the **single source of truth** for all 23 tools (22 MCP tools + info endpoint):
- Both MCP server (`mcp_server.py`) and HTTP API (`web/server.py`) consume it
- Adding a new tool = one registration + one function
- Each tool has: `name`, `description`, `inputSchema` (JSON Schema)

## Path Scope

- `lib/db.py` — schema + all DB operations
- `lib/api/` — tool registry (consumed by MCP + HTTP)
- `lib/lexicon/` — word dictionary, roots, collocations, concordance
- `lib/connections/` — type definitions + PaRDeS
- `lib/controls/` — anti-hallucination
- `lib/sod/` — hidden pattern detection
- `lib/symbols/` — symbol data + typology
- `lib/gematria.py` / `lib/gematria_greek.py` — numerical computation
- `scripts/ingest_vulgate.py` — Latin Vulgate textual variant ingestion
