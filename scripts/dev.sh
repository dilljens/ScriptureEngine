#!/bin/bash
# Start both local dev servers for Scripture Engine
# API on :8002, Frontend on :5176
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

echo "=== Scripture Engine Dev Servers ==="

# Start API
echo "Starting API on :8002..."
if [ -f .env ]; then source .env; fi
python3 -m uvicorn web.server:app --port 8002 --host 0.0.0.0 &
API_PID=$!
echo "  API PID: $API_PID"

# Start Frontend
echo "Starting Frontend on :5176..."
cd frontend
npx vite --port 5176 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "  API:      http://localhost:8002"
echo "  Frontend: http://localhost:5176"
echo "  Docs:     http://localhost:8002/docs"
echo ""
echo "Press Ctrl+C to stop both."
trap "kill $API_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
