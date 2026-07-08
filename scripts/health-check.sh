#!/bin/bash
# Post-deploy health check — run after deployment to verify everything works.
# Usage: bash scripts/health-check.sh

HOST="${1:-https://scriptureengine.org}"
API="${2:-https://scriptureengine.org}"
PASS=0
FAIL=0

check() {
    local url="$1"
    local expected="$2"
    local label="$3"
    local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [ "$status" = "$expected" ]; then
        echo "  ✅ $label ($status)"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $label — expected $expected, got $status"
        FAIL=$((FAIL + 1))
    fi
}

check_content() {
    local url="$1"
    local pattern="$2"
    local label="$3"
    if curl -s "$url" 2>/dev/null | grep -q "$pattern"; then
        echo "  ✅ $label"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $label — pattern '$pattern' not found"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== ScriptureEngine Health Check ==="
echo ""

echo "--- Core Endpoints ---"
check "$API/api/v1/health" 200 "API health"
check "$USER/" 200 "Frontend HTML"
check "$API/api/v1/verses/gen.1.1" 200 "Verse lookup"

echo ""
echo "--- Audio (Genesis 1) ---"
check "$API/api/v1/audio/play/gen.1.1" 200 "Audio play"
check "$API/api/v1/audio/align/gen.1.1" 200 "Audio alignment"

echo ""
echo "--- Frontend Assets ---"
check "$HOST/assets/index-*.js" 200 "JS bundle (any hash)"

echo ""
echo "--- JS Console Check ---"
# Check for common bundle errors by loading the page
HTML=$(curl -s "$HOST/" 2>/dev/null)
JS_HREF=$(echo "$HTML" | grep -o 'src="/assets/index-[^"]*\.js"' | head -1 | sed 's/src="//;s/"//')
if [ -n "$JS_HREF" ]; then
    JS_URL="${HOST}${JS_HREF}"
    JS=$(curl -s "$JS_URL" 2>/dev/null)
    if echo "$JS" | grep -q "MemorizeIcon"; then
        # Count definitions vs references
        DEFS=$(echo "$JS" | grep -o "function MemorizeIcon" | wc -l)
        REFS=$(echo "$JS" | grep -o "MemorizeIcon" | wc -l)
        if [ "$DEFS" -gt 0 ] || [ "$REFS" -eq 1 ]; then
            echo "  ✅ MemorizeIcon: $REFS refs, $DEFS defs (inline)"
            PASS=$((PASS + 1))
        else
            echo "  ❌ MemorizeIcon: $REFS refs but $DEFS defs — may error"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "  ⚠️  MemorizeIcon not checked (different build)"
    fi
fi

echo ""
echo "--- Summary ---"
echo "  $PASS passed, $FAIL failed"
exit $FAIL
