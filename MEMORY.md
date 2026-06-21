# Scripture Knowledge Engine — Project Memory

> Auto-generated snapshot. Last updated: 2026-06-21

## Facts

- **Verses**: 42,054 total (23,213 Hebrew, 7,925 Greek)
- **Connections**: 1,028,083 typed connections across 88 types in 10 layers
- **Database**: SQLite at `data/processed/scripture.db` (WAL mode)
- **Lexicon**: 11,515 lemmas, 7,853 unique roots, 50,216 collocation pairs
- **Textual Variants**: 31,077 Vulgate Latin verses ingested
- **Passage Guides**: 41,624 cached (materialized view)
- **Entity Links**: 87 (people/places/concepts)
- **RAM Cache**: ~500 MB at startup (sub-ms lookups)
- **Frontend**: React 19 + Vite 6.4.3 + Tailwind 3, Playwright E2E tests
- **API context param**: `GET /api/v1/verses/{ref}?context=N` returns N surrounding verses

## Tools

- **MCP/HTTP tools**: 23 registered in `lib/api/__init__.py` TOOL_REGISTRY
- **MCP server**: `mcp_server.py` (stdio JSON-RPC, supports v2024-11-05 + v2025-03-26)
- **HTTP API**: `web/server.py` (FastAPI + uvicorn, port 8000)

## Generators

- **35 generators** registered in `generators/__init__.py` (33 auto, 2 manual)
- **13 agent-judged connection types** supplement algorithmic generators
- **2 new rabbinic generators** (2026-06-17): Kal v'Chomer, Mukdam u'Meuchar

## Frontend

- **React app** at `frontend/`, Vite dev server on port 5173, proxy `/api` → port 8000
- **Connection Panel**: unified collapsible panel per verse — grouped by type, filterable, confidence dots (green/yellow/gray)
- **Footnote Tooltip**: rich HTML popover on hover — shows category, context word, referenced verse texts
- **VersePreviewCard**: scrollable full-chapter preview with highlighted verses — used in LLM chat results
- **Multi-word footnotes**: sliding-window matching for phrase context words (e.g. "away with", "Holy Ghost")
- **Playwright E2E tests**: 23 tests in `frontend/e2e/` (app load, navigation, connections, footnotes, TSK, command palette, search)
- **Test command**: `cd frontend && npm test` (headless, no window popup)

## Layers

| Layer | Connections | Types |
|-------|-----------|-------|
| numerical | 275,415 | 8 |
| linguistic | 268,816 | 8 |
| intertextual | 242,789 | 8 |
| structural | 71,763 | 16 |
| frequency | 65,902 | 11 |
| textual | 33,211 | 7 |
| chronological | 24,321 | 8 |
| symbolic | 23,409 | 11 |
| geographic | 14,265 | 8 |
| interpretive | 8,192 | 8 |

## Conventions

- Python 3.13+ with type hints, `snake_case`, `PascalCase` classes
- All schema changes through `lib/db.py` SCHEMA_SQL constant
- Tool functions: `def my_tool(conn, **kwargs) -> dict`
- Generators: `def run(conn, book_ids=None) -> int`
- Agent-generated connections: `discovered_by='ai'`, start at `quality_level='speculative'`
- Distinct `linguistic` (text says) vs. `interpretive` (tradition says) labeling
- Frontend: React, JSX, 2-space indent, `camelCase` for JS, Tailwind classes

## Links

- Wiki: `docs/wiki/_index.md`
- Web API: http://localhost:8000/docs
- Frontend: http://localhost:5173
- DB: `data/processed/scripture.db`
- Run: `./run.sh web`, `./run.sh info`, `./run.sh test`
- Test: `cd frontend && npm test`
