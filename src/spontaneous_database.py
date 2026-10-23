
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "spontaneous_applications.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_spontaneous_db():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS spontaneous_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                company TEXT,
                profile TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                cover_letter TEXT NOT NULL,
                cv_path TEXT,
                status TEXT NOT NULL,
                gmail_message_id TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def record_spontaneous_application(
    recipient: str,
    company: str,
    profile: str,
    subject: str,
    body: str,
    cover_letter: str,
    cv_path: str,
    status: str,
    gmail_message_id: str = "",
    error_message: str = "",
):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO spontaneous_applications (
                recipient, company, profile, subject, body,
                cover_letter, cv_path, status,
                gmail_message_id, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recipient,
            company,
            profile,
            subject,
            body,
            cover_letter,
            cv_path,
            status,
            gmail_message_id,
            error_message,
        ))

        return cursor.lastrowid


def list_spontaneous_applications(limit: int = 50):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, recipient, company, profile, subject,
                   status, gmail_message_id, error_message, created_at
            FROM spontaneous_applications
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [dict(row) for row in rows]
