---
status: active
kind: plan
area: chat-study
author: dillon
created: 2026-08-02
---

# Opt-in Chat Study: Come Follow Me + General Conference

**Goal:** Let users study LDS **Come Follow Me** weekly lessons and **General Conference** talks *with the chat LLM* — as an **opt-in** feature. Default OFF: the LLM knows nothing about these corpora until the user checks scope boxes when chatting.

## Requirements
- [x] R1: Come Follow Me 2026 (Old Testament) weekly lessons ingested (52 lessons + intro/thoughts pages)
- [x] R2: General Conference talks, last ~5 years (2021–2026, ~300 talks), ingested
- [x] R3: Content stored as searchable prose corpus (FTS5), NOT in the verses/works graph
- [x] R4: Chat gains 3 tools: `scripture_cfm_lesson`, `scripture_conference_talk`, `scripture_cfm_search`
- [x] R5: **Opt-in by default**: scope checkboxes in the chat Search Scope popover, unchecked by default
- [x] R6: **Server enforcement**: CFM/conference tool schemas are absent from the LLM's tool list unless the request declares the scope (`ChatRequest.scopes`) — even for raw API callers
- [x] R7: Per-user persistence of the opt-in state (existing settings sync → `user_preferences`)
- [x] R8: Default canon chat behavior unchanged when opt-in is off
- [x] R9: **Core-canon-only opt-out** — one toggle that excludes everything outside OT/NT/BoM/D&C/PGP (dss, apoc, pseu, expanded) from the chat scope; persisted per user; server-enforced via the same scopes/works mechanism
- [x] R10: **Library browsing** — the Library gains a "Study Collections" section (Come Follow Me, General Conference) with a browse view: list lessons by month / talks by conference, read full text inline, and jump into chat study

## Pre-resolved Decisions
- **Storage**: two new tables `cfm_lessons` + `talks`, mirroring the proven `js_sources` corpus pattern (`lib/db.py:403-443`) — FTS5 virtual tables + sync triggers. NOT a new `works` row: lessons/talks are prose, not verses; avoids RAM-cache and ref-scheme changes.
  - `cfm_lessons`: `ref_id` PK (`cfm.2026.03`), `year`, `week_slug`, `date_range` ("January 12–18"), `title`, `scripture_block` ("Genesis 1–2; Moses 2–3; Abraham 4–5"), `text`, `metadata`
  - `talks`: `ref_id` PK (slug, `gc.2025.04.13holland`), `year`, `month`, `session` ("Saturday Morning"), `speaker`, `title`, `date`, `text`, `metadata`
- **Scraper**: stdlib `urllib.request` (matches `scripts/import_js_discourses.py` precedent) + one new small dep `beautifulsoup4` for robust HTML extraction (site is server-rendered — verified extractable). `pdftotext` (already a system dep) as fallback. Polite rate limit, retry w/ backoff, raw-HTML disk cache, idempotent upserts, resumable.
- **Chat gating**: add `scopes: list[str] = []` to `ChatRequest` (`web/routes/chat.py`). Filter `TOOL_DEFINITIONS` — CFM/conference schemas only included when `"cfm"` / `"conference"` in `scopes`. No new chat `mode` needed; the existing `[Scope: ...]` system message (`ChatPanel.jsx:1060-1090`) carries the instruction.
- **Frontend**: new `searchScopes` state in `ToggleProvider.jsx` (`{cfm: false, conference: false}`), two checkboxes in the Search Scope popover ("Study Corpora" section), default OFF. Persisted in `settings.jsx` (mirrors `showQuickAsk`) → server-synced per user.
- **Core-canon opt-out**: `coreCanonOnly` boolean in `ToggleProvider` (default false). When on, forces `dss/apoc/pseu/expanded` off + greys their rows; the existing "ALL EXCEPT …" scope instruction enforces it; server sees the same unchecked works. Persisted via the ToggleProvider localStorage pattern (like `translitScheme`).
- **Library browsing**: CFM/GC are prose, not works — the Library's work grid stays verse-only. New "Study Collections" section with dedicated `CollectionView` browse UI + list endpoints (`GET /api/v1/cfm/lessons`, `/api/v1/conference/talks` + item endpoints) in a new `web/routes/cfm.py` router.
- **Error handling**: tools return `{"ok": False, "error": ...}` style (registry convention) on empty results; chat loop already handles tool errors.
- **Testing**: pytest, temp-DB fixtures (`tests/conftest.py`); new `tests/test_cfm.py`.

