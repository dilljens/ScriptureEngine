#!/usr/bin/env python3
"""
Load test for Scripture Engine API endpoints.

Tests search, verse lookup, and health endpoints under concurrent load.
Zero external dependencies — uses only Python standard library.

Usage:
    python3 tests/load_test.py                          # Default: 50 concurrent
    python3 tests/load_test.py --concurrent 100          # 100 concurrent
    python3 tests/load_test.py --endpoint search         # Only search
    python3 tests/load_test.py --endpoint verse          # Only verse
    python3 tests/load_test.py --endpoint health         # Only health
    python3 tests/load_test.py --server http://localhost:8002  # Live server
"""

import argparse
import concurrent.futures
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Default: use TestClient for local testing (no server needed)
USE_TESTCLIENT = True
SERVER_URL = "http://test"


def build_requests():
    """Build the list of (name, url, method, body) test requests.

    Returns list of dicts with: name, url, method, body (or None)
    """
    return [
        # Search queries
        {"name": "search-covenant", "url": "/api/v1/search?q=covenant&limit=10"},
        {"name": "search-hebrew", "url": "/api/v1/search?q=%D7%91%D7%A8%D7%99%D7%AA&limit=10"},
        {"name": "search-greek", "url": "/api/v1/search?q=%CE%BB%CF%8C%CE%B3%CE%BF%CF%82&limit=10"},
        {"name": "search-short", "url": "/api/v1/search?q=love&limit=5"},
        {"name": "search-empty", "url": "/api/v1/search?q=&limit=5"},
        # Verse lookups
        {"name": "verse-gen1", "url": "/api/v1/verses/gen.1.1"},
        {"name": "verse-john1", "url": "/api/v1/verses/john.1.1"},
        {"name": "verse-psalm23", "url": "/api/v1/verses/psa.23.1"},
        {"name": "verse-isa53", "url": "/api/v1/verses/isa.53.5"},
        # Health
        {"name": "health", "url": "/api/v1/health"},
        {"name": "info", "url": "/api/v1/info"},
        # Chapter
        {"name": "chapter-gen1", "url": "/api/v1/chapter/gen.1"},
        {"name": "chapter-matt5", "url": "/api/v1/chapter/matt.5"},
        # Connections
        {"name": "conn-gen1", "url": "/api/v1/verses/gen.1.1/connections?limit=10"},
    ]


def make_request(req, use_testclient):
    """Make a single HTTP request and return timing data."""
    url = req["url"]
    start = time.perf_counter()
    status = 0
    size = 0

    try:
        if use_testclient:
            # Import here to avoid overhead at module level
            from fastapi.testclient import TestClient
            from web.server import app
            client = TestClient(app)
            path = url
            resp = client.get(path)
            status = resp.status_code
            size = len(resp.content)
        else:
            full_url = f"{SERVER_URL}{url}"
            resp = urllib.request.urlopen(full_url, timeout=30)
            status = resp.status
            size = len(resp.read())
    except Exception as e:
        status = getattr(e, "code", 599)

    elapsed = time.perf_counter() - start
    return {
        "name": req["name"],
        "status": status,
        "latency_ms": round(elapsed * 1000, 1),
        "size_bytes": size,
        "ok": status < 500,
    }


