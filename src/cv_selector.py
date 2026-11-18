
from pathlib import Path
import json

import fitz

from src.config import PROFILE_PATH, ROOT


def select_cv(role_id: str) -> Path | None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    role = profile["roles"].get(role_id)

    if not role:
        return None

    uploaded_path = ROOT / "cvs" / "uploads" / f"{role_id}.pdf"
    cv_path = uploaded_path if uploaded_path.is_file() else ROOT / role["cv"]

    if not cv_path.is_file():
        return None

    return cv_path


def list_profile_cvs() -> list[dict]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    return [
        {
            "role": role_id,
            "label": role["label"],
            "path": str(select_cv(role_id) or ROOT / role["cv"]),
            "available": select_cv(role_id) is not None,
        }
        for role_id, role in profile["roles"].items()
    ]


def extract_cv_text(cv_path: str | Path) -> str:
    path = Path(cv_path)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        raise ValueError("Le CV doit être un fichier PDF existant.")
    with fitz.open(path) as document:
        return "\n".join(page.get_text() for page in document).strip()


def validate_cv_upload(uploaded_file) -> tuple[bool, str]:
    if uploaded_file is None:
        return False, "Aucun fichier sélectionné."
    name = getattr(uploaded_file, "name", "")
    if not name.lower().endswith(".pdf"):
        return False, "Le CV doit être au format PDF."
    content = uploaded_file.getvalue()
    if not content:
        return False, "Le fichier est vide."
    try:
        with fitz.open(stream=content, filetype="pdf") as document:
            if document.page_count == 0:
                return False, "Le PDF ne contient aucune page."
    except Exception as exc:
        return False, f"PDF invalide : {exc}"
    return True, ""
