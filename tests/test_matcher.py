from src.matcher import match_offer, normalize


def test_matching_returns_explainable_score():
    result = match_offer(
        "Stage PFE Data Engineer",
        "Python, SQL, Apache Spark, ETL, Airflow and data pipelines",
    )
    assert 0 <= result["score"] <= 100
    assert result["role"] == "data_engineer"
    assert result["matching_skills"]
    assert result["reasons"]
    assert result["recommendations"]


def test_normalize_removes_accents_and_whitespace():
    assert normalize("  Développement   Python  ") == "developpement python"