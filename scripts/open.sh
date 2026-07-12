#!/usr/bin/env bash
# ScriptureEngine — start both dev servers (if not already open)
# Usage: ./scripts/open.sh
#
# API_PORT and FE_PORT can be overridden via env vars.

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${SCRIPTURE_API_PORT:-8002}"
FE_PORT="${SCRIPTURE_FE_PORT:-5173}"
API_PID_FILE="/tmp/scripture-dev-api.pid"
FE_PID_FILE="/tmp/scripture-dev-fe.pid"
API_LOG="/tmp/scripture-dev-api.log"
FE_LOG="/tmp/scripture-dev-fe.log"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'
info()  { echo -e "${BLUE}ℹ${NC} $1"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠${NC} $1"; }

port_in_use() {
  ss -tlnp "sport = :$1" 2>/dev/null | grep -q "LISTEN.*:$1"
}

# ── Start API ──

if port_in_use "$API_PORT"; then
  pid=$(ss -tlnp "sport = :$API_PORT" 2>/dev/null | grep "LISTEN" | grep -oP 'pid=\K[0-9]+' | head -1)
  warn "API already running (PID $pid) — http://localhost:$API_PORT"
  echo "$pid" > "$API_PID_FILE"
else
  info "Starting API server..."
  # Load API key from .env if present
  [ -f "$DIR/.env" ] && set -a && source "$DIR/.env" && set +a
  cd "$DIR/web"
  PY_BIN="python3"
  if [ -f "${DIR}/.venv/bin/python3" ] && "${DIR}/.venv/bin/python3" -c "import uvicorn" 2>/dev/null; then
    PY_BIN="${DIR}/.venv/bin/python3"
  fi
  SCRIPTURE_WORKERS=1 nohup "$PY_BIN" -m uvicorn server:app \
    --port "$API_PORT" --host 0.0.0.0 --workers 1 --log-level info \
    > "$API_LOG" 2>&1 &
  echo $! > "$API_PID_FILE"
  info "Waiting for API..."
  for i in $(seq 1 30); do
    if curl -s "http://localhost:$API_PORT/api/v1/health" > /dev/null 2>&1; then
      ok "API ready (PID $(cat "$API_PID_FILE")) — http://localhost:$API_PORT"
      break
    fi
    sleep 1
  done
fi

# ── Start Frontend ──

if port_in_use "$FE_PORT"; then
  pid=$(ss -tlnp "sport = :$FE_PORT" 2>/dev/null | grep "LISTEN" | grep -oP 'pid=\K[0-9]+' | head -1)
  warn "Frontend already running (PID $pid) — http://localhost:$FE_PORT"
  echo "$pid" > "$FE_PID_FILE"
else
  info "Starting frontend dev server..."
  cd "$DIR/frontend"
  nohup npx vite --port "$FE_PORT" --host > "$FE_LOG" 2>&1 &
  echo $! > "$FE_PID_FILE"
  info "Waiting for frontend..."
  for i in $(seq 1 20); do
    if curl -s -o /dev/null "http://localhost:$FE_PORT" 2>/dev/null; then
      break
    fi
    sleep 1
  done
  ok "Frontend ready (PID $(cat "$FE_PID_FILE")) — http://localhost:$FE_PORT"
  info "API proxy: /api → http://localhost:$API_PORT"
fi

URL="http://localhost:$FE_PORT"
echo ""
echo "  ${GREEN}Both servers open${NC}"
echo "  API:      http://localhost:$API_PORT"
echo "  Frontend: $URL"
echo "  Close:    ./scripts/close.sh"
echo ""

# Open browser tab
case "$(uname -s)" in
  Linux)   xdg-open "$URL" 2>/dev/null || true ;;
  Darwin)  open "$URL" 2>/dev/null || true ;;
  CYGWIN*|MINGW*|MSYS*) start "$URL" 2>/dev/null || true ;;
esac
