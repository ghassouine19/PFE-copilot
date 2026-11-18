
import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DATABASE_PATH", ROOT / "data" / "pfe_copilot.db"))
if not DB_PATH.is_absolute():
    DB_PATH = ROOT / DB_PATH

OPPORTUNITY_STATUSES = (
    "New", "Analyzed", "Interested", "Application prepared",
    "Applied", "Interview", "Rejected", "Accepted",
)


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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id TEXT NOT NULL UNIQUE,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT DEFAULT '',
                description TEXT DEFAULT '',
                source TEXT DEFAULT '',
                source_url TEXT DEFAULT '',
                deadline TEXT DEFAULT '',
                recipient TEXT DEFAULT '',
                role TEXT DEFAULT '',
                score INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'New',
                cv_path TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migrate older databases without losing records.
        app_columns = {row["name"] for row in conn.execute("PRAGMA table_info(applications)")}
        for name, definition in (
            ("sent_at", "TEXT"), ("gmail_message_id", "TEXT"),
            ("updated_at", "TEXT"),
        ):
            if name not in app_columns:
                conn.execute(f"ALTER TABLE applications ADD COLUMN {name} {definition}")

        opportunity_columns = {row["name"] for row in conn.execute("PRAGMA table_info(opportunities)")}
        for name, definition in (
            ("recipient", "TEXT DEFAULT ''"), ("cv_path", "TEXT DEFAULT ''"),
        ):
            if name not in opportunity_columns:
                conn.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {definition}")

        app_statuses = {row["status"] for row in conn.execute("SELECT DISTINCT status FROM applications")}
        status_map = {"draft": "New", "approved": "Application prepared", "sent": "Applied"}
        for old_status, new_status in status_map.items():
            if old_status in app_statuses:
                conn.execute("UPDATE applications SET status = ? WHERE status = ?", (new_status, old_status))


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
    allowed = set(OPPORTUNITY_STATUSES)
    allowed.update({"draft", "approved", "sent"})
    if status not in allowed:
        raise ValueError("Statut invalide")

    with connect() as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (status, application_id)
        )


def upsert_opportunity(data: dict) -> tuple[int, bool]:
    """Insert or update an opportunity; return (id, created)."""
    from src.job_sources import make_offer_id

    payload = dict(data)
    payload["offer_id"] = data.get("offer_id") or make_offer_id(payload)
    payload.setdefault("status", "New")
    fields = (
        "offer_id", "company", "title", "location", "description",
        "source", "source_url", "deadline", "recipient", "role",
        "score", "status", "cv_path",
    )
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM opportunities WHERE offer_id = ?",
            (payload["offer_id"],),
        ).fetchone()
        if existing:
            assignments = ", ".join(f"{field} = ?" for field in fields if field != "offer_id")
            values = [payload.get(field, "") for field in fields if field != "offer_id"]
            conn.execute(
                f"UPDATE opportunities SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (*values, existing["id"]),
            )
            return existing["id"], False
        placeholders = ", ".join("?" for _ in fields)
        cursor = conn.execute(
            f"INSERT INTO opportunities ({', '.join(fields)}) VALUES ({placeholders})",
            tuple(payload.get(field, "") for field in fields),
        )
        return cursor.lastrowid, True


def list_opportunities(search: str = "", status: str = "") -> list[dict]:
    query = "SELECT * FROM opportunities WHERE 1 = 1"
    params = []
    if search:
        query += " AND (company LIKE ? OR title LIKE ? OR description LIKE ?)"
        term = f"%{search}%"
        params.extend((term, term, term))
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY created_at DESC, id DESC"
    with connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def get_opportunity(opportunity_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM opportunities WHERE id = ?", (opportunity_id,))
        result = row.fetchone()
        return dict(result) if result else None


def update_opportunity(opportunity_id: int, **changes) -> None:
    allowed = {
        "company", "title", "location", "description", "source",
        "source_url", "deadline", "recipient", "role", "score",
        "status", "cv_path",
    }
    filtered = {key: value for key, value in changes.items() if key in allowed}
    if not filtered:
        return
    assignments = ", ".join(f"{key} = ?" for key in filtered)
    with connect() as conn:
        conn.execute(
            f"UPDATE opportunities SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*filtered.values(), opportunity_id),
        )


def dashboard_metrics() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        analyzed = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE status != 'New'"
        ).fetchone()[0]
        applications = conn.execute(
            "SELECT COUNT(*) FROM applications WHERE status = 'Applied'"
        ).fetchone()[0]
        interviews = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE status = 'Interview'"
        ).fetchone()[0]
        accepted = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE status = 'Accepted'"
        ).fetchone()[0]
        rejected = conn.execute(
            "SELECT COUNT(*) FROM opportunities WHERE status = 'Rejected'"
        ).fetchone()[0]
        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM opportunities GROUP BY status"
        ).fetchall()
        return {
            "total": total,
            "analyzed": analyzed,
            "applications_sent": applications,
            "interviews": interviews,
            "accepted": accepted,
            "rejected": rejected,
            "conversion_rate": round(applications / total * 100, 1) if total else 0.0,
            "status_distribution": {row["status"]: row["count"] for row in status_rows},
        }
