
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config" / "profile.json"


def select_cv(role_id: str) -> Path | None:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    role = profile["roles"].get(role_id)

    if not role:
        return None

    cv_path = ROOT / role["cv"]

    if not cv_path.is_file():
        return None

    return cv_path
