"""OpenAPI route-floor test — catches accidental endpoint removal.

Intentional additions pass freely (no snapshot-update cycle); only REMOVED
routes fail, since deleting an endpoint breaks existing clients. The snapshot
is a floor of known routes, not an exact mirror.
"""
import json
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).parent / "__snapshots__"
SNAPSHOT_PATH = SNAPSHOT_DIR / "openapi.json"


def _endpoints(spec):
    found = set()
    for path, methods in spec.get("paths", {}).items():
        for method in methods:
            found.add(f"{method.upper()} {path}")
    return found


def test_openapi_no_routes_removed():
    """Fail only if a snapshotted endpoint disappeared. Additions are free."""
    from web.server import app
    current = _endpoints(app.openapi())

    if not SNAPSHOT_PATH.exists():
        # First run: record the floor
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        json.dump(app.openapi(), SNAPSHOT_PATH.open("w"), indent=2)
        return  # First run always passes

    saved = _endpoints(json.loads(SNAPSHOT_PATH.read_text()))

    removed = saved - current
    assert not removed, (
        f"API endpoints removed (breaks existing clients): {sorted(removed)}. "
        f"If intentional, delete {SNAPSHOT_PATH} and re-run to record the new floor."
    )

    added = current - saved
    if added:
        print(f"\nNew endpoints since snapshot (informational, not a failure): {sorted(added)}")
