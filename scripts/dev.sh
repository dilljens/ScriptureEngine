#!/bin/bash
# Start both local dev servers for Scripture Engine
# API on :5174, Frontend on :5175 (leased pool ports, owner scriptureengine)
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

echo "=== Scripture Engine Dev Servers ==="

# Start API
echo "Starting API on :5174..."
if [ -f .env ]; then source .env; fi
python3 -m uvicorn web.server:app --port 5174 --host 0.0.0.0 &
API_PID=$!
echo "  API PID: $API_PID"

# Start Frontend
echo "Starting Frontend on :5175..."
cd frontend
npx vite --port 5175 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "  API:      http://localhost:5174"
echo "  Frontend: http://localhost:5175"
echo "  Docs:     http://localhost:5174/docs"
echo ""
echo "Press Ctrl+C to stop both."
trap "kill $API_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
