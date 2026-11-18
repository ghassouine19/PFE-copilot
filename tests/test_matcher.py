from src.matcher import match_offer


def test_matcher_returns_zero_score_for_unknown_offer():
    result = match_offer("Stage administratif", "Gestion de documents et accueil")
    assert result["score"] == 15 if result["is_pfe"] else result["score"] == 0
    assert result["matched_keywords"] == []