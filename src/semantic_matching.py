from __future__ import annotations

from src.matcher import match_offer


def semantic_match_offer(title: str, description: str, enabled: bool = False) -> dict:
    result = match_offer(title, description)
    if not enabled:
        return {**result, "comparison_method": "fallback-local"}

    try:
        from sentence_transformers import SentenceTransformer
        from sklearn.metrics.pairwise import cosine_similarity

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        offer_embedding = model.encode([f"{title} {description}"])
        profile_embeddings = model.encode([
            "Data Engineer ETL SQL Spark Airflow pipelines cloud",
            "Data Scientist machine learning statistics predictive modeling",
            "BI Data Analyst Power BI dashboards reporting visualization",
            "AI Engineer deep learning MLOps LLM model deployment",
        ])
        scores = cosine_similarity(offer_embedding, profile_embeddings)[0]
        index = int(scores.argmax())
        role_ids = ["data_engineer", "data_scientist", "bi_analyst", "ai_engineer"]
        semantic_score = round(float(scores[index]) * 100)
        if semantic_score > result["score"]:
            result["score"] = semantic_score
            result["role"] = role_ids[index]
        result["method"] = "sentence-transformer"
        result["comparison_method"] = "semantic"
    except Exception as exc:
        result["comparison_method"] = f"fallback-local ({type(exc).__name__})"
    return result
