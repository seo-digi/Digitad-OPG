"""Tests for scraper module."""
import pytest
from unittest.mock import patch, MagicMock

from scraper import scrape_tags, parse_tags_from_html


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dermatologie - Medicym</title>
    <meta name="description" content="Services de dermatologie a Blainville.">
</head>
<body>
    <h1>Dermatologie</h1>
    <p>Content here</p>
</body>
</html>
"""

MISSING_TAGS_HTML = """
<!DOCTYPE html>
<html>
<head></head>
<body><p>No tags</p></body>
</html>
"""


class TestParseTagsFromHtml:
    def test_extracts_title_h1_meta(self):
        tags = parse_tags_from_html(SAMPLE_HTML)
        assert tags["title"] == "Dermatologie - Medicym"
        assert tags["h1"] == "Dermatologie"
        assert tags["meta_description"] == "Services de dermatologie a Blainville."

    def test_handles_missing_tags(self):
        tags = parse_tags_from_html(MISSING_TAGS_HTML)
        assert tags["title"] == ""
        assert tags["h1"] == ""
        assert tags["meta_description"] == ""


class TestScrapeTags:
    @patch("scraper.requests.get")
    def test_scrapes_single_url(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML
        mock_get.return_value = mock_resp

        results = scrape_tags(["https://example.com/derm"])
        assert results["https://example.com/derm"]["title"] == "Dermatologie - Medicym"

    @patch("scraper.requests.get")
    def test_handles_http_error(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = Exception("404")
        mock_get.return_value = mock_resp

        results = scrape_tags(["https://example.com/missing"])
        assert results["https://example.com/missing"]["error"] == "404"
        assert results["https://example.com/missing"]["title"] == ""
        assert results["https://example.com/missing"]["h1"] == ""
        assert results["https://example.com/missing"]["meta_description"] == ""
