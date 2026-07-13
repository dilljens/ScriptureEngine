#!/usr/bin/env python3
"""Frontend validation tests.

Usage:
  python3 scripts/test_frontend.py              # Run all tests
  python3 scripts/test_frontend.py --api        # API integration tests only
  python3 scripts/test_frontend.py --agent      # Agent-powered E2E tests only
  python3 scripts/test_frontend.py --list       # List available tests

Requires: API server running on localhost:8002
  ./run.sh web --port 8002
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("SCRIPTURE_API_URL", "http://localhost:8002")
API_BASE = f"{BASE}/api/v1"
AGENT_BASE = f"{BASE}/api/v1/agent"

PASS = 0
FAIL = 0
SKIP = 0


def test(name, fn):
    """Run a single test case."""
    global PASS, FAIL
    try:
        fn()
        print(f"  ✅ {name}")
        PASS += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        FAIL += 1


def skip(name, reason):
    global SKIP
    print(f"  ⏭️  {name}: {reason}")
    SKIP += 1


def fetch(url, method="GET", body=None):
    """Make an HTTP request and return parsed JSON."""
    headers = {"Accept": "application/json"}
    data = None
    if body:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if body:
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                pass
        return {"error": e.code, "body": body[:200]}
    except (urllib.error.URLError, OSError) as e:
        return {"error": str(e)}


def agent_action(action, wait=0.5):
    """Queue an agent action and wait for it to be consumed."""
    result = fetch(f"{AGENT_BASE}/action", "POST", action)
    time.sleep(wait)
    return result


def agent_read_state():
    """Read the current frontend state as reported by the agent hook."""
    return fetch(f"{AGENT_BASE}/state")


def agent_clear():
    """Clear the action queue."""
    fetch(f"{AGENT_BASE}/clear", "POST", {})


# ═══════════════════════════════════════════════════════════════
# API INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════

def test_api_version():
    d = fetch(f"{API_BASE}/health")
    assert d.get("ok"), f"health failed: {d}"
    assert "connections" in d["data"], f"missing connections: {d}"


def test_api_verse():
    d = fetch(f"{API_BASE}/verses/isa.55.6")
    assert d.get("ok"), f"verse failed: {d}"
    assert d["data"].get("text_english"), f"empty text: {d}"
    assert "Seek" in d["data"]["text_english"], f"wrong verse: {d}"


def test_api_search():
    d = fetch(f"{API_BASE}/search?q=written+heart&lang=english")
    assert d.get("ok"), f"search failed: {d}"
    assert d["data"]["total"] > 0, "no results"
    assert "written" in d["data"]["results"][0]["text"].lower(), f"wrong result: {d['data']['results'][0]}"


def test_api_semantic_search():
    d = fetch(f"{API_BASE}/semantic-search?q=faith&limit=3")
    assert d.get("ok"), f"semantic failed: {d}"
    assert len(d["data"]["results"]) > 0, "no semantic results"


def test_api_parallelism():
    d = fetch(f"{API_BASE}/parallelism/isaiah/6")
    assert d.get("ok"), f"parallelism failed: {d}"
    assert d["data"]["statistics"]["total_verses"] == 13, "wrong verse count"
    assert "verses" in d["data"], "missing verses"
    # Check intra-verse lines
    v10 = [v for v in d["data"]["verses"] if v["verse"] == 10][0]
    assert len(v10.get("lines", [])) >= 2, "v10 should have multiple lines"


def test_api_footnotes():
    d = fetch(f"{API_BASE}/footnotes/isa.55.6")
    assert d.get("ok"), f"footnotes failed: {d}"
    assert d["data"]["total"] > 0, "no footnotes for Isa 55:6"
    fn = d["data"]["footnotes"][0]
    assert "context_word" in fn, "missing context_word"
    assert "category" in fn, "missing category"


def test_api_tsk():
    d = fetch(f"{API_BASE}/tsk-crossrefs/isa.55.6")
    assert d.get("ok"), f"TSK failed: {d}"
    assert d["data"]["total"] > 0, "no TSK refs"
    ref = d["data"]["cross_references"][0]
    assert "target_verse" in ref, "missing target_verse"
    assert "type" in ref, "missing type"


def test_api_books():
    d = fetch(f"{API_BASE}/books")
    assert d.get("ok"), f"books failed: {d}"
    works = d["data"]["works"]
    assert len(works) >= 5, f"should have 5+ works, got {len(works)}"
    total_books = sum(len(w["books"]) for w in works)
    assert total_books >= 200, f"should have 200+ books, got {total_books}"


def test_api_gematria():
    d = fetch(f"{API_BASE}/gematria?word=%D7%99%D7%94%D7%95%D7%94")
    assert d.get("ok"), f"gematria failed: {d}"
    assert d["data"]["gematria"]["standard"] == 26, "YHWH should be 26"


def test_api_pardes():
    d = fetch(f"{API_BASE}/pardes/isa.55.6")
    assert d.get("ok"), f"pardes failed: {d}"


def test_api_grammar():
    d = fetch(f"{API_BASE}/verses/isa.55.6/grammar")
    assert d.get("ok"), f"grammar failed: {d}"
    assert d["data"]["text_english"], "missing text"
    assert "connections" in d["data"], "missing connections"


def test_api_chapter_generic():
    """Generic chapter endpoint works for any book."""
    for ref in ["gen.1", "matt.5", "alma.32"]:
        d = fetch(f"{API_BASE}/chapter/{ref}")
        assert d.get("ok"), f"chapter {ref} failed: {d}"
        assert d["data"]["statistics"]["total_verses"] > 0, f"no verses for {ref}"
    # Genesis 1 should have synonymous parallelism
    gen = fetch(f"{API_BASE}/chapter/gen.1")
    by_type = gen["data"]["statistics"]["by_type"]
    assert "parallel_synonymous" in by_type, "missing synonymous in genesis"
    assert by_type["parallel_synonymous"] > 0, "0 synonymous in genesis"


def test_api_chapter_footnotes():
    d = fetch(f"{API_BASE}/footnotes/isa.55")
    assert d.get("ok"), f"chapter footnotes failed: {d}"
    assert d["data"]["total"] >= 25, "should have 25+ footnotes in Isa 55"


# ═══════════════════════════════════════════════════════════════
# AGENT-POWERED E2E TESTS (requires ?agent=true on frontend)
# ═══════════════════════════════════════════════════════════════

def test_agent_endpoints():
    """Verify the agent control endpoints work."""
    agent_clear()
    d = fetch(f"{AGENT_BASE}/state")
    assert d.get("ok"), f"agent state failed: {d}"
    # Queue an action
    r = fetch(f"{AGENT_BASE}/action", "POST", {"action": "test"})
    assert r.get("ok"), f"queue action failed: {r}"
    assert "action_id" in r, "missing action_id"
    # Poll
    d = fetch(f"{AGENT_BASE}/actions?after=-1")
    assert d.get("ok"), f"poll failed: {d}"
    assert d["data"]["pending"] > 0, "no pending actions"
    # Report state
    r = fetch(f"{AGENT_BASE}/state", "POST", {"test": True})
    assert r.get("ok"), f"report state failed: {r}"


def test_agent_navigate():
    """Test that agent can queue a navigation action and read state."""
    agent_clear()
    agent_action({"action": "navigate", "book": "isa", "chapter": 6})
    d = agent_read_state()
    # The frontend should have processed the action by now
    # (if the agent hook is active via ?agent=true)
    print(f"\n       Agent state after navigate: {json.dumps(d.get('data', {}), indent=2)[:200]}")


def test_agent_toggle():
    """Test toggle via agent."""
    agent_clear()
    agent_action({"action": "toggle", "key": "footnotes"})
    d = agent_read_state()
    # Check if toggles changed
    print(f"\n       Agent state after toggle: {json.dumps(d.get('data', {}).get('toggles', {}), indent=2)[:200]}")


# ═══════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════

def run_api_tests():
    print("\n═══ API Integration Tests ═══")
    test("Health endpoint", test_api_version)
    test("Verse lookup (Isa 55:6)", test_api_verse)
    test("FTS5 search (written heart)", test_api_search)
    test("Semantic search (faith)", test_api_semantic_search)
    test("Parallelism (Isa 6)", test_api_parallelism)
    test("Footnotes (Isa 55:6)", test_api_footnotes)
    test("Footnotes chapter-level (Isa 55)", test_api_chapter_footnotes)
    test("TSK cross-refs (Isa 55:6)", test_api_tsk)
    test("Books list", test_api_books)
    test("Gematria (YHWH)", test_api_gematria)
    test("PaRDeS levels (Isa 55:6)", test_api_pardes)
    test("Grammar (Isa 55:6)", test_api_grammar)
    test("Generic chapter (Gen, Matt, Alma)", test_api_chapter_generic)


def run_agent_tests():
    print("\n═══ Agent E2E Tests ═══")
    test("Agent control endpoints", test_agent_endpoints)
    test("Agent navigate + read state", test_agent_navigate)
    test("Agent toggle + read state", test_agent_toggle)


def run_all():
    run_api_tests()
    # Check if API is up first
    try:
        health = fetch(f"{API_BASE}/health")
        if not health.get("ok"):
            print(f"\n❌ API not available at {API_BASE}")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ API not available at {API_BASE}: {e}")
        print("   Start with: ./run.sh web --port 8002")
        sys.exit(1)

    run_api_tests()
    run_agent_tests()

    total = PASS + FAIL + SKIP
    print(f"\n═══ Summary: {PASS} passed, {FAIL} failed, {SKIP} skipped ({total} total) ═══")
    return FAIL == 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Frontend validation tests")
    parser.add_argument("--api", action="store_true", help="API tests only")
    parser.add_argument("--agent", action="store_true", help="Agent E2E tests only")
    parser.add_argument("--list", action="store_true", help="List tests")
    args = parser.parse_args()

    if args.list:
        print("API tests:")
        for name in [k for k in dir(sys.modules[__name__]) if k.startswith("test_api_")]:
            print(f"  - {name.replace('test_api_', '')}")
        print("Agent tests:")
        for name in [k for k in dir(sys.modules[__name__]) if k.startswith("test_agent_")]:
            print(f"  - {name.replace('test_agent_', '')}")
        sys.exit(0)

    # Check API
    health = fetch(f"{API_BASE}/health")
    if not health.get("ok"):
        print(f"❌ API not available at {API_BASE}")
        print("   Start with: ./run.sh web --port 8002")
        sys.exit(1)

    if args.api:
        run_api_tests()
    elif args.agent:
        run_agent_tests()
    else:
        run_api_tests()
        run_agent_tests()

    total = PASS + FAIL + SKIP
    print(f"\n═══ Summary: {PASS} passed, {FAIL} failed, {SKIP} skipped ({total} total) ═══")
    sys.exit(1 if FAIL > 0 else 0)
