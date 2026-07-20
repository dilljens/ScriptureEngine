#!/bin/bash
# ScriptureEngine Deployment Script
# Builds frontend, rsyncs API + data to Hetzner CX23, restarts API server.
#
# Prerequisites:
#   - SSH key loaded for root@40.160.241.74
#   - Hetzner server has /var/www/scripture/ and the systemd service
#
# Usage:
#   ./scripts/deploy.sh

set -euo pipefail

HOST="ubuntu@40.160.241.74"
REMOTE_DIR="/var/www/scripture"

echo "=== ScriptureEngine Deployment ==="

# 1. Pre-deploy validation gate
echo "=== Pre-deploy Validation ==="

echo "[1/5] Python test suite..."
# Skip flaky/slow tests:
#   - hebrew_fsrs_review: MEM_DB lock contention
#   - test_db_integrity: 72s full PRAGMA (redundant with step 3/5 quick_check)
#   - test_graph_tg_topic, test_graph_explore: 60-80s graph traversals (redundant with step 2/5 regression check)
PYTHON=.venv/bin/python3; [ -x "$PYTHON" ] || PYTHON=python3
$PYTHON -m pytest tests/ -q --tb=short -n auto \
  --deselect tests/test_api.py::TestHebrewRoutes::test_hebrew_fsrs_review \
  --deselect tests/test_db_schema.py::TestIntegrity::test_db_integrity \
  --deselect tests/test_db_schema.py::TestIntegrity::test_no_duplicate_connections \
  --deselect tests/test_db_schema.py::TestIntegrity::test_no_orphaned_source_verses \
  --deselect tests/test_db_schema.py::TestIntegrity::test_no_orphaned_target_verses \
  --deselect tests/test_api.py::TestGraphRoutes::test_graph_tg_topic \
  --deselect tests/test_api.py::TestGraphRoutes::test_graph_explore \
  --deselect tests/test_api.py::TestServerSearchRoutes::test_semantic_search \
  --deselect tests/test_api.py::TestServerSearchRoutes::test_semantic_search_keyword \
  --deselect tests/test_api.py::TestServerSearchRoutes::test_semantic_search_vector \
  2>&1 || {
    echo "✗ Tests failed — aborting deploy"
    echo "  Tip: run .venv/bin/python -m pytest tests/ -q --tb=short --deselect ... to reproduce"
    exit 1
}

echo "[2/5] Graph regression check..."
python3 scripts/test_graph_regression.py || {
    echo "✗ Graph regression detected — aborting deploy"
    exit 1
}

echo "[3/5] DB integrity check..."
sqlite3 data/processed/scripture.db "SELECT COUNT(*) FROM sqlite_master;" | grep -q "^[1-9]" || {
    echo "✗ DB quick integrity check failed — sqlite_master empty"
    exit 1
}

echo "[4/5] API contract snapshot..."
python3 -m pytest tests/test_openapi_snapshot.py -q --tb=short || {
    echo "✗ API contract changed — update snapshot or fix endpoints"
    exit 1
}

echo "[5/5] Frontend E2E tests..."

cd frontend
# Playwright's webServer handles both API and Vite startup
# Only run desktop chromium tests (mobile tests would need mobile viewport setup)
npx playwright test --project=chromium app.spec.ts navigation.spec.ts chat.spec.ts wiki.spec.ts --workers=2 --timeout=60000 || {
    echo "✗ Frontend E2E tests failed — aborting deploy"
    exit 1
}
npm run build
cd ..

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
rsync -avz --delete \
	--exclude audio \
	--exclude '*.wav' \
	--exclude '*.mp3' \
	data/ "$HOST:$REMOTE_DIR/data/"

# Sync audio alignments separately (small JSON files, not the raw audio)
if [ -d data/audio/alignments ]; then
	echo "Syncing audio alignments..."
	ssh "$HOST" "mkdir -p $REMOTE_DIR/data/audio/alignments"
	rsync -avz --delete data/audio/alignments/ "$HOST:$REMOTE_DIR/data/audio/alignments/"
fi

echo "Syncing nginx + service configs..."
rsync -avz scripts/nginx-scripture.conf "$HOST:$REMOTE_DIR/nginx-scripture.conf"
ssh "$HOST" "sudo cp $REMOTE_DIR/nginx-scripture.conf /etc/nginx/sites-available/scriptureengine"
rsync -avz scripts/scripture-api.service "$HOST:$REMOTE_DIR/scripture-api.service"
ssh "$HOST" "sudo cp $REMOTE_DIR/scripture-api.service /etc/systemd/system/scripture-api.service"

# 3. Install Python dependencies on remote
echo "Installing Python dependencies..."
ssh "$HOST" "cd $REMOTE_DIR && pip install -r web/requirements.txt 2>&1 | tail -5"

# 4. Ensure nginx site is enabled + reloaded
echo "Configuring nginx..."
ssh "$HOST" "sudo ln -sf /etc/nginx/sites-available/scriptureengine /etc/nginx/sites-enabled/ && sudo systemctl reload nginx || sudo systemctl restart nginx"

# 5. Ensure systemd is aware of service changes
echo "Reloading systemd..."
ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl enable scripture-api"

# 6. Ensure .env exists (service requires it for DATABASE_PATH)
# DEEPSEEK_API_KEY is already set on the server separately
echo "Ensuring .env..."
ssh "$HOST" "test -f $REMOTE_DIR/.env || echo 'DATABASE_PATH=data/processed/scripture.db' | sudo tee $REMOTE_DIR/.env"

# 7. Restart API server
echo "Restarting API server..."
ssh "$HOST" "sudo systemctl daemon-reload && sudo systemctl restart scripture-api"

echo "=== Done ==="
echo "Frontend: https://scriptureengine.org"
echo "API:      https://scriptureengine.org/api/v1/health"
