"""Tests for search and gematria endpoints."""


class TestSearch:
    def test_search_basic(self, client):
        resp = client.get("/api/v1/search?q=covenant&limit=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "results" in data
        assert len(data["results"]) > 0

    def test_search_empty_string(self, client):
        resp = client.get("/api/v1/search?q=")
        assert resp.status_code == 200

    def test_search_special_characters(self, client):
        resp = client.get("/api/v1/search?q=%24%25%5E%26")  # $%^&
        assert resp.status_code == 200


class TestGraphSearch:
    def test_graph_search_basic(self, client):
        resp = client.get("/api/v1/graph/search?q=faith&limit=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "results" in data

    def test_graph_search_tg_topics(self, client):
        """Search should return TG topics."""
        resp = client.get("/api/v1/graph/search?q=covenant")
        data = resp.json()["data"]
        results = data.get("results", [])
        topics = [r for r in results if r.get("type") == "topic"]
        assert len(topics) > 0, f"Expected TG topic results, got {len(topics)}"

    def test_graph_search_empty(self, client):
        resp = client.get("/api/v1/graph/search?q=xqzzz999")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data.get("results", [])) == 0


class TestGematria:
    def test_gematria_hebrew_word(self, client):
        resp = client.get("/api/v1/gematria?word=%D7%99%D7%94%D7%95%D7%94")  # יהוה
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Gematria may be nested in data.gematria or direct in data
        std = data.get("gematria", {}).get("standard", 0) or data.get("standard", 0)
        assert std > 0, f"YHWH should have a gematria value, got data keys: {list(data.keys())}"

    def test_gematria_unknown_word(self, client):
        resp = client.get("/api/v1/gematria?word=xxxxx")
        assert resp.status_code == 200

    def test_gematria_empty_word(self, client):
        resp = client.get("/api/v1/gematria?word=")
        assert resp.status_code in (200, 400, 422)