## Track A: Content Ingestion & Storage
- Description: schema + shared fetcher + two importers + the actual ingest run.
- 📏 Scope: ~5 files, ~500 lines

### Phase A1: DB schema — cfm_lessons + talks tables with FTS5
- 🏷 Priority: high
- [x] Add `cfm_lessons`, `talks` tables + FTS5 virtual tables + sync triggers to `SCHEMA_SQL` in `lib/db.py` (copy `js_sources` shape at `lib/db.py:403-443`)
- [x] Verify `init_db()` is idempotent on an existing DB (CREATE IF NOT EXISTS covers new tables)
- 📏 Scope: 1 file, ~70 lines
- ✅ Checkpoint: `.venv/bin/python -c "import sqlite3;c=sqlite3.connect('data/processed/scripture.db');print(sorted(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name IN ('cfm_lessons','talks','cfm_lessons_fts','talks_fts')\")))"` shows all 4
- ⚙ Fallback: if FTS triggers conflict with existing schema, use external-content FTS with a manual rebuild step (like `scripts/build_fts_index.py`)
- Depends on: nothing

### Phase A2: Shared church-site fetcher `lib/ingest/church_site.py`
- 🏷 Priority: high
- [x] `fetch(url)` — urllib with User-Agent, ~1s delay, retry w/ backoff, raw-HTML cache under `data/raw/church_site/`
- [x] `extract_article(html)` — beautifulsoup4: pull title + article body text; strip nav/footer/images
- [x] `slugs_from_toc(toc_html, base_path)` — helper to parse the TOC pages (verified structure: CFM weeks + GC sessions/talks)
- 📏 Scope: 1 new file, ~120 lines
- ✅ Checkpoint: `.venv/bin/python -c "from lib.ingest.church_site import fetch,extract_article; h=fetch('https://www.churchofjesuschrist.org/study/manual/come-follow-me-for-home-and-church-old-testament-2026/03?lang=eng'); t=extract_article(h); print(len(t), 'Genesis 1' in t)"` prints length>500 and True
- ⚙ Fallback: if bs4 unavailable/unwanted, fall back to a stdlib `html.parser` subclass; if the page yields no text, try the manual PDF (`assets.churchofjesuschrist.org/.../2026_come_follow_me_for_home_and_church_old_testament.pdf`) via `pdftotext`
- Depends on: A1 (not strictly — can build in parallel)

### Phase A3: CFM importer `scripts/import_cfm.py`
- 🏷 Priority: high
- [x] Fetch manual TOC (`/study/manual/come-follow-me-for-home-and-church-old-testament-2026?lang=eng`) → parse 52 lesson slugs + date range + title + scripture block
- [x] Fetch each lesson page → extract body text → upsert into `cfm_lessons` (idempotent by `ref_id`)
- [x] `--dry-run` flag (print plan only) and `--limit N` for testing; skip `-thoughts`/appendix pages unless `--include-extras`
- 📏 Scope: 1 new file, ~150 lines
- ✅ Checkpoint: `.venv/bin/python scripts/import_cfm.py --dry-run` lists ~52 lessons with scripture blocks; after a `--limit 2` run, the A1 checkpoint query shows 2 rows with `length(text) > 500`
- ⚙ Fallback: if per-week pages fail en masse, parse the single manual PDF (found in lesson pages) and split on the date-range headings
- Depends on: A2

