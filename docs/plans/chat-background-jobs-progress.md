# Progress: Chat Background Jobs + Response Completeness

## Session 2026-08-02 (planning)
- Plan created: `docs/plans/chat-background-jobs.md` (2 tracks, 7 phases)
- Findings: `docs/plans/chat-background-jobs-findings.md` (diagnosis, research, decisions, API contract)
- Decisions made (user-confirmed):
  - SQLite job table + HTTP polling (~2s while visible) — not SSE resume
  - Reasoning effort: auto (fix max_tokens budget + finish_reason detection/retry only)
  - Full 3-mode fix in one effort (truncation, heartbeats, background jobs, frontend reconnect)
- Quality baseline: `sentrux check .` → 3 violations (pre-existing: App.jsx fan-out, StudyEditor↔StudyViewer + web-route cycles, node_modules)
- Repo state warning: 18 uncommitted paths; `main` 2 ahead of origin

## Session 2026-08-03 (execution)

### Track A — Server (all 4 phases done)
- **A1 complete**: finish_reason read in both endpoints + surfaced in `done`/response; `ChatRequest` max_tokens default 4096→16384 (`MIN_THINKING_TOKENS`); one-shot retry with `_retry_budget` (min(max*4, 128k)) on `finish_reason="length"` (non-stream loop + stream regenerate-once + force-summary retry); `stream_options.include_usage`; `_heartbeat_lines` (15s idle heartbeats) during the final stream. Tests: `tests/chat_reliability_test.py` (8 pass).
- **A2 complete**: `chat_jobs` DDL — extracted to `CHAT_JOBS_SQL` constant (appended to `SCHEMA_SQL`) so the job manager can lazily create the table at runtime (the web server never runs init_db()). Schema tests in `tests/test_db_schema.py::TestChatJobsSchema` (4 pass).
- **A3 complete**: refactored the stream pipeline into shared `_chat_pipeline(body, msgs)` (dict-yielding) used by both `/chat/stream` (SSE wrapper) and the new job runner. New `web/lib/jobs.py` — `ChatJob` + `JobManager` (per-IP cap 5, events buffer with seqs, SQLite persistence batched every 2s/50 events for cross-worker poll correctness). Endpoints: `POST /api/v1/chat/jobs`, `GET /api/v1/chat/jobs/{id}?after_seq=N`, `POST /api/v1/chat/jobs/{id}/cancel`. Tests: `tests/chat_background_jobs_test.py` (7 pass).
- **A4 complete**: server-side completion save via `add_message` (idempotent, `job-{id}` key) when `session_id` provided; startup recovery (stale `running` rows → `failed` "interrupted — retry") + periodic sweeper in lifespan (`web/server.py`).
- **Server tests**: `chat_reliability` + `chat_background_jobs` + `test_db_schema` = **31 passed** (105s). `test_api.py` **hangs** on `TestMemorizeRoutes::test_memorize_queue_batch` — PRE-EXISTING (unrelated to chat; reproduce in isolation; `tests/test_api.py` unmodified in working tree).
- **Live smoke** (uvicorn + test DB + fake key): create → `{job_id, queued}` instantly; poll → `running` → `failed` with the DeepSeek auth error persisted; cancel/not-found graceful; legacy `/chat/stream` still SSE; `chat_jobs` rows (done/failed/cancelled) verified in SQLite. ✓

### Track B — Client (all 3 phases done)
- **B1 complete**: `chatStream` reimplemented as background-job + poll (2s while visible, backoff 1→10s, `visibilitychange→visible` immediate re-poll, watchdog via polling; Stop aborts + POSTs server cancel; `onTruncated` callback; done-event synthesized from `final` snapshot when incremental events were missed). Added `chatComplete` (non-streaming job wrapper). `frontend/src/api.js` parses clean.
- **B2 complete**: ChatPanel — passes `session_id`/`client_message_id`; `onTruncated` (clears partial, "regenerating" note); `finish_reason==="length"` → amber banner + "Continue with more room" (re-runs at 128k); "resumed in background — caught up" chip on foreground; `chat_pending_*` localStorage marker + `recoverPendingChat` poll (reload recovery via server-side session save); pending marker cleared on done/error/abort. `ChatPanel.jsx` parses clean.
- **B3 complete**: StudyViewer + StudyEditor Q&A routed through `chatComplete` (survives minimize, correct `deepseek-v4-flash` model — also fixes their response parsing which never matched the `/chat` envelope). Both parse clean.

### Verification
- `sentrux check .` → 3 violations, **same as baseline** (no new cycles/god files from this work).
- `python3 -c "import web.server"` OK; `vite build` running (background).
- Known pre-existing issues (NOT from this change): `test_memorize_queue_batch` hang; 18 uncommitted paths; `main` 2 ahead of origin.

## Session log (append during execution)
- (see above)
