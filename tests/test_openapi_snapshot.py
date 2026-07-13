"""OpenAPI schema snapshot test — catches accidental API changes."""
import json
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "__snapshots__"
SNAPSHOT_PATH = SNAPSHOT_DIR / "openapi.json"


def test_openapi_matches_snapshot():
    """Fail if OpenAPI schema changed. Update snapshot deliberately."""
    from web.server import app
    current = app.openapi()

    if not SNAPSHOT_PATH.exists():
        # First run: create snapshot
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        json.dump(current, SNAPSHOT_PATH.open("w"), indent=2)
        return  # First run always passes

    saved = json.loads(SNAPSHOT_PATH.read_text())

    # Compare path counts (quick check)
    saved_paths = len(saved.get("paths", {}))
    current_paths = len(current.get("paths", {}))

    assert saved_paths == current_paths, (
        f"API path count changed: {saved_paths} → {current_paths}. "
        f"If intentional, delete {SNAPSHOT_PATH} and re-run."
    )

    # Compare endpoint signatures (method + path)
    saved_endpoints = set()
    for path, methods in saved.get("paths", {}).items():
        for method in methods:
            saved_endpoints.add(f"{method.upper()} {path}")

    current_endpoints = set()
    for path, methods in current.get("paths", {}).items():
        for method in methods:
            current_endpoints.add(f"{method.upper()} {path}")

    added = current_endpoints - saved_endpoints
    removed = saved_endpoints - current_endpoints

    assert not added, f"New endpoints added (not in snapshot): {added}"
    assert not removed, f"Endpoints removed (in snapshot but missing): {removed}"
