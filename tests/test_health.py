"""Health endpoint tests — run against live server."""
import os

import pytest

# Skip if not running against live server
SKIP_REASON = "Set SCRIPTURE_TEST_LIVE=1 to run health tests against live server"


class TestHealthLive:
    def test_health_live(self):
        """Run against the production server: SCRIPTURE_TEST_LIVE=1 pytest ..."""
        if not os.environ.get("SCRIPTURE_TEST_LIVE"):
            pytest.skip(SKIP_REASON)
        import requests
        r = requests.get("https://scriptureengine.org/api/v1/health", timeout=10)
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["status"] in ("ok", "degraded")
        assert data["verses"] >= 40000
        assert data["integrity"] == "ok"
