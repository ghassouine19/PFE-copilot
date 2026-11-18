
import json
import re
import unicodedata
from pathlib import Path

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
    text = normalize(f"{title} {description}")

    scores = {}
    matched_by_role = {}

    for role_id, role in profile["roles"].items():
        keywords = [normalize(k) for k in role["keywords"]]
        matches = [k for k in keywords if k in text]

        scores[role_id] = len(matches) / max(len(keywords), 1)
        matched_by_role[role_id] = matches

    best_role = max(scores, key=scores.get)
    matched = matched_by_role[best_role]

    is_pfe = any(
        word in text
        for word in ["pfe", "stage de fin d'etudes",
                     "stage de fin d études",
                     "final year internship", "graduation internship"]
    )

    # Heuristique simple : à affiner avec les offres réelles.
    score = min(100, round(100 * scores[best_role]))
    if is_pfe:
        score = min(100, score + 15)

    return {
        "role": best_role,
        "role_label": profile["roles"][best_role]["label"],
        "score": score,
        "is_pfe": is_pfe,
        "matched_keywords": matched
    }
