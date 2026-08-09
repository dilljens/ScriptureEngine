# Progress: Chat Speedup + UX + Cross-Granularity Connections

## Session 2026-08-08 — executed (build mode)
All tracks from chat-speedup.md + chat-ux-polish work completed in one pass.

## Completed
- **[A1] Real parallel tool execution** — sync DB tools run via `asyncio.to_thread`
  with per-call connections in BOTH tool loops (`web/routes/chat.py`); staging
  writes stay serialized. The old `asyncio.gather` over sync `call_tool` was fake
  parallelism (blocked the loop, ran serially). Verified by wall-clock test:
  3×250ms tools complete in <0.6s.
- **[A2] Tool-result cache** — new `lib/chat_cache.py`: in-memory TTL dict keyed
  by sha256(name+args), whitelist of 11 deterministic tools, errors never cached.
  Streaming-tool-rounds folded into the subagent pipeline (workers emit
  tool_progress chips), so the separate stream-mode tool rounds were not needed.
- **Prompt cleanup** — `CHAT_AGENTS.md`: removed "Teach the User to Fish" section,
  Rule 4 tool-narration, Study Flow step 6; strengthened Rule 6; removed
  QUIZ/HEBREW_QUIZ cards from chat mode; kept %%%HEBREW + %%%CLICK.
- **Cross-granularity connections** — the big one:
  - Registered 21 passage types in `lib/connections/types.py` LAYERS.
  - `lib/api/passage.py`: `derive_granularity()` (verse|chunk|chapter|book),
    `split_embedded_range()` fixes the chiastic_promoter `--` data bug; all
    passage rows now carry a `granularity` label.
  - `lib/api/graph.py`: passage edges wired into `graph_reachable` (chapter/chunk/
    book anchors surface at depth+1) and `graph_path` (fast `_passage_bridged_path`
    — 2/3-hop mixed paths through chapter↔book edges, ~0.1s). Book-indexed +
    TTL-cached passage loading.
  - `lib/db.py`: `granularity` column + idempotent migration.
  - Chat agent got 3 new tools: `scripture_passage_connections`,
    `scripture_chapter_connections`, `scripture_book_connections`.
- **Subagent pipeline** — new `web/lib/subagents.py`: `should_plan` heuristic,
  planner call (fast `deepseek-chat`), ≤3 concurrent workers (focused prompts +
  tool slices + threaded tools + per-worker timeout/failure isolation), synthesis
  message builder. `_chat_pipeline` fans out for research-shaped questions and
  falls back to the sequential loop otherwise. Shared `_stream_final_response`
  helper extracted (used by both paths).
- **Track D tools** — `scripture_batch_lookup` (registered tool, one call for many
  verses) + `scripture_research_parallel` (worker pool as a sync tool call).
- **UX** — blockquote → soft indigo cards (ChatPanel + scripture-markdown); mobile
  type scale 15px/14px; **one-tap verse expansion** inline under the message
  (VersePreviewCard, scrollable, collapse button) replacing the 85vh VersePopup.

## Verification
- Tests: 383 passed, 1 skipped (full suite incl. 4 new test files:
  chat_speedup, passage_granularity, subagents, track_d).
- `sentrux check .`: 3 pre-existing violations (unchanged; App.jsx god-file).
- Frontend: `npm run build` clean.

## Net file changes (this work)
- New: `lib/chat_cache.py`, `web/lib/subagents.py`,
  `tests/{chat_speedup,passage_granularity,subagents,track_d}_test.py`
- Modified: `web/routes/chat.py` (+~300), `lib/api/graph.py`, `lib/api/passage.py`,
  `lib/api/verse.py`, `lib/api/__init__.py`, `lib/connections/types.py`, `lib/db.py`,
  `CHAT_AGENTS.md`, `frontend/src/components/ChatPanel.jsx`,
  `frontend/src/lib/scripture-markdown.jsx`
- NOTE: the working tree also contains OTHER pre-existing uncommitted changes
  (materialized views, hebrew, ingest, temporal, graph.py routes) — NOT mine;
  do not commit them together.

## Known costs / follow-ups
- `graph_reachable` passage expansion: 2-4s per call (threaded, acceptable for an
  analytical tool). `graph_path` direct BFS can take ~15-20s for very dense
  neighborhoods (pre-existing `lib/connections/graph.py` behavior — untouched).
- Streaming tool rounds (A2 second half) deliberately not built — subagent workers
  provide the progress UX; revisit only if thinking-only rounds feel silent.
