# Progress: Opt-in Chat Study — Come Follow Me + General Conference

## Session 2026-08-02 (build)
- **Status: ALL TRACKS COMPLETE** (A1–A5, B1–B5, C1–C5, D1–D2) — plan ready for user review.

### What was built
- **Content**: 52 Come Follow Me 2026 lessons + 375 General Conference talks (2021–2026, 11 conferences; Oct 2026 correctly skipped — future). Stored as prose corpora in new `cfm_lessons` + `talks` tables with FTS5 (js_sources pattern), outside the verse graph.
- **Scrapers**: `lib/ingest/church_site.py` (stdlib urllib + html.parser, no new deps, raw-HTML cache, rate-limited, resumable), `scripts/import_cfm.py`, `scripts/import_conference.py`. Both idempotent.
- **Tools** (registered, MCP + HTTP + CLI): `scripture_cfm_lesson`, `scripture_conference_talk`, `scripture_cfm_search` — all scope-gated.
- **Server enforcement**: `ChatRequest.scopes` (`cfm`/`conference`, default none). `_filter_tools` in chat.py drops CFM/GC tool schemas unless opted in; a call-time scope gate also rejects them. Works for both /chat and /chat/stream.
- **Frontend opt-in**: "Study Corpora" checkboxes (Come Follow Me, Conference Talks) in the chat Search Scope popover, **default OFF**, persisted in localStorage (translitScheme pattern). `[Scope: ...]` instruction tells the LLM what's in/out of scope. Scopes sent in the chat payload.
- **Core-canon opt-out**: "Core Canon Only" toggle in Search Scope — forces dss/apoc/pseu/expanded off + greys them; the existing "ALL EXCEPT …" scope instruction enforces it. Persisted.
- **Library browsing**: "Study Collections" section in the Library (CFM + GC cards with live counts) → `CollectionView` (browse lessons by month / talks by conference+session, expand to read full text, "Study in chat" button that pre-enables the scope and opens chat). New endpoints in `web/routes/cfm.py` (collections/lessons/talks list + detail).

### Deviations from plan
- **C3 (persistence)**: used localStorage in ToggleProvider (the `translitScheme` pattern) instead of settings.jsx server-sync — keeps opt-in state with the rest of the toggle state; account-level sync deferred. Server enforcement is unaffected (scope-declaration based).

