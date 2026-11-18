
from pathlib import Path
import json
from src.cv_parser import extract_pdf_text

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config" / "profile.json"


def get_cv_candidates() -> list[dict]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    candidates = []
    for role_id, role in profile["roles"].items():
        cv_path = ROOT / role["cv"]
        text = ""
        if cv_path.is_file():
            try:
                text = extract_pdf_text(cv_path)
            except (ValueError, OSError):
                text = ""
        candidates.append({
            "role": role_id,
            "label": role["label"],
            "path": str(cv_path),
            "exists": cv_path.is_file(),
            "text": text,
            "keywords": role["keywords"],
        })
    return candidates


def select_cv(role_id: str) -> Path | None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    role = profile["roles"].get(role_id)

    if not role:
        return None

    cv_path = ROOT / role["cv"]

    if not cv_path.is_file():
        return None

    return cv_path


def recommend_cv(role_id: str, offer_text: str = "") -> dict:
    candidates = get_cv_candidates()
    selected = next((item for item in candidates if item["role"] == role_id), None)
    if not selected:
        return {"cv_path": None, "reason": "Aucun CV associé à ce profil.", "exists": False}
    cv_path = Path(selected["path"])
    if not cv_path.is_file():
        return {"cv_path": cv_path, "reason": "Le PDF associé à ce profil est introuvable.", "exists": False}

    normalized_offer = offer_text.lower()
    matched_keywords = [keyword for keyword in selected["keywords"] if keyword.lower() in normalized_offer]
    reason = (
        f"CV recommandé pour l'orientation {selected['label']}."
        + (
            f" Mots-clés corroborés : {', '.join(matched_keywords[:5])}."
            if matched_keywords else ""
        )
    )
    return {
        "cv_path": cv_path,
        "reason": reason,
        "exists": True,
        "role": role_id,
        "label": selected["label"],
    }
