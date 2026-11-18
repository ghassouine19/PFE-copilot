from src.cv_selector import recommend_cv, select_cv


def test_cv_selector_missing_role():
    assert select_cv("unknown_role") is None


def test_cv_recommendation_is_explainable():
    result = recommend_cv("data_engineer", "spark sql python etl")
    assert "cv_path" in result
    assert "reason" in result
    assert isinstance(result["exists"], bool)