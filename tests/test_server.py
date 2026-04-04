"""Tests for server module."""
import json
import threading
import time
import pytest
from unittest.mock import patch

from server import ValidationServer


@pytest.fixture
def sample_mapping():
    return {
        "https://example.com/derm": {
            "keyword": "dermatologue",
            "similarity": 0.96,
            "volume": 6600,
            "position": "12",
            "relevance_score": 8942,
            "confidence": "OK",
            "top_queries": [{"query": "dermatologue", "impressions": 6944, "ctr": 0.95}],
            "lang": "fr",
        },
        "https://example.com/en/derm": {
            "keyword": "dermatologist",
            "similarity": 0.95,
            "volume": 2900,
            "position": "8",
            "relevance_score": 7800,
            "confidence": "OK",
            "top_queries": [{"query": "dermatologist", "impressions": 2100, "ctr": 0.9}],
            "lang": "en",
        },
    }


@pytest.fixture
def sample_opp_scores():
    return {
        "https://example.com/derm": 12450.0,
        "https://example.com/en/derm": 7400.0,
    }


@pytest.fixture
def sample_config():
    return {"brand_name": "TestBrand", "languages": ["fr", "en"]}


@pytest.fixture
def server(sample_mapping, sample_opp_scores, sample_config):
    return ValidationServer(sample_mapping, sample_opp_scores, sample_config)


class TestValidationServer:
    def test_init(self, server, sample_mapping):
        assert server.mapping_data == sample_mapping
        assert server.result is None
        assert not server.ready_event.is_set()

    def test_format_api_data(self, server):
        data = server.format_api_data()
        assert "client" in data
        assert "mapping" in data
        assert "fr" in data["mapping"]
        assert "en" in data["mapping"]
        assert len(data["mapping"]["fr"]) == 1
        assert data["mapping"]["fr"][0]["url"] == "https://example.com/derm"
        assert data["mapping"]["fr"][0]["opportunity_score"] == 12450.0

    def test_apply_validation_result(self, server):
        post_data = {
            "mapping": {
                "https://example.com/derm": {
                    "keyword": "dermatologue blainville",
                    "lang": "fr",
                    "status": "modified",
                },
                "https://example.com/en/derm": {
                    "keyword": "dermatologist",
                    "lang": "en",
                    "status": "ok",
                },
            }
        }
        result = server.apply_validation_result(post_data)
        assert "https://example.com/derm" in result
        assert result["https://example.com/derm"]["keyword"] == "dermatologue blainville"
        assert "https://example.com/en/derm" in result

    def test_apply_validation_skips_entries(self, server):
        post_data = {
            "mapping": {
                "https://example.com/derm": {"keyword": "dermatologue", "lang": "fr", "status": "skip"},
                "https://example.com/en/derm": {"keyword": "dermatologist", "lang": "en", "status": "ok"},
            }
        }
        result = server.apply_validation_result(post_data)
        assert "https://example.com/derm" not in result
        assert "https://example.com/en/derm" in result

    def test_apply_validation_rejects_empty(self, server):
        with pytest.raises(ValueError):
            server.apply_validation_result({"mapping": {}})

    def test_update_progress_thread_safe(self, server):
        server.update_progress("scraping", 5, 25)
        assert server.get_progress()["step"] == "scraping"
        assert server.get_progress()["current"] == 5

    def test_mark_done(self, server):
        server.update_progress("scraping", 25, 25)
        server.mark_done(grace_seconds=0)
        assert server.get_progress()["done"] is True


class TestFlaskEndpoints:
    @pytest.fixture
    def client(self, server):
        app = server._create_app()
        app.config["TESTING"] = True
        return app.test_client()

    def test_api_data_returns_json(self, client):
        r = client.get("/api/data")
        assert r.status_code == 200
        data = r.get_json()
        assert "client" in data
        assert "mapping" in data

    def test_api_validate_accepts_valid_post(self, client, server):
        post_data = {
            "mapping": {
                "https://example.com/derm": {"keyword": "dermatologue", "lang": "fr", "status": "ok"},
                "https://example.com/en/derm": {"keyword": "dermatologist", "lang": "en", "status": "ok"},
            }
        }
        r = client.post("/api/validate", json=post_data)
        assert r.status_code == 200
        assert server.ready_event.is_set()
        assert server.result is not None

    def test_api_validate_rejects_empty(self, client):
        r = client.post("/api/validate", json={"mapping": {}})
        assert r.status_code == 400

    def test_api_validate_rejects_duplicate(self, client, server):
        post_data = {"mapping": {"https://example.com/derm": {"keyword": "test", "lang": "fr", "status": "ok"}}}
        client.post("/api/validate", json=post_data)
        r = client.post("/api/validate", json=post_data)
        assert r.status_code == 409

    def test_api_progress(self, client, server):
        server.update_progress("scraping", 3, 10)
        r = client.get("/api/progress")
        data = r.get_json()
        assert data["step"] == "scraping"
        assert data["current"] == 3
