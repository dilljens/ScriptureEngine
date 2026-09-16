#!/bin/bash
# ScriptureEngine Deployment Script
# Builds frontend, rsyncs API + data to Hetzner CX23, restarts API server.
#
# The reverse proxy is Caddy (Docker), managed via /opt/sololedger/deploy/.
# After deploying the frontend, reload Caddy to pick up the new static files:
#   ssh ubuntu@40.160.241.74 "docker compose -f /opt/sololedger/deploy/docker-compose.yml restart caddy"
#
# Prerequisites:
#   - SSH key loaded for ubuntu@40.160.241.74
#   - VPS has /var/www/scripture/ and the systemd service
#
# Usage:
#   ./scripts/deploy.sh
#
# Fast paths (env — default behavior is unchanged):
#   SKIP_E2E=1      — skip step 5/5 Playwright suite (the long pole, ~5-15 min)
#   SKIP_BACKEND=1  — skip pytest / graph / openapi gates (backend untouched)
#   FRONTEND_ONLY=1 — both of the above, plus skip data rsync and pip install.
#                     Use when the change is frontend-only: no web/, lib/,
#                     data/, or requirements changes.
if [ "${FRONTEND_ONLY:-0}" = "1" ]; then
    SKIP_BACKEND=1
    SKIP_E2E=1
fi

set -euo pipefail

# CI/agent shells may not source the interactive fnm setup, while Playwright
# and Vite need Node. Initialize fnm non-interactively when node is absent.
if ! command -v node >/dev/null 2>&1; then
    FNM_BIN="${FNM_BIN:-$HOME/.local/share/fnm/fnm}"
    if [ -x "$FNM_BIN" ]; then
        eval "$($FNM_BIN env --shell bash)"
    fi
fi
if ! command -v node >/dev/null 2>&1; then
    echo "✗ Node.js is required for the frontend deploy gate"
    exit 1
fi

HOST="ubuntu@40.160.241.74"
REMOTE_DIR="/var/www/scripture"

echo "=== ScriptureEngine Deployment ==="

# 1. Pre-deploy validation gate
echo "=== Pre-deploy Validation ==="

echo "[1/5] Python test suite..."
if [ "${SKIP_BACKEND:-0}" = "1" ]; then
    echo "  (skipped — SKIP_BACKEND/FRONTEND_ONLY)"
else
# Skip flaky/slow tests:
#   - hebrew_fsrs_review: MEM_DB lock contention
#   - test_db_integrity: 72s full PRAGMA (redundant with step 3/5 quick_check)
#   - test_graph_tg_topic, test_graph_explore: 60-80s graph traversals (redundant with step 2/5 regression check)
PYTHON=.venv/bin/python3; [ -x "$PYTHON" ] || PYTHON=python3

echo "[0/5] Frontend build (first — a failed build must not leave the pytest"
#      gate without a dist/, and an OOM here must not cost a full test run)
# Vite builds have died with "Ineffective mark-compacts near heap limit"
# under the default V8 old-space cap while the same build passed standalone.
NODE_OPTIONS="--max-old-space-size=8192${NODE_OPTIONS:+ $NODE_OPTIONS}" \
    npm run build --prefix frontend

# The suite MUST run against the small fixture DB. conftest.py silently falls
# back to the 1.4GB production scripture.db when data/test/test.db is absent,
# which turned this gate into a 77-minute, 50GB-read crawl. Generate it if
# missing so a fresh clone / CI machine can't hit that cliff.
if [ ! -f data/test/test.db ]; then
    echo "  test fixture DB missing — building data/test/test.db"
    python3 scripts/create_test_db.py --reset
fi

# Database-backed tests share SQLite files; run serially to avoid xdist workers
# racing PRAGMA journal_mode/WAL initialization during the deploy gate.
# Slow tests (production-DB scans, minute-long traversals, sqlite_vec cases)
# are excluded via the `slow` marker in pytest.ini; only the flaky FSRS case
# still needs an explicit deselect.
$PYTHON -m pytest tests/ -q --tb=short --durations=10 \
  -m "not slow" \
  --deselect tests/test_api.py::TestHebrewRoutes::test_hebrew_fsrs_review \
  2>&1 || {
    echo "✗ Tests failed — aborting deploy"
    echo "  Tip: run .venv/bin/python -m pytest tests/ -q --tb=short to reproduce"
    exit 1
  }
fi

echo "[2/5] Graph regression check..."
if [ "${SKIP_BACKEND:-0}" = "1" ]; then
    echo "  (skipped — SKIP_BACKEND/FRONTEND_ONLY)"
else
python3 scripts/test_graph_regression.py || {
    echo "✗ Graph regression detected — aborting deploy"
    exit 1
}
fi

echo "[3/5] DB integrity check..."
sqlite3 data/processed/scripture.db "SELECT COUNT(*) FROM sqlite_master;" | grep -q "^[1-9]" || {
    echo "✗ DB quick integrity check failed — sqlite_master empty"
    exit 1
}

