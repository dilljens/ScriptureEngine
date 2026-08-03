---
status: completed
kind: plan
area: chat/api
author: plan-agent
created: 2026-08-02
completed: 2026-08-03
---

# Project: Chat Background Jobs + Response Completeness

Goal: Chat survives phone minimize (runs to completion server-side, client re-joins and catches up), never truncates mid-thought, and keeps DeepSeek tool calls working through the background flow — via a SQLite-backed job system with polling.

## Requirements
- [x] R1: Minimizing the phone app no longer cancels an in-flight chat — the response completes server-side and appears on return ("resumed — caught up").
- [x] R2: No response is silently truncated — `finish_reason="length"` is detected, surfaced, and auto-retried with a larger budget.
- [x] R3: Tool calls (scripture tools) keep working through the background flow with progress visible.
- [x] R4: `sentrux check .` shows no new structural violations vs. baseline (3 pre-existing).

## Pre-resolved Decisions (see findings.md)
- Job store: SQLite `chat_jobs` table; transport = HTTP polling (~2s while visible) with events since `after_seq`. SSE event shapes reused unchanged.
- Reasoning effort: auto (no UI control); fix `max_tokens` budget + detect/retry on `finish_reason="length"`.
- No new dependencies; must work with `uvicorn --workers 2`; schema via `CREATE TABLE IF NOT EXISTS` (live-DB-safe).
- Client remains the source of truth for message saving; server save is best-effort idempotent.

## Track A: Server — reliable chat pipeline `[x]`
- Description: finish_reason detection, max_tokens budget fix, retry-on-length, final-stream heartbeats, `include_usage`, then the SQLite-backed job system (job manager + endpoints + completion save + GC/recovery).
- 📏 Scope: ~9 files, ~1,100 lines (4 phases below)

### Phase A1: LLM helpers + legacy endpoint hardening `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 20
- [x] Read `finish_reason` in `/api/v1/chat` (`chat.py:1187-1310` loop + final) and `/api/v1/chat/stream` (`chat.py:1485-1674`); surface it in the `done` event and in the non-stream response; log it (structured logging exists in `web/server.py:192+`).
- [x] Floor `max_tokens` for thinking mode: server `ChatRequest` default 4096 → 16384 (`chat.py:1086`); keep the 128k cap.
- [x] Auto-retry once on `finish_reason="length"`: non-stream path re-calls with `max_tokens = min(max_tokens*4, 128000)`; stream path restarts the final stream once with the bigger budget and marks `finish_reason` on the `done` event. Surface `insufficient_system_resource` as a retryable error.
- [x] Add `stream_options: {"include_usage": true}` to the stream payload (`_build_payload`/stream call) so usage + reasoning_tokens arrive reliably.
- [x] Heartbeats every 15s during the final stream (`chat.py:1570-1622`) using the same `asyncio.wait` pattern as tool rounds (`chat.py:1472-1476`) — emit heartbeat when no chunk arrived in 15s.
- [x] Add `tests/chat_reliability_test.py`: stubbed `call_deepseek` (monkeypatch) covering finish_reason=length retry (non-stream + stream) and heartbeat emission.
- 📏 Scope: `web/routes/chat.py` (~120 lines changed), `tests/chat_reliability_test.py` (new ~150). ~2 files, ~270 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_reliability_test.py -q`
- ⚙ Fallback: If DeepSeek rejects `stream_options`/retry semantics, drop auto-rerun — surface `finish_reason` in `done` only, and do the retry client-side (B2 "Continue" button).
- Depends on: nothing

### Phase A2: `chat_jobs` schema `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 10
- [x] Add `chat_jobs` table to `lib/db.py` DDL block (columns per findings.md: id, session_id, client_message_id, status, seq, model, max_tokens, temperature, tool_results_json, usage_json, finish_reason, error, final_content, final_reasoning, created_at, updated_at, expires_at). Follow existing `CREATE TABLE IF NOT EXISTS` + index conventions.
- [x] Extend `tests/test_db_schema.py` with a chat_jobs schema assertion.
- 📏 Scope: `lib/db.py` (+45), `tests/test_db_schema.py` (+15). ~2 files, ~60 lines.
- ✅ Checkpoint: `python3 -c "from lib.db import get_db; c=get_db(); assert c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='chat_jobs'\").fetchone(); print('chat_jobs ok')"`
- ⚙ Fallback: If the live DB has a conflicting table name, rename to `chat_jobs_v1`; otherwise standard CREATE IF NOT EXISTS is live-safe.
- Depends on: nothing

