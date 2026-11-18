import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
CV_DIR = ROOT / "cvs"
TEMPLATES_DIR = ROOT / "templates"
PROFILE_PATH = ROOT / "config" / "profile.json"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "pfe_copilot.db")))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH
SPONTANEOUS_DB_PATH = DATA_DIR / "spontaneous_applications.db"
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"
