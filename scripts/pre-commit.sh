#!/usr/bin/env bash
# Pre-commit hook: saves session context, runs fast checks before commit.
# Install: ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit
#
# Checks:
# 1. Frontend builds without errors
# 2. Manifest.json and vite.svg exist in dist after build
# 3. API can import without crashes (basic import check)
# 4. Go backend tests pass (if Go files changed)

set -e

# Resolve project root: use git rev-parse (works from any subdirectory)
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
  ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi

echo "=== Session save ==="
cd "$ROOT"
python3 scripts/save_session.py 2>/dev/null && echo "  ✓ Session saved" || echo "  ⚠ Session save skipped"
echo "=== Pre-commit checks ==="

FAIL=0

# ── 1. Frontend build ──
echo "[1/4] Frontend build..."
cd "$ROOT/frontend"
if npx vite build --logLevel error 2>/dev/null; then
    echo "  ✓ Build ok"
else
    echo "  ✗ Build failed"
    FAIL=1
fi

# ── 2. Static files present ──
echo "[2/4] Static file check..."
for f in dist/manifest.json dist/sw.js dist/index.html; do
    if [ -f "$f" ]; then echo "  ✓ $f"; else echo "  ✗ $f missing"; FAIL=1; fi
done

# ── 3. API import check ──
echo "[3/4] API import check..."
cd "$ROOT"
if python3 -c "import sys; sys.path.insert(0,'.'); sys.path.insert(0,'web'); from server import app; print('  ✓ API imports ok')" 2>/dev/null; then
    :
else
    echo "  ✗ API import failed"
    FAIL=1
fi

# ── 4. Go backend tests (only if Go files changed) ──
CHANGED_GO=$(git diff --cached --name-only | grep -c 'backend/go-srs/' || true)
if [ "$CHANGED_GO" -gt 0 ]; then
    echo "[4/4] Go backend tests..."
    cd "$ROOT/backend/go-srs"
    if go test ./internal/... -count=1 2>/dev/null; then
        echo "  ✓ All Go tests pass"
    else
        echo "  ✗ Go tests failed"
        FAIL=1
    fi
else
    echo "[4/4] No Go files changed — skipping Go tests"
fi

# ── Result ──
if [ "$FAIL" -eq 0 ]; then
    echo "=== All checks passed ==="
else
    echo "=== Some checks FAILED — fix before committing ==="
fi
exit $FAIL