echo "[4/5] API contract snapshot..."
if [ "${SKIP_BACKEND:-0}" = "1" ]; then
    echo "  (skipped — SKIP_BACKEND/FRONTEND_ONLY)"
else
python3 -m pytest tests/test_openapi_snapshot.py -q --tb=short || {
    echo "✗ API contract changed — update snapshot or fix endpoints"
    exit 1
}
fi

echo "[5/5] Frontend E2E tests..."
if [ "${SKIP_E2E:-0}" = "1" ]; then
    echo "  (skipped — SKIP_E2E/FRONTEND_ONLY)"
else
cd frontend
# Playwright's webServer handles both API and Vite startup
# Run the core desktop suite, including the deterministic SSE regression.
# Serial workers + explicit retries: the API is cold-loading its RAM cache
# while early specs run; parallel workers turned first-paint timing into a
# coin-flip gate (three aborted deploys). Real breakage still fails 3x.
./node_modules/.bin/playwright test --project=chromium app.spec.ts navigation.spec.ts chat.spec.ts chat-streaming.spec.ts wiki.spec.ts --workers=1 --retries=2 --timeout=60000 || {
    echo "✗ Frontend E2E tests failed — aborting deploy"
    exit 1
}
cd ..
fi

# 2. Rsync frontend dist + API code
echo "Syncing frontend..."
rsync -avz --delete frontend/dist/ "$HOST:$REMOTE_DIR/frontend/dist/"

echo "Syncing API code..."
rsync -avz --delete \
	--exclude __pycache__ \
	--exclude '*.pyc' \
	--exclude .venv \
	web/ "$HOST:$REMOTE_DIR/web/"

echo "Syncing lib code..."
rsync -avz --delete \
	--exclude __pycache__ \
	--exclude '*.pyc' \
	lib/ "$HOST:$REMOTE_DIR/lib/"

echo "Syncing data files..."
if [ "${FRONTEND_ONLY:-0}" = "1" ]; then
    echo "  (skipped — FRONTEND_ONLY)"
else
rsync -avz --delete \
	--exclude audio \
	--exclude '*.wav' \
	--exclude '*.mp3' \
	data/ "$HOST:$REMOTE_DIR/data/"
fi

# Sync audio alignments separately (small JSON files, not the raw audio)
if [ -d data/audio/alignments ]; then
	echo "Syncing audio alignments..."
	ssh "$HOST" "mkdir -p $REMOTE_DIR/data/audio/alignments"
	rsync -avz --delete data/audio/alignments/ "$HOST:$REMOTE_DIR/data/audio/alignments/"
fi

echo "Syncing service config..."
rsync -avz scripts/scripture-api.service "$HOST:$REMOTE_DIR/scripture-api.service"
ssh "$HOST" "sudo cp $REMOTE_DIR/scripture-api.service /etc/systemd/system/scripture-api.service"

# Sync the Caddy site snippet and hot-reload ferrum-caddy (zero downtime).
# NOTE: scriptureengine.org is fronted by Caddy in Docker, NOT nginx —
# docs/deployment.md's nginx architecture section is stale. The canonical
# site config is scripts/caddy-scriptureengine.conf; the server copy lives
# at /opt/sololedger/deploy/sites/ (ro-mounted into the container).
echo "Syncing Caddy site config..."
rsync -avz scripts/caddy-scriptureengine.conf "$HOST:/opt/sololedger/deploy/sites/scriptureengine.conf"
ssh "$HOST" "docker exec ferrum-caddy caddy validate --config /etc/caddy/Caddyfile >/dev/null && docker exec ferrum-caddy caddy reload --config /etc/caddy/Caddyfile"

# 3. Install Python dependencies on remote
# Ubuntu 24.04 system Python is externally-managed (PEP 668) — the VPS runs
# the API on system python3, so --break-system-packages is required there.
echo "Installing Python dependencies..."
if [ "${FRONTEND_ONLY:-0}" = "1" ]; then
    echo "  (skipped — FRONTEND_ONLY)"
else
ssh "$HOST" "cd $REMOTE_DIR && pip install --break-system-packages -r web/requirements.txt 2>&1 | tail -5"
fi

# 4. Ensure systemd is aware of service changes
echo "Reloading systemd..."
ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl enable scripture-api"

# 5. Ensure .env exists (service requires it for DATABASE_PATH)
# DEEPSEEK_API_KEY is already set on the server separately
echo "Ensuring .env..."
ssh "$HOST" "test -f $REMOTE_DIR/.env || echo 'DATABASE_PATH=data/processed/scripture.db' | sudo tee $REMOTE_DIR/.env"

# 6. Restart API server
echo "Restarting API server..."
ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl restart scripture-api"

echo "=== Done ==="
echo "Frontend: https://scriptureengine.org"
echo "API:      https://scriptureengine.org/api/v1/health"
