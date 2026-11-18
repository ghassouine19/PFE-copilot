
import sqlite3

from src.config import DB_PATH


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


def list_applications(search: str = "", status: str = ""):
    with connect() as conn:
        clauses = []
        params = []
        if search.strip():
            clauses.append("(company LIKE ? OR title LIKE ? OR role LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term, term])
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM applications {where} ORDER BY id DESC", params
        ).fetchall()
        return [dict(row) for row in rows]


def get_application(application_id: int):
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM applications WHERE id = ?", (application_id,)
        ).fetchone()
        return dict(row) if row else None


def application_stats() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        drafts = conn.execute("SELECT COUNT(*) FROM applications WHERE status = 'draft'").fetchone()[0]
        spontaneous = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE recipient = ''"
        ).fetchone()[0]
        by_status = {
            row["status"]: row["count"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS count FROM applications GROUP BY status"
            ).fetchall()
        }
        return {"total": total, "drafts": drafts, "spontaneous": spontaneous, "by_status": by_status}


def update_status(application_id: int, status: str):
    allowed = {"draft", "approved", "sent", "rejected"}
    if status not in allowed:
        raise ValueError("Statut invalide")

    with connect() as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, application_id)
        )
