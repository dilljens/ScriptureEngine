# Findings: Chat Background Jobs + Response Completeness

Status: active · Area: chat/api · Author: plan-agent · Created: 2026-08-02

## Requirements (discovery answers)

1. **Goal:** Make the scripture chat agent survive phone minimize/backgrounding (run to completion server-side, client re-joins and catches up), stop responses from being truncated mid-thought, and keep DeepSeek tool calls working through the background flow.
2. **Tracks:** A) Server-side reliable chat pipeline (response completeness + job execution). B) Client-side background-resilient chat (poll/reconnect + UX).
3. **Pre-resolved decisions (user-confirmed):**
   - Delivery: **SQLite-backed job table + lightweight polling** (~2s while visible). Not SSE-with-resume (needs sticky nginx sessions, fragile with 2 uvicorn workers) — but job events reuse the existing SSE event shapes so the client's event-processing code is unchanged.
   - Reasoning effort: **auto** — keep "let DeepSeek decide"; fix the `max_tokens` budget and detect/retry on `finish_reason="length"`. No user-facing effort control in this pass.
   - Scope: **all three failure modes** fixed in one effort (truncation, heartbeats, background jobs, frontend reconnect).
4. **Constraints:** No new dependencies (stdlib/httpx/SQLite only). Must work with existing `uvicorn --workers 2` deployment. Must not change the public SSE event shapes consumed by `api.js`. Live production DB (`/var/www/scripture/.env`) — schema must use the existing `CREATE TABLE IF NOT EXISTS` pattern.
5. **Acceptance criteria:**
   - Minimizing the phone app no longer cancels an in-flight chat — the response completes server-side and appears when the user returns ("resumed — caught up").
   - No response is silently truncated: `finish_reason="length"` is detected, surfaced, and auto-retried with a larger budget.
   - Tool calls (scripture tools) keep working across the background flow with progress visible.
   - `sentrux check .` shows no new structural violations vs. baseline (3 pre-existing).
6. **Anti-scope:** No reasoning_effort UI. No SSE live-tail (deferred). No auth overhaul. No changes to `graph.py` grading calls (30s timeout is fine). No changes to the Inklomancer project's WebSocket server.

## Diagnosis (confirmed in code)

Three distinct failure modes, all reproduced by reading `web/routes/chat.py` and `frontend/src/api.js` + `ChatPanel.jsx`:

1. **Truncation — "stops mid thought"**
   - `frontend/src/components/ChatPanel.jsx:329-343` sends `max_tokens=4096` for "short" responses. DeepSeek v4-flash has thinking mode ON by default, and **reasoning tokens count against `max_tokens`** — a 4k budget can be exhausted by CoT alone → `finish_reason="length"` → cut off before (or mid) answer.
   - **`finish_reason` is never read anywhere** in `chat.py` (checked both `/api/v1/chat` and `/api/v1/chat/stream`), so truncation is invisible and treated as a final answer.
   - Server `ChatRequest` default is also 4096 (`chat.py:1086`).
2. **Connection-coupled run — "minimize cancels"**
   - The entire tool loop + final stream lives inside one `stream_generator()` (`chat.py:1459-1674`). Mobile freeze → socket dies → `GeneratorExit` at the next `yield` → `async with _http_client.stream(...)` closes → **DeepSeek run aborted**. Nothing persists (the "save to conversation history" block at `chat.py:1676-1683` is a no-op stub).
   - No job queue, no background task, no resume. Client has zero `visibilitychange`/`pagehide` handlers and no reconnect logic (`api.js:291-392`); EOF without a terminal event = hard error ("The connection closed before the response finished").
3. **Proxy timeout — also "stops mid thought"**
   - Only ONE pre-stream heartbeat (`chat.py:1572`). A long silent thinking pause in the final call can trip Cloudflare's ~100s proxy read timeout (app is behind Cloudflare: `cf-connecting-ip` at `chat.py:1127`, 524-retry in `api.js:18-25`).

**Tool calls already work:** 15-round loop (`chat.py:1466-1563`), `reasoning_content` correctly echoed back in the assistant message (`chat.py:1500`) — no 400 risk. The failure is that the whole loop dies with the connection.

