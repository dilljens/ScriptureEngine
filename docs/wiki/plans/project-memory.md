# Scripture Knowledge Engine — Project Memory

> Auto-generated snapshot. Last updated: 2026-07-01

## Facts

- **Verses**: 45,254 total (23,213 Hebrew, 7,925 Greek, 14,116 English-only)
- **Works**: 6 — OT, NT, BoM, D&C, PGP, Apocrypha (254 books)
- **Connections**: 1,079,179 typed connections across 124 types in 11 layers
- **Database**: SQLite at `data/processed/scripture.db` (WAL mode, ~1.2GB)
- **Database tables**: 71+ (works, books, verses, gematria, connections, passage_guides, text_resources, etc.)
- **Text versions**: KJV=45,052 (default, full canon), LSV=31,104 (OT+NT), WEB=31,095 (OT+NT)
- **Textual Variants**: 31,077 Vulgate Latin (Clementine Vulgate)
- **Other imports**: LXX (Septuagint) from Swete 1930, STEPBible TAHOT+TAGNT, DSS variants
- **Passage Guides**: 41,645 cached in RAM
- **Entity Links**: 87 (people/places/concepts)
- **Verse Entities**: 57,395 entity-verse mappings
- **Knowledge Items**: 51,752 (quality-filtered, PaRDeS-leveled) — rebuilt 2026-07-01
- **Codebase knowledge graph**: 4,735 nodes, 11,804 edges (auto-synced via git polling)
- **Memory**: ~1.2GB at startup (sub-ms lookups), per-worker
- **LLM Model**: DeepSeek v4-flash (`deepseek-v4-flash`)
- **Context budget**: 300K tokens total, max_tokens=128K, compaction at 200K

## Tools

- **MCP/HTTP tools**: 52 registered in `lib/api/__init__.py` TOOL_REGISTRY
  - 15 study-specific tools (create, edit, export, publish, fork, import)
  - 10 graph traversal tools (path, reachable, hubs, entities, etc.)
- **MCP server**: `mcp_server.py` (stdio JSON-RPC, supports v2024-11-05 + v2025-03-26)
- **HTTP API**: `web/server.py` (FastAPI + uvicorn, port 8002)
- **Study API endpoints**: 15+ HTTP routes for studies
- **Conversation API**: 280+ sessions, full CRUD, ref extraction, connection promotion
- **Codebase knowledge graph**: 3,950 nodes, 7,752 edges (auto-synced via git polling)

## Generators & Importers

- **41 generators** in `generators/` directory (same-root, semuchin, gematria, chiasm, parallelism, temple_themes, etc.)
- **Seed scripts** in `scripts/`: barker_sod, beale_temple, heiser_council, orlov_merkabah, morales_ascent, etc.
- **13 agent-judged connection types** (prophetic_fulfillment, type_antitype, modified_quotation, wordplay, etc.)
- **Missing**: `peshitta_variant` — no Syriac Peshitta data source found
- **Knowledge domain**: 48,828 quality items from full rebuild

## Frontend

- **React 19 + Vite 6.4.3 + Tailwind 3** at `frontend/`
- **App.jsx**: ~1,220 lines
- **26 component files** in `src/components/` (ChatPanel, SearchBar, BookView, WorkView, LibraryView, ChapterView, StudyViewer, StudyEditor, MobileBottomNav, MobileMenuDrawer, ConnectionGraph, etc.)
- **Tab-based chat**: Ctrl+P opens chat as a tab, edit/resend messages, copy per-message or all
- **Universal command palette** (`/` key): `/chat`, `/search`, `/dark`, `/font`, `/toggle`, `/history`, `/structure`, plus fuzzy book search
- **fzf-style fuzzy matching**: character-level match highlighting, relevance scoring, Tab chapter preview
- **Library view**: all 6 works as color-coded cards, left/right navigation
- **Verse jump**: type any number in chapter view → scroll to verse
- **Navigation memory**: zoom up/down preserves position
- **SearchBar**: keyword highlighting, work badges, pagination, work filter, semantic toggle
- **StudyViewer/StudyEditor**: interactive study guides with LLM-powered editing
- **ToggleProvider**: work/layer toggles, Bible version (default: KJV), tool categories, display language
- **Playwright E2E tests**: 10 spec files in `frontend/e2e/`
- **Test command**: `cd frontend && npm test`

## Chat System

