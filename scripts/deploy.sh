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
python3 -m pytest tests/ -q --tb=short || {
    echo "✗ Tests failed — aborting deploy"
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
npx playwright test --project=chromium app.spec.ts navigation.spec.ts chat.spec.ts wiki.spec.ts --workers=1 --timeout=60000 || {
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

# 6. Restart API server
echo "Restarting API server..."
ssh "$HOST" "sudo systemctl restart scripture-api"

echo "=== Done ==="
echo "Frontend: https://scriptureengine.org"
echo "API:      https://scriptureengine.org/api/v1/health"
