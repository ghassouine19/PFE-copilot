from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import json

from src.processing import normalize_text


DEFAULT_PREFERENCES = {
    "target_positions": ["Data Engineer", "AI Engineer", "Data Scientist", "BI/Data Analyst"],
    "locations": ["Morocco", "France", "remote"],
    "technologies": ["python", "sql", "spark", "airflow", "power bi", "machine learning"],
    "internship_only": False,
    "experience_level": "",
    "publication_days": 90,
    "exclusion_keywords": ["senior", "5+ years", "payant"],
    "minimum_score": 20,
}


def load_preferences(path: str | Path) -> dict:
    path = Path(path)
    preferences = dict(DEFAULT_PREFERENCES)
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        preferences.update(saved)
    return preferences


def save_preferences(path: str | Path, preferences: dict):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(preferences, indent=2, ensure_ascii=False), encoding="utf-8")


def apply_filters(job: dict, preferences: dict, score: float = 0) -> tuple[bool, list[str]]:
    reasons = []
    text = normalize_text(
        f"{job.get('title', '')} {job.get('description', '')} "
        f"{job.get('location', '')} {job.get('contract_type', '')}"
    )

    for keyword in preferences.get("exclusion_keywords", []):
        if normalize_text(keyword) and normalize_text(keyword) in text:
            reasons.append(f"Exclusion: {keyword}")

    if preferences.get("internship_only"):
        internship_terms = ("pfe", "stage", "intern", "internship", "fin d'etudes")
        if not any(term in text for term in internship_terms):
            reasons.append("Pas une offre de stage/PFE")

    locations = preferences.get("locations", [])
    location_text = normalize_text(job.get("location", ""))
    if locations and location_text:
        if not any(normalize_text(location) in location_text or normalize_text(location) in text
                   for location in locations):
            reasons.append("Localisation hors préférence")

    publication_days = preferences.get("publication_days", 90)
    published = str(job.get("published_at", "")).strip()
    if publication_days and published:
        try:
            parsed = datetime.fromisoformat(published.replace("Z", "+00:00")).replace(tzinfo=None)
            if parsed < datetime.utcnow() - timedelta(days=int(publication_days)):
                reasons.append("Offre trop ancienne")
        except (TypeError, ValueError):
            pass

    minimum_score = float(preferences.get("minimum_score", 0))
    if score < minimum_score:
        reasons.append(f"Score inférieur au seuil {minimum_score}")

    return not reasons, reasons