### Verification
- `tests/test_cfm.py`: 10/10 pass (tools, scope filtering, current-week default, library endpoints).
- `tests/test_openapi_snapshot.py`: regenerated to 166 paths (includes concurrent session's +3) — passes.
- DB integrity (`PRAGMA integrity_check` over prod DB): **PASSED** — new tables didn't corrupt anything.
- test_verses (5), test_search (9), test_db_schema (13 incl. integrity): pass.
- `chat_reliability_test.py`: 2 failures (`heartbeat_lines` group) — **proven pre-existing** (fail identically on baseline chat.py via git stash).
- Frontend `vite build`: clean.
- `sentrux check .`: same 3 pre-existing violations (App.jsx god file + node_modules noise) — **no new degradation**.
- CLI smoke: `tools/connections.py '{"tool": "scripture_cfm_lesson", ...}'` returns real lesson data.

### ⚠️ Concurrent work detected
The working tree contains an **uncommitted "chat background jobs" feature from another session** (web/lib/jobs.py, big chat.py refactor, +3 API routes, its own docs/plans/chat-background-jobs*.md). It overlaps chat.py + server.py. Both features coexist and pass the shared tests (its TestChatJobsSchema passed). **Do not commit indiscriminately** — separate commits per feature, or review both together. The 2 heartbeat test failures are attributable to that refactor, not this feature.

## Net file changes (this feature)
- New: lib/api/cfm.py, lib/ingest/church_site.py, web/routes/cfm.py, scripts/import_cfm.py, scripts/import_conference.py, frontend/src/components/CollectionView.jsx, tests/test_cfm.py, 3 plan docs
- Modified: lib/db.py (+schema/migration), lib/api/__init__.py (+3 tools), web/routes/chat.py (+scopes gating +3 schemas), web/server.py (+router), frontend/src/{App,ToggleProvider,ChatPanel,LibraryView,api}.js(x), CHAT_AGENTS.md, .opencode/AGENTS.md, openapi snapshot
- Data: 52 cfm_lessons + 375 talks ingested into data/processed/scripture.db

## Session 2026-08-03 (follow-up: weekly study view)
- **New**: dedicated **CFM Weekly Study view** (`frontend/src/components/CfmStudyView.jsx`) — "read the lesson, read the scriptures, ask chat":
  - Week selector (52 weeks, default = current calendar week), prev/next + dropdown
  - Full lesson text with scripture-block chips
  - "Read the Scriptures": parses the scripture_block into resolvable book+chapter lists (backend `cfm_scripture_blocks` in `lib/api/cfm.py` + `GET /api/v1/cfm/lessons/{ref_id}/scriptures`), per-chapter expandable verse reading (chapter endpoint), per-verse 💬 ask-chat, "Open in reader ↗" navigation
  - Sticky "Ask chat about this lesson" → opens chat pre-seeded with lesson context, CFM scope pre-enabled
- **Entry points**: Library CFM card → weekly study (current week); CollectionView CFM rows → "Weekly study" button per lesson; "Browse all lessons" ↔ study view.
- **Parser handles all 52 blocks**: ranges, continuation chapters ("Exodus 19–20; 24; 31–34"), bare/whole books ("Esther", "Ruth"), abbreviated ends ("Psalms 102–3"→102–103), \xa0 ("1\xa0Samuel"), holiday lessons (no scripture).
- Tests: 14/14 in test_cfm.py (incl. 3 new parser tests + scriptures endpoint); frontend build clean; real-data smoke (lesson 03 → gen.1-2/moses.2-3/abraham.4-5, chapter fetches, Esther whole-book).
- Net: +2 new files (CfmStudyView.jsx, none else) · modified api.js, LibraryView.jsx, CollectionView.jsx, App.jsx, lib/api/cfm.py, web/routes/cfm.py, tests/test_cfm.py, openapi snapshot.

## Session 2026-08-03 (follow-up 2: navigation)
- **Mobile + library directory navigation**: the mobile top bar's history arrows (←/→) were replaced with **directory navigation** — ↑ (up a level), ← (prev at current level), → (next at current level), matching the desktop header's semantics. History back/forward remains available via the More menu (🕐) and Alt+←/→.
- **LibraryView hint fixed**: stale "↑↓ zoom in/out" → "↑ up a level · ← → navigate works · Enter to open".
- **Command bar fixes** (real bugs):
  - `onCommand` was never wired to CommandInput → `/dark /font /toggle /history /structure /search` from the palette silently did nothing. Now wired to `handleSearchCommand` and `executeResult` dispatches `{type:...}` objects matching the handler contract.
  - refParser returned `type:'command'` for `/dark`//font` but consumers expect `'dark'`/`'font'` → both SearchBar and palette now classify correctly.
  - **New commands**: `/cfm` (this week's study), `/conference` (browse talks), `/collections` (browse both), `/library` — wired into the library/study/collection views.
  - Chapter-preview chips capped (max-h + scroll) + count label (Genesis 50 chapters no longer explode the list).
  - TYPE_ICONS/TYPE_COLORS for collection/library types.
- **gitignore**: `data/audio/words/` + `data/audio/letters/` (generated TTS output).
- Verified: vite build clean; refParser unit-checked (/dark→dark, /font up→font+up, /cfm→collection+cfm-study, /c autocomplete carries targets); vitest 85/94 (9 failures all in chatStream.test.js — pre-existing, committed in ae5cb3c, untouched by this work).
