
import sqlite3
from datetime import datetime, timezone

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
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS job_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                config TEXT NOT NULL DEFAULT '{}',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS raw_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER,
                source_name TEXT NOT NULL,
                payload TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                offer_id TEXT,
                FOREIGN KEY(source_id) REFERENCES job_sources(id)
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id TEXT UNIQUE NOT NULL,
                source_id INTEGER,
                source_name TEXT NOT NULL,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                published_at TEXT NOT NULL DEFAULT '',
                contract_type TEXT NOT NULL DEFAULT '',
                application_url TEXT NOT NULL DEFAULT '',
                hr_email TEXT NOT NULL DEFAULT '',
                required_skills TEXT NOT NULL DEFAULT '[]',
                normalized_company TEXT NOT NULL DEFAULT '',
                normalized_title TEXT NOT NULL DEFAULT '',
                collected_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'COLLECTED',
                is_duplicate INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(source_id) REFERENCES job_sources(id)
            );
            CREATE TABLE IF NOT EXISTS job_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                skill TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            CREATE TABLE IF NOT EXISTS candidate_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                skills TEXT NOT NULL DEFAULT '[]',
                cv_path TEXT NOT NULL DEFAULT '',
                preferences TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS matching_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                role_id TEXT NOT NULL,
                score REAL NOT NULL,
                matched_skills TEXT NOT NULL DEFAULT '[]',
                missing_skills TEXT NOT NULL DEFAULT '[]',
                method TEXT NOT NULL,
                explanation TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            CREATE TABLE IF NOT EXISTS application_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                job_id INTEGER,
                document_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                editable TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(application_id) REFERENCES applications(id),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'RUNNING',
                statistics TEXT NOT NULL DEFAULT '{}',
                error TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS pipeline_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                job_id INTEGER,
                stage TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '',
                started_at TEXT NOT NULL,
                finished_at TEXT,
                FOREIGN KEY(run_id) REFERENCES pipeline_runs(id),
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER,
                recipient TEXT NOT NULL,
                status TEXT NOT NULL,
                gmail_message_id TEXT NOT NULL DEFAULT '',
                error_message TEXT NOT NULL DEFAULT '',
                sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(application_id) REFERENCES applications(id)
            );
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


def update_application_content(application_id: int, recipient: str, subject: str, body: str):
    with connect() as conn:
        conn.execute(
            "UPDATE applications SET recipient=?, subject=?, body=? WHERE id=?",
            (recipient.strip(), subject.strip(), body.strip(), application_id),
        )


def upsert_job_source(name: str, source_type: str, config: str = "{}", enabled: bool = True) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT id FROM job_sources WHERE name = ?", (name,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE job_sources SET source_type=?, config=?, enabled=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (source_type, config, int(enabled), row["id"]),
            )
            return row["id"]
        cursor = conn.execute(
            "INSERT INTO job_sources(name, source_type, config, enabled) VALUES (?, ?, ?, ?)",
            (name, source_type, config, int(enabled)),
        )
        return cursor.lastrowid


def list_job_sources():
    with connect() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM job_sources ORDER BY name"
        ).fetchall()]


def insert_raw_job(source_name: str, payload: str, collected_at: str, offer_id: str = "", source_id: int | None = None) -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO raw_jobs(source_id, source_name, payload, collected_at, offer_id) VALUES (?, ?, ?, ?, ?)",
            (source_id, source_name, payload, collected_at, offer_id),
        )
        return cursor.lastrowid


def insert_job(job: dict) -> tuple[int, bool]:
    fields = (
        "offer_id", "source_id", "source_name", "company", "title", "description",
        "location", "published_at", "contract_type", "application_url", "hr_email",
        "required_skills", "normalized_company", "normalized_title", "collected_at",
        "status", "is_duplicate",
    )
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM jobs WHERE offer_id=?", (job["offer_id"],)
        ).fetchone()
        if existing:
            return existing["id"], True
        cursor = conn.execute(
            f"INSERT INTO jobs({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
            tuple(job.get(field, "" if field not in {"source_id", "is_duplicate"} else 0) for field in fields),
        )
        job_id = cursor.lastrowid
        for skill in job.get("skills", []):
            conn.execute("INSERT INTO job_skills(job_id, skill) VALUES (?, ?)", (job_id, skill))
        return job_id, False


