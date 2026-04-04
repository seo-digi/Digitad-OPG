"""Tests for mapper module."""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from mapper import (
    compute_opportunity_scores,
    aggregate_gsc_by_url,
    get_top_queries_per_url,
    map_keywords_to_urls,
    reconcile_unmapped_urls,
)


@pytest.fixture
def gsc_df():
    return pd.DataFrame([
        {"page": "https://example.com/derm", "query": "dermatologue", "clicks": 66, "impressions": 6944, "ctr": 0.95, "avg_position": 5.0},
        {"page": "https://example.com/derm", "query": "dermatologie", "clicks": 30, "impressions": 3000, "ctr": 1.0, "avg_position": 6.0},
        {"page": "https://example.com/derm", "query": "peau specialiste", "clicks": 10, "impressions": 500, "ctr": 2.0, "avg_position": 8.0},
        {"page": "https://example.com/medecin", "query": "medecin famille", "clicks": 45, "impressions": 3450, "ctr": 1.3, "avg_position": 8.3},
    ])


@pytest.fixture
def keywords_df():
    return pd.DataFrame([
        {"keyword": "dermatologue", "volume": 6600, "position": "12", "priority": "high", "url": "", "intent": "commercial"},
        {"keyword": "médecin de famille", "volume": 4400, "position": "-", "priority": "", "url": "", "intent": "commercial"},
    ])


class TestAggregateGsc:
    def test_aggregates_impressions_per_url(self, gsc_df):
        agg = aggregate_gsc_by_url(gsc_df)
        assert agg.loc["https://example.com/derm", "impressions"] == 10444
        assert agg.loc["https://example.com/medecin", "impressions"] == 3450


class TestTopQueries:
    def test_returns_top_n_queries(self, gsc_df):
        top = get_top_queries_per_url(gsc_df, n=2)
        derm_queries = top["https://example.com/derm"]
        assert len(derm_queries) == 2
        assert derm_queries[0]["query"] == "dermatologue"


class TestOpportunityScore:
    def test_high_impressions_low_ctr_scores_higher(self):
        df = pd.DataFrame([
            {"page": "url1", "query": "a", "impressions": 10000, "clicks": 50, "ctr": 0.5},
            {"page": "url2", "query": "b", "impressions": 10000, "clicks": 500, "ctr": 5.0},
        ])
        scores = compute_opportunity_scores(df)
        assert scores["url1"] > scores["url2"]

    def test_ctr_zero_uses_floor(self):
        df = pd.DataFrame([
            {"page": "url1", "query": "a", "impressions": 100, "clicks": 0, "ctr": 0.0},
        ])
        scores = compute_opportunity_scores(df)
        assert scores["url1"] == 100 * (1 / 0.1)


class TestMapKeywordsToUrls:
    @patch("mapper.SentenceTransformer")
    def test_maps_based_on_cosine_similarity(self, mock_st_class, gsc_df, keywords_df):
        mock_model = MagicMock()
        mock_st_class.return_value = mock_model

        def fake_encode(texts, **kwargs):
            vecs = []
            for t in texts:
                t_clean = t.replace("query: ", "").replace("passage: ", "").lower()
                if "dermato" in t_clean:
                    vecs.append(np.array([1.0, 0.0, 0.0]))
                elif "medecin" in t_clean or "médecin" in t_clean:
                    vecs.append(np.array([0.0, 1.0, 0.0]))
                else:
                    vecs.append(np.array([0.3, 0.3, 0.3]))
            return np.array(vecs)

        mock_model.encode = fake_encode

        result = map_keywords_to_urls(gsc_df, keywords_df, model=mock_model)
        assert result["https://example.com/derm"]["keyword"] == "dermatologue"
        assert result["https://example.com/medecin"]["keyword"] == "médecin de famille"


class TestReconcileUnmappedUrls:
    def test_finds_study_urls_not_in_mapping(self):
        kw_df = pd.DataFrame([
            {"keyword": "test", "volume": 100, "position": "5", "priority": "", "url": "https://example.com/new-page", "intent": ""},
            {"keyword": "mapped", "volume": 200, "position": "3", "priority": "", "url": "https://example.com/derm", "intent": ""},
        ])
        mapped_urls = {"https://example.com/derm"}
        unmapped = reconcile_unmapped_urls(kw_df, mapped_urls)
        assert len(unmapped) == 1
        assert unmapped[0]["url"] == "https://example.com/new-page"
        assert unmapped[0]["keyword"] == "test"
