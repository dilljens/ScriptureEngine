# Runbook — OpenCode Go provider pool

Operator procedures for the four-account native OpenCode Go pool that backs
general chat and the Hebrew Tutor (plan Track G, phases G2–G4).

## Architecture in one paragraph

The web process never sees a workspace key. Each of the four credentials
(`ai-secret` names `opencode-go-1` … `opencode-go-4`) is injected into its own
worker subprocess (`scripts/opencode_go_worker.py`), which exposes a
loopback Unix-socket endpoint (`/health`, `/chat/completions`). The chat API's
`ProviderRouter` (`web/lib/llm_provider.py`) round-robins healthy workers,
marks rate-limited workers with a cooldown, and fails over only before the
first streamed byte. Public surfaces report availability via
`ProviderRouter.public_summary()` — never model inventory or worker counts.

## Daily health check

```bash
# 1. Workers listening?
ss -xl | grep scriptureengine-opencode-go   # expect 4 sockets

# 2. Provider configured as seen by the API?
curl -s http://127.0.0.1:8000/api/v1/chat/instructions | jq '.data.provider'
# {"available": true}  ← public shape; anything richer is a bug (Track G3)

# 3. Contract tests green?
python3 -m pytest tests/test_llm_provider.py -q
```

## Start / stop the pool

Start under the process supervisor or a systemd service so the whole group is
managed together:

```bash
OPENCODE_GO_SOCKET_DIR=$XDG_RUNTIME_DIR/scriptureengine-opencode-go \
  scripts/start_opencode_go_workers.sh
```

Export the printed `OPENCODE_GO_WORKER_SOCKETS=...` into the web service
environment, then restart it. Stopping: stop the supervisor unit for the
workers (SIGTERM; each worker exits cleanly — covered by
`test_worker_reports_not_ready_without_credential_and_stops_on_sigterm`).

## Add / remove an account

Accounts are `ai-secret` entries named `opencode-go-N`, N = 1…4.

- **Add:** register the secret (`ai-secret add opencode-go-5` …), bump the
  loop bound in `scripts/start_opencode_go_workers.sh`, restart the pool.
- **Remove an account temporarily:** drop its socket from
  `OPENCODE_GO_WORKER_SOCKETS` and restart the web service. No key handling.
- **Rotate a workspace key:** re-set the value with `ai-secret`
  (`ai-secret rotate opencode-go-N` or equivalent), then restart only that
  worker. Keys are read at worker start; nothing is persisted elsewhere.

Never copy key values into `.env`, the repo, logs, or DB rows; never read
OpenCode's own balancer SQLite from this project.

## Disable switches (emergency)

| Goal | Action |
|---|---|
| Kill both chat modes, keep scripture lookups | set env `CHAT_DISABLED=1`, reload web service |
| Kill Hebrew Tutor only | set `HEBREW_CHAT_DISABLED=1` |
| Take the Go pool out without killing DeepSeek fallback | unset `OPENCODE_GO_WORKER_SOCKETS` + unset `OPENCODE_PROVIDER`/set `CHAT_PROVIDER=deepseek`, restart |
| Shed load per mode | lower `CHAT_RATE_LIMIT` / `HEBREW_RATE_LIMIT` (requests per 60s per IP) |

All switches are env-only — no code change needed. Verified by
`tests/test_chat_modes.py::test_emergency_disable_switch_scopes_by_mode`.

## Cooldowns & failover tuning

- Per-account cooldown after 429/network error:
  `OPENCODE_GO_ACCOUNT_COOLDOWN` seconds (default 15).
- Failover contract: retryable status codes are listed in `RETRYABLE_STATUS`;
  streaming fails over **only before the first byte**
  (`test_stream_fails_over_to_second_account_after_429`).

## Contributor-tier disclosure

The default Go model is contributor-tier. `/api/v1/chat/instructions` returns
`data_handling` text whenever the configured model id contains
"contributor"; keep that true if the model id changes.

## Known gaps (tracked in plan follow-ups)

- Live load/429 drill against real workspaces is manual; automated coverage
  uses mock transports only.
- The DeepSeek-vs-Go groundedness benchmark (plan G4) is not yet scripted.