### Phase A4: Conference importer `scripts/import_conference.py`
- 🏷 Priority: high
- [x] Iterate conferences 2021.04 → 2026.04 (10 conferences): fetch session page (`/study/general-conference/{YYYY}/{MM}?lang=eng`) → parse sessions + talk slugs + speaker + title
- [x] Fetch each talk page (`/study/general-conference/{YYYY}/{MM}/{slug}?lang=eng`) → extract body → upsert into `talks` (idempotent by `ref_id`)
- [x] `--years` flag (default `2021-2026`), `--limit` for testing, skip the sustaining/auditing reports (`11oaks`, `12larson` pattern) unless `--include-reports`
- 📏 Scope: 1 new file, ~150 lines
- ✅ Checkpoint: `.venv/bin/python scripts/import_conference.py --years 2025 --limit 3` inserts 3 talks; count query for `talks` grows by 3
- ⚙ Fallback: if the session-page parse drifts, fall back to per-session pages (`/study/general-conference/2025/04/saturday-morning-session?lang=eng`)
- Depends on: A2

### Phase A5: Full ingest run + verification
- 🏷 Priority: medium
- [x] Run `import_cfm.py` (full) + `import_conference.py` (full, 2021–2026)
- [x] Verify counts + text quality; rebuild FTS if needed
- 📏 Scope: 0 code files (ops), runtime
- ✅ Checkpoint: `.venv/bin/python -c "import sqlite3;c=sqlite3.connect('data/processed/scripture.db');print(c.execute('SELECT (SELECT count(*) FROM cfm_lessons),(SELECT count(*) FROM talks),(SELECT min(length(text)) FROM cfm_lessons),(SELECT min(length(text)) FROM talks)').fetchone())"` → ≥52 lessons, ≥250 talks, min text length > 500
- ⚙ Fallback: if rate-limited, run in chunks (`--years`/`--limit`) across sessions; the raw-HTML cache + idempotent upserts make re-runs cheap
- Depends on: A3, A4

## Track B: Backend Tools + Chat Gating
- Description: the 3 tools + registry + scopes-based schema filtering in the chat proxy.
- 📏 Scope: ~4 files, ~420 lines

### Phase B1: `lib/api/cfm.py` — tool functions
- 🏷 Priority: high
- [x] `cfm_lesson(conn, year, week)` → lesson row (title, date_range, scripture_block, text); default = current calendar week
- [x] `conference_talk(conn, year, month, session, speaker, title)` → talk row; fuzzy match on speaker/title when partial args given
- [x] `cfm_search(conn, query, corpus, year, limit)` → FTS5 MATCH across `cfm_lessons_fts` / `talks_fts`, ranked, with snippet
- [x] Follow registry convention: `(conn, **args)`, plain dict return, docstring = tool description
- 📏 Scope: 1 new file, ~200 lines
- ✅ Checkpoint: `.venv/bin/python -c "from lib.api.cfm import cfm_lesson; from lib.db import get_db; r=cfm_lesson(get_db(), year=2026, week='03'); print(r.get('title','')[:60])"` prints "January 12–18…" (needs A5 data; with `--limit 2` CFM data at minimum)
- ⚙ Fallback: if FTS5 MATCH syntax is finicky, fall back to LIKE-based search (small corpus)
- Depends on: A1 (tables must exist)

### Phase B2: Register tools in `lib/api/__init__.py`
- 🏷 Priority: high
- [x] Import + register `cfm_lesson`, `conference_talk`, `cfm_search` in `TOOL_REGISTRY` (auto-exposes as MCP + HTTP `/api/v1/tools/...`)
- 📏 Scope: 1 file, +3 lines
- ✅ Checkpoint: `.venv/bin/python -c "from lib.api import TOOL_REGISTRY; print(all(k in TOOL_REGISTRY for k in ('scripture_cfm_lesson','scripture_conference_talk','scripture_cfm_search')))"` prints True
- ⚙ Fallback: n/a (trivial)
- Depends on: B1

