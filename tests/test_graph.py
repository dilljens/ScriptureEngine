"""Tests for graph exploration endpoints."""
import pytest


class TestGraphExplore:
    def test_graph_explore_basic(self, client, verse_refs):
        resp = client.get(f"/api/v1/graph/explore?verse={verse_refs['gen1_1']}&depth=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "nodes" in data
        assert "edges" in data
        assert data["node_count"] > 0

    def test_graph_explore_tg_topic(self, client):
        """Graph should work with TG topic nodes."""
        resp = client.get("/api/v1/graph/explore?verse=tg:faith&depth=1&limit=10")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["node_count"] > 0

    def test_graph_explore_with_layer_filter(self, client, verse_refs):
        resp = client.get(
            f"/api/v1/graph/explore?verse={verse_refs['gen1_1']}&depth=1&layers=interpretive&limit=10"
        )
        assert resp.status_code == 200

    def test_graph_explore_bd_entry(self, client):
        resp = client.get("/api/v1/graph/explore?verse=bd:faith&depth=1&limit=10")
        assert resp.status_code == 200


class TestGraphCentrality:
    def test_centrality_basic(self, client):
        resp = client.get("/api/v1/graph/centrality?limit=5")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data.get("results", [])) > 0

    def test_centrality_by_book(self, client):
        resp = client.get("/api/v1/graph/centrality?book=gen&limit=5")
        assert resp.status_code == 200


class TestQuiz:
    def test_quiz_text_tier(self, client):
        resp = client.get("/api/v1/quiz?tier=text&count=3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["returned"] > 0
        for q in data["questions"]:
            assert q["tier"] == "text"

    def test_quiz_analysis_tier(self, client):
        resp = client.get("/api/v1/quiz?tier=analysis&count=3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["returned"] > 0

    def test_quiz_consistency_tier(self, client):
        resp = client.get("/api/v1/quiz?tier=consistency&count=3")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["returned"] > 0

    def test_quiz_shows_verse_text(self, client):
        """Quiz questions should contain passage text, not just references."""
        resp = client.get("/api/v1/quiz?tier=text&count=5")
        questions = resp.json()["data"]["questions"]
        has_verse_text = any("“" in q["question"] or "**" in q["question"] for q in questions)
        assert has_verse_text, "Expected verse text formatting in quiz questions"
