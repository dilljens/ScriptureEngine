#!/usr/bin/env bash
set -euo pipefail

# ─── test-frontend.sh ───────────────────────────────────────────────
# Convenience wrapper: ensures Vite and the Python API are running,
# then runs Playwright E2E tests against the frontend.
#
# Usage:
#   ./scripts/test-frontend.sh            # run all tests (headless)
#   ./scripts/test-frontend.sh --headed   # run with browser visible
#   ./scripts/test-frontend.sh --ui       # run with Playwright UI mode
#   ./scripts/test-frontend.sh --file e2e/navigation.spec.ts  # single file
# ────────────────────────────────────────────────────────────────────

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ── Check required tools ──

check_port() {
  local port=$1
  ss -tlnp 2>/dev/null | grep -q ":$port " || nc -z localhost "$port" 2>/dev/null
}

echo -e "${YELLOW}Checking servers...${NC}"

# Check Python API (port 8000)
if check_port 8000; then
  echo -e "  ${GREEN}✓${NC} Python API on :8000"
else
  echo -e "  ${YELLOW}Starting Python API on :8000...${NC}"
  cd "$PROJECT_ROOT"
  .venv/bin/uvicorn web.server:app --port 8000 --host 127.0.0.1 &
  API_PID=$!
  echo -n "  Waiting for API..."
  for i in $(seq 1 30); do
    if check_port 8000; then echo -e " ${GREEN}ready${NC}"; break; fi
    sleep 1; echo -n "."
  done
  echo ""
  if ! check_port 8000; then
    echo -e "  ${RED}✗ API failed to start${NC}"
    kill $API_PID 2>/dev/null || true
    exit 1
  fi
fi

# Check Vite (port 5173)
if check_port 5173; then
  echo -e "  ${GREEN}✓${NC} Vite on :5173"
else
  echo -e "  ${YELLOW}Starting Vite on :5173...${NC}"
  cd "$FRONTEND_DIR"
  npx vite --port 5173 --host 127.0.0.1 &
  VITE_PID=$!
  echo -n "  Waiting for Vite..."
  for i in $(seq 1 30); do
    if check_port 5173; then echo -e " ${GREEN}ready${NC}"; break; fi
    sleep 1; echo -n "."
  done
  echo ""
  if ! check_port 5173; then
    echo -e "  ${RED}✗ Vite failed to start${NC}"
    kill $VITE_PID 2>/dev/null || true
    exit 1
  fi
fi

# ── Run tests ──

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Running Playwright tests${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cd "$FRONTEND_DIR"

# Forward remaining args to playwright
npx playwright test "$@"
EXIT_CODE=$?

# ── Cleanup ──

cleanup() {
  kill ${API_PID:-} ${VITE_PID:-} 2>/dev/null || true
}
trap cleanup EXIT

echo ""
if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}All tests passed!${NC}"
else
  echo -e "${RED}Some tests failed (exit code: $EXIT_CODE)${NC}"
  echo -e "  Open report: npx playwright show-report"
fi

exit $EXIT_CODE