- **DeepSeek v4-flash** with 32 scripture tools
- **Session persistence**: 280+ saved conversations via `conversations` API
- **Bible version**: defaults to KJV (covers entire canon); user can switch to LSV/WEB
- **Scope instructions**: sent as `[Scope: ...]` — version, works, layers, language, tool filters
- **Context budget**: 300K total, compaction at 200K (strips tool traces from old messages, keeps last 15 exchanges)
- **max_tokens**: 30,000
- **Tool result limiting**: results truncated to 3,000 chars, stored truncated in metadata
- **Copy/edit**: copy per-message, copy all, edit user messages and resend

## Study Feature (v1.1 — 2026-06-22)

- **Study JSON format**: `scripture-study-v1` — steps with full graph paths (layer, type, strength, confidence, source/target texts), author chain, fork attribution
- **Publish flow**: Create study → publish → immutable snapshot with slug URL → `/study/torah-in-all-scripture`
- **Fork flow**: Fork any published study → get editable copy with `forked_from` chain → publish your own version
- **Export formats**: JSON (canonical), self-contained HTML, Markdown
- **Interactive StudyViewer tab**: Expand/collapse steps, clickable verse refs → VersePreviewCard popups, graph path display color-coded by layer, layer filter toggles, branching choices
- **LLM-powered StudyEditor**: LLM proposes changes via `<study-action>` JSON blocks. Supported actions: add_step, remove_step, update_step, reorder, set_title, set_description. User reviews and applies each change.
- **Settings toggle**: `showQuickAsk` — inline LLM bar in study tabs (default: off)
- **URL sharing**: `?study=slug` query param opens study tab on page load

## Layers

| Layer | Connections | Types | Notes |
|-------|-----------|-------|-------|
| numerical | 275,415 | 8 | Gematria generators |
| linguistic | 268,816 | 9 | Same-root + lemma produce 250K+ |
| intertextual | 240,450 | 9 | Quotation + allusion generators |
| structural | 71,764 | 16 | Parallelism types + chiasms |
| frequency | 65,902 | 11 | Frequency + hapax/dislegomenon |
| textual | **60,161** | **8** | Vulgate variants (31K) + other text-critical |
| sod | 26,465 | 30 | Temple theology + Merkabah + Barker |
| chronological | 24,321 | 8 | Genealogical + feast connections |
| symbolic | 23,424 | 11 | Shared symbols + apocalyptic + temple symbols |
| geographic | 14,265 | 8 | Same-location + journey paths |
| interpretive | 8,196 | 9 | Giliadi patterns + patristic readings |

## Quality Distribution

| Quality Level | Count |
|---------------|-------|
| pattern | 643,401 |
| suggested | 384,007 |
| verified | 51,752 |
| scholarly | 19 |

## Deployment

- **Production**: VPS (40.160.241.74), 4GB RAM, 2 vCPUs
- **Domains**: `scriptureengine.org` (FastAPI + React), `inklomancer.com` (WebSocket game), `api.daglock.com`
- **API**: 2 uvicorn workers with RAM cache, served via nginx with Let's Encrypt SSL
- **Chat**: DeepSeek v4-flash via API, DEEPSEEK_API_KEY in `/var/www/scripture/.env`
- **Deploy script**: `scripts/deploy.sh` — builds frontend, rsyncs code + configs, restarts services
- **SSL**: Let's Encrypt via certbot for both `.org` and `.com` domains

## Conventions

- Python 3.14+ with type hints, `snake_case`, `PascalCase` classes
- All schema changes through `lib/db.py` SCHEMA_SQL constant
- Tool functions: `def my_tool(conn, **kwargs) -> dict`
- Generators: `def run(conn, book_ids=None) -> int`
- Agent-generated connections: `discovered_by='ai'`, start at `quality_level='speculative'`
- Distinct `linguistic` (text says) vs. `interpretive` (tradition says) labeling
- Frontend: React, JSX, 2-space indent, `camelCase` for JS, Tailwind classes
- Bible version: KJV is default (full canon); user can switch in ToggleProvider

## Links

- Wiki: `docs/wiki/_index.md`
- Production: https://scriptureengine.org
- Web API: http://localhost:8002/docs
- Frontend: http://localhost:5176 (dev) / https://scriptureengine.org (prod)
- DB: `data/processed/scripture.db`
- Run: `./run.sh web`, `./run.sh info`, `./run.sh test`
- Deploy: `./scripts/deploy.sh`
- Test: `cd frontend && npm test`