### Phase A3: Job manager + endpoints `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 30
- [x] New `web/lib/jobs.py`: `JobManager` singleton — `create(body)` (rate-limit + concurrent-job cap per IP, insert row, spawn `asyncio.create_task(_run)`), `get`, `poll(job_id, after_seq)`, `cancel`.
- [x] `_run(job_id)`: move the tool-loop + final-stream pipeline from `stream_generator` (`chat.py:1459-1674`) into the job task; emit seq-numbered events (`thinking`/`text`/`tool_progress`/`heartbeat`/`truncated`/`done`/`error`) into an in-memory deque; flush SQLite state at phase boundaries (queued→running→streaming→done/failed); reuse A1 helpers (finish_reason, retry, include_usage, heartbeats).
- [x] Endpoints in `chat.py`: `POST /api/v1/chat/jobs` → 201 `{job_id, seq:0, status}`, `GET /api/v1/chat/jobs/{job_id}?after_seq=N` → `{status, seq, events, done?, error?}`, `POST /api/v1/chat/jobs/{job_id}/cancel`. Keep origin check + rate limit on creation.
- [x] Keep `POST /api/v1/chat/stream` working (thin wrapper: create job, stream its buffer live) so StudyViewer/Editor and any old clients don't break; `POST /api/v1/chat` unchanged.
- [x] `tests/chat_background_jobs_test.py`: create→poll→done lifecycle with stubbed DeepSeek (stream deltas incl. finish_reason), after_seq replay, cancel, concurrent-job cap.
- 📏 Scope: `web/lib/jobs.py` (new ~200), `web/routes/chat.py` (+250), `web/server.py` (lifespan import +15), `tests/chat_background_jobs_test.py` (new ~200). ~4 files, ~665 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_background_jobs_test.py -q`
- ⚙ Fallback: If cross-worker job reads race in practice, pin polling to SQLite state only (no in-process buffering for reads) — the design already does this; escalate only if SQLite write contention appears (then serialize via a module lock).
- Depends on: A1, A2

### Phase A4: Completion save + GC + startup recovery `[x]`
- 🏷 Priority: medium
- 🔁 Max turns: 15
- [x] On `done`, if `session_id` + `client_message_id` provided, best-effort save of the assistant message via `lib/api/conversations.py:366-398` idempotent path (replaces the no-op stub at `chat.py:1676-1683`).
- [x] GC: lifespan asyncio task sweeps expired jobs (done >1h) and marks stale `running`/`queued` rows `failed` ("interrupted — retry") on startup (`web/server.py:56`).
- [x] Log per-job `finish_reason` + `reasoning_tokens` for diagnostics.
- 📏 Scope: `web/routes/chat.py` (+60), `web/lib/jobs.py` (+40), `web/server.py` (+25). ~3 files, ~125 lines.
- ✅ Checkpoint: `python3 -m pytest tests/chat_background_jobs_test.py -q && python3 -c "import web.server; print('import ok')"`
- ⚙ Fallback: If the conversation save conflicts with the client's own save, keep client save as source of truth (server save best-effort, keyed by client_message_id — already idempotent).
- Depends on: A3

## Track B: Client — background-resilient chat `[x]`
- Description: reimplement `chatStream` as job + poll with reconnect, ChatPanel visibility/resume/truncation UX, and route StudyViewer/StudyEditor through the shared job client.
- 📏 Scope: ~6 files, ~470 lines (3 phases below)

### Phase B1: Job/poll client in api.js `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 20
- [x] Add `createChatJob(messages, opts)` (POST `/api/v1/chat/jobs` → job_id) and `pollChatJob(jobId, afterSeq, opts)` (GET with `after_seq`; returns events + status).
- [x] Reimplement `chatStream(messages, opts)` (keep exact signature + callbacks: onThinking/onText/onToolProgress/onDone/onError) as: create job → poll loop every 2s **only while `document.visibilityState === 'visible'`** → feed events through the existing `processEvent` switch (preserve AbortError behavior for the Stop button via job cancel).
- [x] Reconnect/backoff: poll failure → retry 1s→2s→5s→10s cap; `visibilitychange→visible` → immediate poll. Job reads are idempotent (after_seq) so re-polls are safe.
- [x] Add `onTruncated` callback (finish_reason==="length" on done) + expose `job_id` on done for recovery.
- 📏 Scope: `frontend/src/api.js` (~180 lines changed). ~1 file, ~180 lines.
- ✅ Checkpoint: `grep -q "pollChatJob" frontend/src/api.js && grep -q "visibilityState" frontend/src/api.js && echo ok`
- ⚙ Fallback: If 2s polling feels chatty on the phone, gate polls on `document.hidden` (skip entirely while hidden) and add a 3s minimum interval.
- Depends on: Track A API contract (A3 endpoint shapes — fixed in findings.md, can be built in parallel)