**Existing infrastructure to build on:**
- Conversation persistence with idempotency: `lib/api/conversations.py:366-398` (`client_message_id` dedup) — a natural home for server-side completion save.
- SQLite schema via `CREATE TABLE IF NOT EXISTS` blocks in `lib/db.py:45+`; pytest suite in `tests/` (`test_api.py`, `test_db_schema.py`).
- Lifespan hook in `web/server.py:56` for startup job-recovery/GC sweep.
- `done` event already carries `final_content`/`final_reasoning` (`chat.py:1659-1674`) — the client's recovery hook.
- SSE plumbing end-to-end (`chat.py:1405+`, `api.js:291+`, nginx tuned `web/nginx.conf:85-94`); heartbeat pattern proven in tool rounds (`chat.py:1472-1476`).

## Research summary (DeepSeek docs, fetched 2026-08-02)

- `max_tokens` is "the maximum number of tokens that can be generated" — **reasoning + answer share the budget** (thinking-mode guide; archived reasoner doc: "max_tokens: The maximum output length (including the COT part)"). Set too low → cut off during CoT. Max output today: 384K; context 1M. `deepseek-chat`/`deepseek-reasoner` were retired 2026-07-24 → now non-thinking/thinking modes of `deepseek-v4-flash` (thinking default ON).
- **`finish_reason="length"` is the official truncation signal** (also `insufficient_system_resource` for rare inference interruption). Streaming: final chunk carries `finish_reason`; `stream_options.include_usage: true` guarantees a usage chunk incl. `completion_tokens_details.reasoning_tokens`.
- **Tool calls:** enabled via `tools` + `tool_choice` (default `auto` when tools present). Loop = model returns `tool_calls` → execute → append `{role:"tool",tool_call_id,...}` → repeat until `tool_calls` is `None`. **Must echo `reasoning_content` back when `tools` is present** (400 otherwise) — already done at `chat.py:1500`. Validate tool `arguments` JSON server-side (already done).
- `temperature`/`top_p` are **ignored in thinking mode**; `reasoning_effort` (low/medium/high) is the speed lever — not used per user decision.
- **Mobile lifecycle (Chrome/MDN):** backgrounded page → *frozen* (timers + fetch callbacks don't run); only WebSocket/WebRTC exempt from throttling. `visibilitychange→hidden` is the last reliably observable event on mobile; `pagehide`/`unload` unreliable. **Standard fix: decouple the job from the client connection** — job runs server-side, client polls or reconnects.

## Pre-resolved decisions

- **Job store:** SQLite table `chat_jobs` (the app already runs on SQLite; survives workers + redeploys; poll reads work from any worker). Job *execution* is an in-process asyncio task in the worker that created it; *state* is persisted to SQLite so any worker can serve polls.
- **Transport:** HTTP polling (2s while visible) with events since `after_seq`. Reuses existing SSE event shapes (`thinking`/`text`/`tool_progress`/`heartbeat`/`done`/`error`) + new `truncated` event.
- **Completeness:** read `finish_reason` everywhere; floor `max_tokens` (server min 16k for thinking mode; bump ChatPanel "short" 4096→16384); auto-retry once with bigger budget on `finish_reason="length"` (both non-stream tool rounds and final stream); `stream_options.include_usage`; heartbeats every 15s during the final stream.
- **Completion save:** job takes optional `session_id` + `client_message_id`; on `done`, server saves the assistant message idempotently (best-effort; client remains the source of truth).
- **GC / recovery:** jobs expire ~1h after completion; stale `running` jobs marked `failed`/`interrupted` at startup.
- **Rate limiting:** keep the per-IP 20/60s gate on job *creation*; cap concurrent jobs per IP (e.g. 5) to prevent abuse.

## Architecture notes

### `chat_jobs` table (lib/db.py)
```
CREATE TABLE IF NOT EXISTS chat_jobs (
  id TEXT PRIMARY KEY,               -- uuid4 hex
  session_id TEXT,                   -- nullable; conversation session
  client_message_id TEXT,            -- idempotent save key
  status TEXT NOT NULL DEFAULT 'queued',  -- queued|running|streaming|done|failed|cancelled
  seq INTEGER NOT NULL DEFAULT 0,    -- last emitted event seq
  model TEXT, max_tokens INTEGER, temperature REAL,
  tool_results_json TEXT,
  usage_json TEXT,
  finish_reason TEXT,
  error TEXT,
  created_at TEXT, updated_at TEXT, expires_at TEXT
)
```
Thinking/content partials do NOT live in SQLite (too chatty to write per chunk) — they are accumulated in the in-process job record and returned in the poll response as `events since after_seq`; the client accumulates. On `done`, the full `final_content`/`final_reasoning` ARE persisted (columns `final_content TEXT, final_reasoning TEXT`) so a late poller still gets the complete answer.

### Job manager (`web/lib/jobs.py`, new)
- `JobManager` (module-level singleton): `create(body) -> job_id` (validates rate limit, inserts row, spawns `asyncio.create_task(_run(job_id))`), `get(job_id)`, `poll(job_id, after_seq)`.
- `_run(job_id)`: same pipeline as today's `stream_generator` (tool rounds → final stream) but owned by the job, writing events to an in-memory deque with seq numbers, flushing state to SQLite at phase boundaries (queued→running→streaming→done/failed), and on `done` persisting `final_content`/`final_reasoning`/`usage`/`finish_reason` (+ best-effort conversation save).
- Client disconnect is irrelevant: the task never yields to the HTTP response.
- Multi-worker: job task lives in the creating worker; poll reads are served from SQLite by any worker. On worker death, the row stays `running` until the startup sweep marks it `interrupted` (client retries). SQLite writes are per-job and serialized (single task) — no write contention.
- GC: periodic sweep (lifespan asyncio task) marks/removes expired jobs.

### Endpoints (web/routes/chat.py)
```
POST /api/v1/chat/jobs                       → 201 {job_id, seq:0, status:"queued"}
GET  /api/v1/chat/jobs/{job_id}?after_seq=N  → {status, seq, events:[...], done:{...}|null, error?}
POST /api/v1/chat/jobs/{job_id}/cancel       → {ok:true} (optional; stops the task)
```
`events` reuse the SSE shapes: `{seq, type:"thinking"|"text"|"tool_progress"|"heartbeat"|"truncated"|"done"|"error", ...}`. The `done` event carries `usage`, `cost`, `model`, `tool_results`, `final_content`, `final_reasoning`, `finish_reason`.

### Frontend (frontend/src/api.js + ChatPanel.jsx)
- `chatStream()` reimplemented internally as: POST job → poll loop (2s, only while `document.visibilityState === 'visible'`) → feed events through the SAME `processEvent` switch (signature unchanged; all callers keep working).
- Reconnect: if a poll fails (network/freeze), retry with backoff (1s→2s→5s→10s cap); on `visibilitychange→visible`, immediately poll. Job reads are idempotent — safe to repeat from any seq.
- Watchdog: if no successful poll within ~20s while visible, show "reconnecting…" and keep polling.
- Truncation: on `done` with `finish_reason==="length"` → show banner "Answer was cut off (hit output limit)" + "Continue with more room" button (re-runs the final generation with `max_tokens=128000`).
- Recovery: persist `job_id` + partial thinking/content into the existing localStorage snapshot (`ChatPanel.jsx:1758-1787`); on mount, if a job exists and isn't done, resume polling.

### Deployment
- nginx: no change required (polling is a normal GET). Cloudflare: fine.
- DB migration: `CREATE TABLE IF NOT EXISTS chat_jobs` runs at startup (existing pattern) — live DB auto-upgrades.

## Quality baseline

- `sentrux check .` → 3 violations, all pre-existing: `no_god_files` `frontend/src/App.jsx` (fan-out=39); the other 2 are node_modules noise. `web/routes/chat.py` is already a large router (1688 lines) — the job manager goes in a new `web/lib/jobs.py` to avoid growing it further.

## Repo state note

- ⚠ Working tree has **18 uncommitted paths** and `main` is **2 commits ahead of origin** (diverged). Recommend committing/stashing before implementation and confirming a clean baseline first.
- No active docket plans or other threads touching `web/routes/chat.py` (checked via docket orient/crossings).

## Open risks

- **iOS freeze + poll loop:** frozen pages don't run timers; on resume the loop must restart cleanly (visibility handler + `setInterval` re-arm). Mitigated by polling only when visible.
- **2-worker race on job reads:** safe (SQLite reads); job *execution* pinned to creating worker — if that worker dies mid-job the run is lost and the client retries (acceptable for a personal tool).
- **SQLite write load:** job state flushes are at phase boundaries, not per chunk — bounded.
- **DeepSeek `insufficient_system_resource`:** rare finish_reason; log it and surface as a retryable error.
