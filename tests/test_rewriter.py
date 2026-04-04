"""Tests for rewriter module."""
import json
import pytest
from unittest.mock import patch, MagicMock

from rewriter import (
    validate_mapping,
    rewrite_tags,
    validate_meta_desc_length,
    build_rewrite_payload,
)


class TestValidateMetaDescLength:
    def test_in_range_passes(self):
        desc = "x" * 150
        assert validate_meta_desc_length(desc) is True

    def test_too_short_fails(self):
        desc = "x" * 100
        assert validate_meta_desc_length(desc) is False

    def test_too_long_fails(self):
        desc = "x" * 200
        assert validate_meta_desc_length(desc) is False


class TestBuildRewritePayload:
    def test_builds_correct_structure(self):
        pages = [
            {
                "url": "https://example.com/derm",
                "keyword": "dermatologue",
                "page_type": "service",
                "current_title": "Old Title",
                "current_h1": "Old H1",
                "current_meta_desc": "Old desc",
            }
        ]
        payload = build_rewrite_payload(pages, "Medicym", "fr")
        assert "dermatologue" in payload
        assert "Medicym" in payload
        assert "service" in payload


class TestValidateMapping:
    @patch("rewriter.anthropic.Anthropic")
    def test_returns_validated_mappings(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps([
            {"url": "https://example.com/derm", "keyword": "dermatologue",
             "status": "OK", "suggestion": None, "reason": None}
        ]))]
        mock_client.messages.create.return_value = mock_response

        mappings = [
            {"url": "https://example.com/derm", "keyword": "dermatologue",
             "top_queries": [{"query": "dermatologue", "impressions": 6944}]}
        ]
        result = validate_mapping(mappings, client=mock_client, model="claude-haiku-4-5-20251001")
        assert result[0]["status"] == "OK"


class TestRewriteTags:
    @patch("rewriter.anthropic.Anthropic")
    def test_returns_rewritten_tags(self, mock_anthropic_class):
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps([
            {
                "url": "https://example.com/derm",
                "new_title": "Dermatologue : Soins experts - Medicym",
                "new_h1": "Dermatologue a Blainville",
                "new_meta_desc": "D" * 150,
            }
        ]))]
        mock_client.messages.create.return_value = mock_response

        pages = [{
            "url": "https://example.com/derm",
            "keyword": "dermatologue",
            "page_type": "service",
            "current_title": "Old",
            "current_h1": "Old",
            "current_meta_desc": "Old",
        }]
        result = rewrite_tags(pages, "Medicym", "fr", client=mock_client, model="claude-sonnet-4-20250514")
        assert result[0]["new_title"] == "Dermatologue : Soins experts - Medicym"
