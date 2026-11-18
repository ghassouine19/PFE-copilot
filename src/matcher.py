
import json
import re
import unicodedata
from pathlib import Path
from importlib.util import find_spec

from src.config import PROFILE_PATH


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def match_offer(title: str, description: str) -> dict:
    profile = load_profile()
    text = normalize(f"{title} {description}")

    scores = {}
    matched_by_role = {}

    for role_id, role in profile["roles"].items():
        keywords = [normalize(k) for k in role["keywords"]]
        matches = [k for k in keywords if k in text]

        scores[role_id] = len(matches) / max(len(keywords), 1)
        matched_by_role[role_id] = matches

    best_role = max(scores, key=lambda role_id: (scores[role_id], len(matched_by_role[role_id])))
    matched = matched_by_role[best_role]

    is_pfe = any(
        word in text
        for word in ["pfe", "stage de fin d'etudes",
                     "stage de fin d études",
                     "final year internship", "graduation internship"]
    )

    baseline_score = 0
    baseline_method = "keyword"
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        documents = [text]
        profile_labels = {}
        for role_id, role in profile["roles"].items():
            documents.append(normalize(f"{role['label']} {' '.join(role['keywords'])}"))
            profile_labels[len(documents) - 1] = role_id
        vectorizer = TfidfVectorizer(stop_words=None, ngram_range=(1, 2))
        matrix = vectorizer.fit_transform(documents)
        similarities = cosine_similarity(matrix[0:1], matrix[1:].copy()).flatten()
        tfidf_role_index = int(similarities.argmax())
        tfidf_role = profile_labels[tfidf_role_index + 1]
        tfidf_score = float(similarities.max()) * 100
        baseline_method = "tfidf-cosine"
        if tfidf_role == best_role:
            baseline_score = min(100, round((scores[best_role] * 70) + (tfidf_score * 0.30)))
        else:
            baseline_score = min(100, round(scores[best_role] * 100))
    except Exception:
        baseline_score = min(100, round(100 * scores[best_role]))

    score = baseline_score
    if is_pfe:
        score = min(100, score + 15)

    missing = [
        keyword
        for keyword in [normalize(k) for k in profile["roles"][best_role]["keywords"]]
        if keyword not in text
    ]

    return {
        "role": best_role,
        "role_label": profile["roles"][best_role]["label"],
        "score": score,
        "is_pfe": is_pfe,
        "matched_keywords": matched,
        "missing_skills": missing,
        "method": baseline_method,
        "explanation": (
            f"Le profil {profile['roles'][best_role]['label']} a été retenu "
            f"car {len(matched)} mot(s)-clé(s) de ce profil apparaissent dans l'offre."
        ),
        "scores": scores,
    }
