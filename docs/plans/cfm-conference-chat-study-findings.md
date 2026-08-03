# Findings: Opt-in Chat Study — Come Follow Me + General Conference

## Discovery answers (from user, 2026-08-02)
1. **Goal**: study with chat the content of Come Follow Me + General Conference talks, as an opt-in feature.
2. **Content source**: scrape churchofjesuschrist.org.
3. **Coverage**: current-year CFM (2026, Old Testament) + recent conferences (~last 5 years).
4. **Chat behavior (custom answer)**: default OFF; when a user starts a chat they click checkboxes for the scope of what the LLM knows.
5. **Opt-in enforcement**: per-user toggle, content pre-loaded; server enforces even for API callers.

## Quality baseline (sentrux check . — 2026-08-02)
3 violations, ALL pre-existing (not caused by this plan):
- `no_god_files`: `frontend/src/App.jsx` fan-out=39
- 2 further violations in vendored `node_modules/playwright*` (noise)

## Architecture notes

### Chat (verified)
- `web/routes/chat.py` (1612 lines): DeepSeek proxy (`deepseek-v4-flash`), function-calling loop, max 15 rounds, tool results truncated to 3000 chars.
- Modes via `_CHAT_PROMPT_FILES` (`chat.py:42-46`): chat / hebrew / knowledge. Frontend never sends `mode` (server default "chat") — we add NO new mode.
- `ChatRequest` (`chat.py:1004-1011`) already has `disabled_tools: list[str]`. We add `scopes: list[str]`.
- `TOOL_DEFINITIONS` (`chat.py:63-869`): 45 tool schemas. Filter by `scope` tag before the call.
- `[Scope: ...]` system message is built client-side in `ChatPanel.jsx:1059-1090` from ToggleProvider state — the natural place to add CFM/GC scope.
- `chatStream()` in `frontend/src/api.js:291-339` sends `{messages, model, max_tokens, temperature, disabled_tools}` — add `scopes`.

### Storage (verified)
- `js_sources` corpus (`lib/db.py:403-443`) = the exact pattern: table + FTS5 virtual table + 3 sync triggers. `import_js_discourses.py` is the importer template (urllib, pdftotext fallback).
- DB: SQLite `data/processed/scripture.db`; schema in `SCHEMA_SQL` (`lib/db.py:43-726`), `init_db()` idempotent (CREATE IF NOT EXISTS) → new tables are safe on existing DBs.
- RAM cache (`web/server.py:391-490`) loads works/books/verses — NOT touched (we don't add works/verses).
- Tool registry: `lib/api/__init__.py` `register()` → instantly available as MCP tool + HTTP `/api/v1/tools/{name}`. New tools need NO web/server.py changes.

### Frontend (verified)
- `ToggleProvider.jsx`: `searchWorks` (9 works, all default ON), `enabledTools` (tool categories; `staging: false` = opt-in precedent), `LayersPopover` Search Scope section at `:270-352` with `ScopeRow` checkboxes. We add `searchScopes` (`cfm`, `conference`) default OFF.
- `settings.jsx`: `showQuickAsk` is the canonical persisted opt-in boolean; `scripture_settings` localStorage + server sync via `/api/v1/user/settings` → `user_preferences` table. We persist `searchScopes` the same way.

### Scraper feasibility (verified by live fetch 2026-08-02)
- CFM manual TOC (`/study/manual/come-follow-me-for-home-and-church-old-testament-2026?lang=eng`): server-rendered, lists all 52 weeks with date range, title, scripture block, slug (`/03` etc.).
- CFM lesson page (`/03`): title, scripture-block links, intro, "Ideas for Learning at Home and at Church", "Ideas for Teaching Children" — clean markdown-extractable. Whole-manual PDF also exists (`assets.churchofjesuschrist.org/.../2026_come_follow_me_for_home_and_church_old_testament.pdf`) as fallback.
- GC session page (`/study/general-conference/2025/04?lang=eng`): all sessions + talk titles + speakers + slugs (`/13holland`). April 2025 = 33 talks. 10 conferences ≈ 300 talks.
- venv has NO bs4/lxml/trafilatura/PyPDF2; `pdftotext` present at /usr/bin. Decision: add `beautifulsoup4` (one small dep) for HTML extraction; urllib (stdlib) for fetching, matching the js importer precedent.

## Pre-resolved decisions
- **Prose corpus, not works/verses**: CFM lessons + talks are long-form prose. `js_sources`-style tables keep them out of the verse graph (no connections/gematria/RAM-cache churn) and give FTS5 search for free. Verse refs inside lesson text stay as plain text — the LLM resolves them to real verses with existing tools.
- **ref_id schemes**: `cfm.2026.03` (year + slug) and `gc.2025.04.13holland` (year.month.slug) — stable, idempotent upserts.
- **Scope = enforcement**: server includes CFM/GC tool schemas ONLY when `ChatRequest.scopes` declares them. A raw API caller that never sends `scopes` can never call these tools. The frontend checkboxes are the only UI path; their state persists per-user via settings sync. This satisfies "default off" + "checkbox scope" + "server enforcement for API callers" with one mechanism.
- **No new chat mode**: the existing `[Scope: ...]` message + tool-schema presence/absence is enough — the LLM learns the corpora exist from the tool descriptions when in scope.
- **Copyright posture**: LDS content is freely published for non-commercial/study use; keeping the feature opt-in and out of the default public scope is the conservative choice. Content stays server-side; no redistribution beyond the existing app.

## Open questions → Resolved
- Q: CFM lessons have no verse numbers — how to store? → A: prose corpus table with `date_range` + `scripture_block` metadata; chat ties to actual verses via existing tools.
- Q: ~300 talks is a big fetch — risk? → A: polite rate limit + raw-HTML cache + idempotent upserts + `--years`/`--limit` flags make it resumable and cheap to re-run.
- Q: Does adding tables break the RAM cache / OpenAPI snapshot test? → A: no works/verses change; `tests/test_openapi_snapshot.py` may need regeneration if TOOL_DEFINITIONS schemas change (B3) — run it and update snapshot if flagged.