### Phase B3: chat.py — schemas + `scopes` gating
- 🏷 Priority: high
- [x] Add 3 schemas to `TOOL_DEFINITIONS` (`web/routes/chat.py:63-869`) tagged with a `scope` field (`"cfm"` / `"conference"`)
- [x] Add `scopes: list[str] = []` to `ChatRequest` (allowed: `cfm`, `conference`)
- [x] Filter `TOOL_DEFINITIONS` before the LLM call: drop schemas whose `scope` isn't in `request.scopes` (both `/chat` and `/chat/stream`)
- [x] Ensure `scripture_search` works enum stays canon-only (unchanged)
- 📏 Scope: 1 file, ~80 lines
- ✅ Checkpoint: `.venv/bin/python -m pytest tests/test_cfm.py::test_chat_scope_filtering -q` passes (assert: `scopes=[]` → no CFM schemas; `scopes=["cfm","conference"]` → all 3 present)
- ⚙ Fallback: if filtering TOOL_DEFINITIONS is invasive, instead gate via `disabled_tools` defaulting on the CFM tools and let the frontend clear them (weaker — server still enforces via scopes field check in `call_tool`)
- Depends on: B2

### Phase B4: Unit tests `tests/test_cfm.py`
- 🏷 Priority: medium
- [x] Tool tests against temp DB (seed 2 fake lessons + 2 talks in fixture)
- [x] Scope-filtering test (B3 contract)
- [x] Current-week default logic test
- 📏 Scope: 1 new file, ~120 lines
- ✅ Checkpoint: `.venv/bin/python -m pytest tests/test_cfm.py -q` → all pass
- ⚙ Fallback: n/a
- Depends on: B1, B3

### Phase B5: Library list endpoints `web/routes/cfm.py`
- 🏷 Priority: high
- [x] `GET /api/v1/cfm/lessons?year=` → lesson list (ref_id, date_range, title, scripture_block, month)
- [x] `GET /api/v1/cfm/lessons/{ref_id}` → full lesson
- [x] `GET /api/v1/conference/talks?year=&month=` → talk list (title, speaker, session)
- [x] `GET /api/v1/conference/talks/{ref_id}` → full talk
- [x] `GET /api/v1/cfm/collections` → counts/years for the library cards
- [x] Register router in `web/server.py` (`app.include_router`)
- 📏 Scope: 1 new file + 1 line, ~130 lines
- ✅ Checkpoint: `.venv/bin/python -m pytest tests/test_openapi_snapshot.py -q` passes (regenerate snapshot if route list changed) or curl the list endpoint against a seeded temp DB
- ⚙ Fallback: if the OpenAPI snapshot test fights back, regenerate the snapshot with the project's regen script and commit both
- Depends on: A1 (tables exist)

## Track C: Frontend Opt-in Scope UI
- Description: the two scope checkboxes (default OFF) + wiring into the chat payload + per-user persistence.
- 📏 Scope: 4 files, ~55 lines

