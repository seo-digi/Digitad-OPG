"""Keyword-URL mapping using embeddings and scoring."""
import math
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, SIMILARITY_THRESHOLD


def aggregate_gsc_by_url(gsc_df):
    """Aggregate GSC data per URL: sum impressions, clicks."""
    return gsc_df.groupby("page").agg({
        "impressions": "sum",
        "clicks": "sum",
    })


def get_top_queries_per_url(gsc_df, n=10):
    """Get top N queries per URL by impressions."""
    missing = [c for c in ["query", "impressions", "ctr"] if c not in gsc_df.columns]
    if missing:
        raise KeyError(f"Missing columns in GSC CSV: {missing}. Found: {gsc_df.columns.tolist()}")
    result = {}
    for page, group in gsc_df.groupby("page"):
        top = group.nlargest(n, "impressions")
        result[page] = top[["query", "impressions", "ctr"]].to_dict("records")
    return result


def compute_opportunity_scores(gsc_df):
    """Compute opportunity score per URL: high impressions + low CTR = high potential.

    Aggregates impressions and computes weighted average CTR per page,
    then applies: opportunity = total_impressions * (1 / max(avg_ctr, 0.1)).
    """
    agg = gsc_df.groupby("page").agg({
        "impressions": "sum",
        "clicks": "sum",
    })
    agg["avg_ctr"] = (agg["clicks"] / agg["impressions"].replace(0, 1)) * 100

    scores = {}
    for page, row in agg.iterrows():
        ctr = max(row["avg_ctr"], 0.1)
        scores[page] = row["impressions"] * (1 / ctr)
    return scores


def map_keywords_to_urls(gsc_df, keywords_df, model=None):
    """Map each URL to the best keyword using embeddings + cosine similarity.

    Returns dict: {url: {keyword, similarity, volume, top_queries, confidence}}
    """
    if model is None:
        model = SentenceTransformer(EMBEDDING_MODEL)

    top_queries = get_top_queries_per_url(gsc_df, n=10)

    kw_list = keywords_df["keyword"].tolist()
    kw_embeddings = model.encode(
        [f"passage: {kw}" for kw in kw_list],
        normalize_embeddings=True,
    )

    result = {}
    for url, queries in top_queries.items():
        query_texts = [q["query"] for q in queries]
        query_impressions = [q["impressions"] for q in queries]

        query_embeddings = model.encode(
            [f"query: {q}" for q in query_texts],
            normalize_embeddings=True,
        )

        sim_matrix = query_embeddings @ kw_embeddings.T

        best_idx = np.unravel_index(sim_matrix.argmax(), sim_matrix.shape)
        best_query_idx, best_kw_idx = best_idx
        best_similarity = sim_matrix[best_query_idx, best_kw_idx]

        matched_keyword = kw_list[best_kw_idx]
        matched_row = keywords_df.iloc[best_kw_idx]

        impressions = query_impressions[best_query_idx]
        volume = matched_row["volume"] if matched_row["volume"] > 0 else 1
        volume_boost = 1 + math.log(volume)
        priority_boost = 1.5 if matched_row.get("priority", "") else 1.0
        relevance = float(best_similarity) * impressions * volume_boost * priority_boost

        result[url] = {
            "keyword": matched_keyword,
            "similarity": float(best_similarity),
            "volume": int(matched_row["volume"]),
            "position": matched_row["position"],
            "relevance_score": relevance,
            "top_queries": queries[:3],
            "confidence": "OK" if best_similarity >= SIMILARITY_THRESHOLD else "LOW",
        }

    return result


def reconcile_unmapped_urls(keywords_df, mapped_urls):
    """Find keyword study URLs that have no GSC data and weren't mapped.

    Returns list of {url, keyword, volume, position, source: "keyword_study"}
    """
    unmapped = []
    for _, row in keywords_df.iterrows():
        study_url = row.get("url", "")
        if not study_url or study_url in mapped_urls:
            continue
        unmapped.append({
            "url": study_url,
            "keyword": row["keyword"],
            "volume": int(row["volume"]),
            "position": row.get("position", "-"),
            "similarity": 1.0,
            "relevance_score": 0,
            "top_queries": [],
            "confidence": "STUDY",
            "source": "keyword_study",
        })
    return unmapped