def run_load_test(num_concurrent=50, endpoint=None, use_testclient=True, warmup=True):
    """Run load test with concurrent requests."""
    all_requests = build_requests()

    # Warmup: make a few single requests to warm caches
    if warmup and use_testclient:
        print("  Warming caches with 3 single requests...", flush=True)
        from fastapi.testclient import TestClient
        from web.server import app
        wc = TestClient(app)
        for r in all_requests[:3]:
            try:
                wc.get(r["url"])
            except Exception:
                pass
        print("  Warmup complete.")
        print()

    # Filter by endpoint type if specified
    if endpoint:
        all_requests = [r for r in all_requests if endpoint in r["name"]]

    if not all_requests:
        print(f"No requests match endpoint filter: {endpoint}")
        return

    print(f"\n{'='*60}")
    print(f"  Load Test — {num_concurrent} concurrent requests")
    print(f"  Endpoints: {len(all_requests)} unique URLs")
    print(f"  Mode: {'TestClient' if use_testclient else f'HTTP ({SERVER_URL})'}")
    print(f"{'='*60}")
    print()

    # Build the task list: each task runs a single request
    tasks = []
    for i in range(num_concurrent):
        req = all_requests[i % len(all_requests)]
        tasks.append(req)

    print(f"  Dispatching {len(tasks)} requests ({num_concurrent} concurrent)...")
    print()

    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = {executor.submit(make_request, req, use_testclient): req for req in tasks}
        done = 0
        for future in concurrent.futures.as_completed(futures):
            req = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append({"name": req["name"], "status": 599, "latency_ms": 0, "size_bytes": 0, "ok": False})

            done += 1
            if done % 25 == 0 or done == len(tasks):
                print(f"    {done}/{len(tasks)} complete...", flush=True)

    # Analyze results
    print()
    print(f"  {'─'*58}")
    print(f"  {'RESULTS':^58}")
    print(f"  {'─'*58}")

    # Overall stats
    total = len(results)
    ok = sum(1 for r in results if r["ok"])
    errors = total - ok
    latencies = [r["latency_ms"] for r in results]
    error_by_status = {}
    for r in results:
        if not r["ok"]:
            error_by_status[r["status"]] = error_by_status.get(r["status"], 0) + 1

    print(f"  Total requests:     {total}")
    print(f"  Successful:         {ok} ({ok/total*100:.1f}%)")
    print(f"  Errors:             {errors}")
    if error_by_status:
        for status, count in sorted(error_by_status.items()):
            print(f"    Status {status}:     {count}")
    print(f"  Total time:         {sum(latencies)/1000:.1f}s")
    print(f"  Avg latency:        {statistics.mean(latencies):.0f}ms")
    if len(latencies) > 1:
        print(f"  Median (p50):       {statistics.median(latencies):.0f}ms")
        sorted_lat = sorted(latencies)
        print(f"  p95:                {sorted_lat[int(len(sorted_lat)*0.95)]:.0f}ms")
        print(f"  p99:                {sorted_lat[int(len(sorted_lat)*0.99)]:.0f}ms")
    print(f"  Min/Max:            {min(latencies):.0f}ms / {max(latencies):.0f}ms")

    # Per-endpoint stats
    print()
    print(f"  {'─'*58}")
    print(f"  {'PER-ENDPOINT':^58}")
    print(f"  {'─'*58}")
    by_name = {}
    for r in results:
        by_name.setdefault(r["name"], []).append(r)

    for name, group in sorted(by_name.items()):
        lat = [r["latency_ms"] for r in group]
        ok_count = sum(1 for r in group if r["ok"])
        print(f"  {name:25s} n={len(group):3d}  ok={ok_count:3d}  "
              f"avg={statistics.mean(lat):5.0f}ms  p95={sorted(lat)[int(len(lat)*0.95)]:5.0f}ms")

    return results


def main():
    parser = argparse.ArgumentParser(description="Load test Scripture Engine API")
    parser.add_argument("--concurrent", type=int, default=50, help="Number of concurrent requests (default: 50)")
    parser.add_argument("--endpoint", choices=["search", "verse", "health", "chapter", "conn"], help="Filter to specific endpoint type")
    parser.add_argument("--server", default="", help="Server URL (e.g., http://localhost:8002). Uses TestClient if empty.")
    args = parser.parse_args()

    use_tc = not args.server
    global SERVER_URL, USE_TESTCLIENT
    if args.server:
        SERVER_URL = args.server.rstrip("/")
        USE_TESTCLIENT = False

    run_load_test(num_concurrent=args.concurrent, endpoint=args.endpoint, use_testclient=use_tc)


if __name__ == "__main__":
    main()
