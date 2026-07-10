#!/usr/bin/env bash
# ScriptureEngine — stop both dev servers
# Usage: ./scripts/close.sh

set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${SCRIPTURE_API_PORT:-8000}"
FE_PORT="${SCRIPTURE_FE_PORT:-5173}"
API_PID_FILE="/tmp/scripture-dev-api.pid"
FE_PID_FILE="/tmp/scripture-dev-fe.pid"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
err()  { echo -e "${RED}✗${NC} $1"; }

alive() { kill -0 "$1" 2>/dev/null; }

# Only kill if the process cwd is under our project
belongs() {
  local cwd
  cwd=$(readlink -f "/proc/$1/cwd" 2>/dev/null || echo "")
  [ "$cwd" = "$DIR" ] || [ "$cwd" = "$DIR/web" ] || [ "$cwd" = "$DIR/frontend" ]
}

stop_one() {
  local pid_file="$1" name="$2" port="$3"
  local pid killed=0

  # Method 1: PID file
  pid=$(cat "$pid_file" 2>/dev/null || echo "")
  if [ -n "$pid" ] && alive "$pid" && belongs "$pid"; then
    kill "$pid" 2>/dev/null && ok "Stopped $name (PID $pid)" && killed=1
  fi

  # Method 2: Port match (only if the process is still alive)
  if [ "$killed" -eq 0 ] && [ -n "$port" ]; then
    local port_pid
    port_pid=$(ss -tlnp "sport = :$port" 2>/dev/null | grep "LISTEN" | grep -oP 'pid=\K[0-9]+' | head -1)
    if [ -n "$port_pid" ] && belongs "$port_pid" && alive "$port_pid"; then
      kill "$port_pid" 2>/dev/null && ok "Stopped $name on port $port (PID $port_pid)" && killed=1
    fi
  fi

  if [ "$killed" -eq 1 ]; then
    # Wait for the process to fully exit (graceful shutdown)
    local waited=0
    while [ "$waited" -lt 3 ]; do
      if [ -n "$port" ]; then
        ss -tlnp "sport = :$port" 2>/dev/null | grep -q "LISTEN" || break
      fi
      sleep 1
      waited=$((waited + 1))
    done
  else
    err "$name not running"
  fi
  rm -f "$pid_file"
}

echo ""
echo "  Closing ScriptureEngine..."
echo ""

stop_one "$API_PID_FILE" "API" "$API_PORT"
stop_one "$FE_PID_FILE"  "Frontend" "$FE_PORT"

echo ""
echo "  Done"
echo ""
