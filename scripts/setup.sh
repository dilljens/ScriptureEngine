#!/usr/bin/env bash
# ScriptureEngine — full project setup from a fresh git clone.
# Sets up virtual environment, installs deps, and fetches the database.
#
# Usage:
#   bash scripts/setup.sh              # interactive — choose how to get DB
#   bash scripts/setup.sh --quick      # download from GitHub Release
#   bash scripts/setup.sh --from-vps   # rsync from production VPS (needs SSH key)

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== ScriptureEngine Setup ==="

# ── 1. Python virtual environment ──
echo ""
echo "[1/4] Python virtual environment..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "  Created .venv"
else
    echo "  .venv already exists"
fi

# ── 2. Python dependencies ──
echo ""
echo "[2/4] Installing Python dependencies..."
.venv/bin/pip install -q -r web/requirements.txt
.venv/bin/pip install -q biblical-transliteration
echo "  Done"

# ── 3. Frontend dependencies ──
echo ""
echo "[3/4] Installing frontend dependencies..."
if [ -d frontend/node_modules ]; then
    echo "  node_modules already exists"
else
    cd frontend && npm install --silent && cd ..
    echo "  Done"
fi

# ── 4. Database ──
echo ""
echo "[4/4] Database..."

DB_PATH="$ROOT/data/processed/scripture.db"

if [ -f "$DB_PATH" ] && [ "$(stat -c%s "$DB_PATH" 2>/dev/null || stat -f%z "$DB_PATH" 2>/dev/null)" -gt 1000000 ]; then
    echo "  ✓ Database already exists ($(du -h "$DB_PATH" | cut -f1))"
    echo "  Setup complete!"
    exit 0
fi

# Determine how to get the DB
MODE="${1:-interactive}"

if [ "$MODE" = "--from-vps" ] || [ "$MODE" = "--quick" ]; then
    FETCH_MODE="$MODE"
else
    echo ""
    echo "  How would you like to get the database?"
    echo "    1) Download from GitHub Release (~200MB compressed)"
    echo "    2) Rsync from production VPS (needs SSH key setup)"
    echo "    3) Build from source scripts (takes hours, needs external data repos)"
    read -rp "  Choose [1/2/3]: " choice
    case "$choice" in
        2) FETCH_MODE="--from-vps" ;;
        3) FETCH_MODE="--build" ;;
        *) FETCH_MODE="--quick" ;;
    esac
fi

mkdir -p "$ROOT/data/processed"

case "$FETCH_MODE" in
    --quick)
        echo "  Downloading from GitHub Release..."
        # Get the latest release asset
        RELEASE_URL=$(curl -s https://api.github.com/repos/dilljens/ScriptureEngine/releases/latest \
            | grep "browser_download_url.*scripture.db.gz" | cut -d'"' -f4)
        if [ -z "$RELEASE_URL" ]; then
            echo "  No release found. Trying VPS fallback..."
            FETCH_MODE="--from-vps"
        else
            echo "  Downloading: $RELEASE_URL"
            curl -L -o /tmp/scripture.db.gz "$RELEASE_URL"
            gunzip -c /tmp/scripture.db.gz > "$DB_PATH"
            rm /tmp/scripture.db.gz
            echo "  ✓ Database downloaded ($(du -h "$DB_PATH" | cut -f1))"
        fi
        ;;
esac

if [ "$FETCH_MODE" = "--from-vps" ]; then
    echo "  Rsyncing from production VPS (40.160.241.74)..."
    echo "  (Requires SSH key access — set up with: ssh-copy-id root@40.160.241.74)"
    rsync -e "ssh -i ~/.ssh/id_ed25519" -avz root@40.160.241.74:/var/www/scripture/scripture.db "$DB_PATH"
    echo "  ✓ Database synced ($(du -h "$DB_PATH" | cut -f1))"
fi

if [ "$FETCH_MODE" = "--build" ]; then
    echo "  Building database from source scripts..."
    echo "  This requires cloned data repos and takes significant time."
    echo "  See docs/deployment.md for instructions."
    exit 1
fi

# ── Done ──
echo ""
echo "=== Setup complete! ==="
echo "  Start the API:   .venv/bin/uvicorn web.server:app --reload --port 8000"
echo "  Start frontend:  cd frontend && npx vite dev"
echo "  Open browser:    http://localhost:5173"
