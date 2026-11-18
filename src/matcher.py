
import json
import re
import unicodedata
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config" / "profile.json"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


def load_profile() -> dict:
    return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))


def match_offer(title: str, description: str) -> dict:
    profile = load_profile()
    offer_text = normalize(f"{title} {description}")
    candidate_skills = [normalize(skill) for skill in profile["candidate"].get("skills", [])]

    role_scores = {}
    role_matches = {}
    for role_id, role in profile["roles"].items():
        role_keywords = [normalize(keyword) for keyword in role["keywords"]]
        matches = [keyword for keyword in role_keywords if keyword in offer_text]
        missing = [skill for skill in role_keywords if skill not in offer_text]
        role_scores[role_id] = len(matches) / max(len(role_keywords), 1)
        role_matches[role_id] = (matches, missing)

    best_role = max(role_scores, key=role_scores.get)
    role_matches_list, missing_role_keywords = role_matches[best_role]

    matched_skills = [skill for skill in candidate_skills if skill in offer_text]
    missing_skills = [skill for skill in candidate_skills if skill not in offer_text]

    documents = [
        " ".join(candidate_skills),
        offer_text,
    ]
    vectorizer = TfidfVectorizer(stop_words=None)
    vectors = vectorizer.fit_transform(documents)
    semantic = float(cosine_similarity(vectors[0], vectors[1])[0][0])

    skill_coverage = len(matched_skills) / max(len(candidate_skills), 1)
    role_coverage = role_scores[best_role]
    score = round(min(100, 100 * (0.55 * role_coverage + 0.25 * skill_coverage + 0.20 * semantic)))

    is_pfe = any(word in offer_text for word in (
        "pfe", "stage de fin d'etudes", "stage de fin d études",
        "final year internship", "graduation internship",
    ))
    matched_keywords = list(dict.fromkeys(role_matches_list + matched_skills))
    missing_keywords = list(dict.fromkeys(missing_role_keywords + missing_skills[:8]))
    reasons = [
        f"{len(matched_skills)} compétences du profil apparaissent dans l'offre",
        f"Le profil {profile['roles'][best_role]['label']} couvre {round(role_coverage * 100)} % des mots-clés ciblés",
        f"Similarité TF-IDF du profil avec l'offre : {round(semantic * 100)} %",
    ]
    recommendations = [
        f"Renforcer votre CV sur : {', '.join(missing_keywords[:5])}"
    ] if missing_keywords else ["Votre profil couvre largement les exigences principales de cette offre."]

    return {
        "role": best_role,
        "role_label": profile["roles"][best_role]["label"],
        "score": score,
        "is_pfe": is_pfe,
        "matched_keywords": matched_keywords,
        "matching_skills": matched_skills,
        "missing_skills": missing_keywords,
        "missing_role_keywords": missing_role_keywords,
        "relevant_keywords": matched_keywords,
        "reasons": reasons,
        "recommendations": recommendations,
        "semantic_similarity": round(semantic * 100, 1),
    }