### Phase B2: ChatPanel resume + truncation UX `[x]`
- 🏷 Priority: high
- 🔁 Max turns: 25
- [x] `visibilitychange` handler: on hidden → nothing (job runs server-side); on visible → re-arm the poll loop and show a "resumed — caught up" chip when the seq jumps.
- [x] Watchdog: if no successful poll for ~20s while visible → "reconnecting…" state (keep polling).
- [x] Truncation banner on `finish_reason==="length"`: "Answer was cut off (hit the output limit)" + "Continue with more room" button → re-runs final generation with `max_tokens=128000` (reuse A1 retry path or a direct follow-up job).
- [x] Persist `job_id` + streaming partials (thinking/content) into the existing localStorage snapshot (`ChatPanel.jsx:1758-1787`); on mount, if a job_id exists and isn't done, resume polling it (survives reload).
- [x] Stop button: cancel job server-side (`POST /jobs/{id}/cancel`) instead of only aborting the fetch.
- 📏 Scope: `frontend/src/components/ChatPanel.jsx` (~180 lines changed), possibly small `TruncationBanner` inline. ~1-2 files, ~200 lines.
- ✅ Checkpoint: `grep -q "visibilitychange" frontend/src/components/ChatPanel.jsx && grep -q "finish_reason" frontend/src/components/ChatPanel.jsx && echo ok`
- ⚙ Fallback: If `visibilitychange` is unreliable on iOS Safari, also resume on `focus`/`pageshow` and add a manual "Resume" affordance when a job is known-running.
- Depends on: B1

### Phase B3: StudyViewer/StudyEditor via shared job client `[x]`
- 🏷 Priority: low
- 🔁 Max turns: 10
- [x] Replace the two plain `fetch('/api/v1/chat')` call sites (`StudyViewer.jsx:108-120`, `StudyEditor.jsx:225-260`) with a shared `chatComplete()` helper wrapping the job flow (they get background survival + finish_reason retry for free); keep their non-streaming await semantics.
- [x] Add AbortController + error messaging where the swap isn't feasible.
- 📏 Scope: `frontend/src/api.js` (+30), `StudyViewer.jsx` (~15), `StudyEditor.jsx` (~15). ~3 files, ~60 lines.
- ✅ Checkpoint: `grep -q "chatComplete" frontend/src/api.js && grep -q "chatComplete" frontend/src/components/StudyViewer.jsx && echo ok`
- ⚙ Fallback: If routing study Q&A through jobs adds risk, leave them on `/chat` but add finish_reason-aware errors + abort handling.
- Depends on: B1

## Definition of Done
- All phases in both tracks checked; `python3 -m pytest tests/ -q` green (plus new tests above).
- Manual smoke on the deployed app: start a deep question → minimize phone → return → answer completed with "resumed — caught up"; force a long response to confirm no truncation banner on normal completion; `sentrux check .` = same 3 violations only.
- Update `docs/deployment.md` if any deploy steps changed (should be none — schema auto-creates).