### Phase C1: `searchScopes` state + checkboxes in Search Scope popover
- 🏷 Priority: high
- [x] `ToggleProvider.jsx`: add `searchScopes` state `{cfm: false, conference: false}` + setter to context; export from provider
- [x] New "Study Corpora" section in `LayersPopover` Search Scope (`:270-352`) with two `ScopeRow`s: "Come Follow Me" (`cfm`), "Conference Talks" (`conference`) — default OFF (unlike works which default ON)
- 📏 Scope: 2 files, ~25 lines
- ✅ Checkpoint: `grep -n "searchScopes" frontend/src/components/ToggleProvider.jsx | wc -l` ≥ 4 (state, setter, provider value, popover rows)
- ⚙ Fallback: if the popover is too crowded, put the two checkboxes in a new "Corpora" section above Tools instead
- Depends on: nothing (contract fixed by B3's `scopes` field + tool names)

### Phase C2: Wire scopes into the chat request
- 🏷 Priority: high
- [x] `frontend/src/api.js` `chatStream()`: accept `scopes = []` in opts, add to JSON body
- [x] `ChatPanel.jsx` `sendMessage()`: append `[Scope: ...]` instruction when `searchScopes.cfm`/`.conference` on; pass enabled scopes to `chatStream`
- 📏 Scope: 2 files, ~20 lines
- ✅ Checkpoint: `grep -n "scopes" frontend/src/api.js frontend/src/components/ChatPanel.jsx | wc -l` ≥ 4
- ⚙ Fallback: n/a
- Depends on: C1 (and B3 contract)

### Phase C3: Per-user persistence
- 🏷 Priority: medium
- [x] `settings.jsx`: add `searchScopes` (or `cfmScopes`) to default settings blob (default `{cfm: false, conference: false}`) → auto localStorage + server-sync via existing `syncSettingsToServer`
- [x] Hydrate `ToggleProvider` initial state from saved settings on mount
- 📏 Scope: 2 files, ~10 lines
- ✅ Checkpoint: toggle a scope → reload page → state persists (localStorage `scripture_settings` contains it)
- ⚙ Fallback: if hydration conflicts with ToggleProvider's in-memory init, read settings lazily in the popover instead
- Depends on: C1

### Phase C4: Core-canon-only opt-out
- 🏷 Priority: high
- [x] `ToggleProvider.jsx`: `coreCanonOnly` state (default false) + `applyCoreCanonOnly(on)` — on: set `dss/apoc/pseu/expanded` false; off: restore true
- [x] Search Scope popover: "Core Canon Only" toggle above the Works list; grey/disable non-canon `ScopeRow`s while on
- [x] localStorage persistence (same pattern as `translitScheme`) so the opt-out sticks per user
- 📏 Scope: 2 files, ~25 lines
- ✅ Checkpoint: toggle ON → the 4 non-canon rows render disabled + the chat payload's `disabled` works list includes DSS/APOC/PSEU/EXPANDED (grep ChatPanel scope build)
- ⚙ Fallback: if row-greying is fiddly, keep rows active but always re-assert the exclusion in the scope instruction
- Depends on: C1 (scope plumbing)

### Phase C5: Library browsing — Study Collections + CollectionView
- 🏷 Priority: high
- [x] `LibraryView.jsx`: "Study Collections" section with two cards (Come Follow Me, General Conference); `onOpenCollection(collectionId)` prop
- [x] New `CollectionView.jsx`: fetch list (B5 endpoints), group CFM by month / GC by year+session, expandable items with full text
- [x] "Study in chat" button per item → opens chat with an initial message referencing the lesson/talk
- [x] `App.jsx`: `collection` state; render `CollectionView` when a collection card is clicked (back button returns to library)
- 📏 Scope: 3 files, ~180 lines
- ✅ Checkpoint: from the Library, click "Come Follow Me" → month-grouped lesson list renders from the seeded DB; clicking a lesson shows its text
- ⚙ Fallback: if CollectionView gets complex, ship a minimal flat list + inline expand first, add grouping later
- Depends on: B5 (endpoints)

## Track D: Docs + End-to-End Verification
- Description: surface the feature in docs, then prove the whole thing works.
- 📏 Scope: ~3 files, ~30 lines

### Phase D1: Docs updates
- 🏷 Priority: low
- [x] `CHAT_AGENTS.md`: short note that CFM/GC corpora exist and are only in scope when the user enables the scope checkboxes
- [x] `.opencode/AGENTS.md` quick-ref: add the 3 tools to the tools list
- 📏 Scope: 2 files, ~20 lines
- ✅ Checkpoint: `grep -n "scripture_cfm" .opencode/AGENTS.md CHAT_AGENTS.md` matches
- ⚙ Fallback: n/a
- Depends on: B2, C1

### Phase D2: End-to-end verification
- 🏷 Priority: high
- [x] Full pytest suite green
- [x] `sentrux check .` — no NEW violations vs baseline (3 pre-existing)
- [x] Manual smoke: chat with CFM scope off → LLM never references CFM; scope on → `scripture_cfm_lesson` gets called and quotes the lesson
- 📏 Scope: 0 code files
- ✅ Checkpoint: `.venv/bin/python -m pytest -q 2>&1 | tail -3 && sentrux check . 2>&1 | tail -3`
- ⚙ Fallback: if a test unrelated to this plan fails, confirm it fails on `main` too and note it in progress.md
- Depends on: all tracks

## Out of Scope (anti-scope)
- No new `works`/`books`/`verses` rows — CFM/GC live outside the verse graph (no connections, no gematria, no RAM-cache changes)
- No changes to `scripture_search` works enum
- No auto "this week's lesson" UI beyond the tool defaulting to the current week
- No scraping of older CFM years (2019–2025) or full talk archives (1971+) — importer flags make that a later extension
- No study-guide auto-creation from lessons/talks (chat can already build guides via existing tools if the user asks)
