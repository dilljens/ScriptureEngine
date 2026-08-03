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
