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

HOST="root@40.160.241.74"
REMOTE_DIR="/var/www/scripture"

echo "=== ScriptureEngine Deployment ==="

# 1. Build frontend
echo "Building frontend..."
cd frontend
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
	rsync -avz --delete data/audio/alignments/ "$HOST:$REMOTE_DIR/data/audio/alignments/"
fi

echo "Syncing nginx + service configs..."
rsync -avz scripts/nginx-scripture.conf "$HOST:/etc/nginx/sites-available/scriptureengine"
rsync -avz scripts/scripture-api.service "$HOST:/etc/systemd/system/scripture-api.service"

# 3. Install Python dependencies on remote
echo "Installing Python dependencies..."
ssh "$HOST" "cd $REMOTE_DIR && pip install -r web/requirements.txt 2>&1 | tail -5"

# 4. Ensure nginx site is enabled + reloaded
echo "Configuring nginx..."
ssh "$HOST" "ln -sf /etc/nginx/sites-available/scriptureengine /etc/nginx/sites-enabled/ && systemctl reload nginx || systemctl restart nginx"

# 5. Ensure systemd is aware of service changes
echo "Reloading systemd..."
ssh "$HOST" "systemctl daemon-reload && systemctl enable scripture-api"

# 6. Restart API server
echo "Restarting API server..."
ssh "$HOST" "systemctl restart scripture-api"

echo "=== Done ==="
echo "Frontend: https://scriptureengine.org"
echo "API:      https://scriptureengine.org/api/v1/health"
