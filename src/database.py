
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "pfe_copilot.db"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                recipient TEXT DEFAULT '',
                source_url TEXT DEFAULT '',
                description TEXT DEFAULT '',
                role TEXT NOT NULL,
                score INTEGER NOT NULL,
                language TEXT NOT NULL DEFAULT 'fr',
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                cv_path TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def add_application(data: dict) -> int:
    fields = (
        "company", "title", "recipient", "source_url",
        "description", "role", "score", "language",
        "subject", "body", "cv_path", "status"
    )

    with connect() as conn:
        cursor = conn.execute(
            f"""INSERT INTO applications
            ({", ".join(fields)})
            VALUES ({", ".join("?" for _ in fields)})""",
            tuple(data.get(field, "") for field in fields)
        )
        return cursor.lastrowid


def list_applications():
    with connect() as conn:
        return [
            dict(row) for row in conn.execute(
                "SELECT * FROM applications ORDER BY id DESC"
            ).fetchall()
        ]


def update_status(application_id: int, status: str):
    allowed = {"draft", "approved", "sent", "rejected"}
    if status not in allowed:
        raise ValueError("Statut invalide")

    with connect() as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, application_id)
        )