def list_jobs(search: str = "", status: str = "", limit: int = 500):
    with connect() as conn:
        clauses = []
        params = []
        if search.strip():
            clauses.append("(company LIKE ? OR title LIKE ? OR description LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term, term])
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM jobs {where} ORDER BY id DESC LIMIT ?", params + [limit]
        ).fetchall()
        return [dict(row) for row in rows]


def get_job(job_id: int):
    with connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        return dict(row) if row else None


def update_job_status(job_id: int, status: str):
    with connect() as conn:
        conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))


def job_stats() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        duplicates = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_duplicate=1").fetchone()[0]
        by_status = {
            row["status"]: row["count"]
            for row in conn.execute(
                "SELECT status, COUNT(*) AS count FROM jobs GROUP BY status"
            ).fetchall()
        }
        return {"total": total, "duplicates": duplicates, "by_status": by_status}


def create_pipeline_run() -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO pipeline_runs(started_at, status) VALUES (?, 'RUNNING')",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"),),
        )
        return cursor.lastrowid


def finish_pipeline_run(run_id: int, status: str, statistics: str = "{}", error: str = ""):
    with connect() as conn:
        conn.execute(
            "UPDATE pipeline_runs SET finished_at=?, status=?, statistics=?, error=? WHERE id=?",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), status, statistics, error, run_id),
        )


def record_pipeline_task(run_id: int, job_id: int | None, stage: str, status: str, message: str = "", attempts: int = 1):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with connect() as conn:
        conn.execute(
            "INSERT INTO pipeline_tasks(run_id, job_id, stage, status, attempts, message, started_at, finished_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, job_id, stage, status, attempts, message, now, now),
        )


def list_pipeline_runs(limit: int = 50):
    with connect() as conn:
        runs = [dict(row) for row in conn.execute(
            "SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()]
        tasks = [dict(row) for row in conn.execute(
            "SELECT * FROM pipeline_tasks ORDER BY id DESC LIMIT 500"
        ).fetchall()]
        return runs, tasks


def save_matching_result(job_id: int, result: dict):
    import json
    with connect() as conn:
        conn.execute(
            "INSERT INTO matching_results(job_id, role_id, score, matched_skills, missing_skills, method, explanation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                job_id,
                result["role"],
                result["score"],
                json.dumps(result.get("matched_keywords", []), ensure_ascii=False),
                json.dumps(result.get("missing_skills", []), ensure_ascii=False),
                result.get("method", "lexical"),
                result["explanation"],
            ),
        )


def list_matching_results(job_id: int | None = None):
    with connect() as conn:
        if job_id:
            rows = conn.execute(
                "SELECT * FROM matching_results WHERE job_id=? ORDER BY id DESC", (job_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM matching_results ORDER BY id DESC LIMIT 500"
            ).fetchall()
        return [dict(row) for row in rows]


def save_application_document(application_id: int | None, job_id: int | None, document_type: str, file_path: str, editable: str = "") -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO application_documents(application_id, job_id, document_type, file_path, editable) "
            "VALUES (?, ?, ?, ?, ?)",
            (application_id, job_id, document_type, file_path, editable),
        )
        return cursor.lastrowid


def list_application_documents(application_id: int | None = None, job_id: int | None = None):
    with connect() as conn:
        clauses = []
        params = []
        if application_id is not None:
            clauses.append("application_id=?")
            params.append(application_id)
        if job_id is not None:
            clauses.append("job_id=?")
            params.append(job_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM application_documents {where} ORDER BY id DESC", params
        ).fetchall()
        return [dict(row) for row in rows]


def record_email_log(application_id: int | None, recipient: str, status: str, gmail_message_id: str = "", error_message: str = "") -> int:
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO email_logs(application_id, recipient, status, gmail_message_id, error_message) "
            "VALUES (?, ?, ?, ?, ?)",
            (application_id, recipient, status, gmail_message_id, error_message),
        )
        return cursor.lastrowid


def list_email_logs(limit: int = 200):
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM email_logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
