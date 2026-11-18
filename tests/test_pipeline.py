from io import BytesIO

import pytest

from src.database import init_db
from src.filtering import apply_filters, DEFAULT_PREFERENCES
from src.ingestion import CSVConnector
from src.processing import deduplicate_jobs, normalize_text, process_job, validate_job


class CSVUpload:
    def __init__(self, content):
        self.content = content

    def getvalue(self):
        return self.content


def test_csv_connector_collects_rows():
    connector = CSVConnector(
        CSVUpload(b"company,title,description,location\nAcme,Data Engineer,Python SQL,Remote"),
        name="Test CSV",
    )
    jobs = connector.collect()
    assert len(jobs) == 1
    assert jobs[0]["company"] == "Acme"


def test_normalization_validation_and_deduplication():
    raw = {
        "company": "  ACME  ",
        "title": "Data Engineer",
        "description": "<p>Python, <b>SQL</b> and Spark</p>",
        "application_url": "https://example.com/job/1",
    }
    processed = process_job(raw)
    assert normalize_text(processed["company"]) == "acme"
    assert "python" in processed["skills"]
    assert "sql" in processed["skills"]
    assert validate_job(processed)[0]

    duplicate = deduplicate_jobs([dict(processed)], [dict(processed)])
    assert duplicate[0]["is_duplicate"] == 1


def test_filter_rejects_exclusion_and_honors_score():
    job = {
        "title": "Senior Data Engineer",
        "description": "Python SQL",
        "location": "Casablanca",
    }
    preferences = dict(DEFAULT_PREFERENCES)
    preferences["exclusion_keywords"] = ["senior"]
    kept, reasons = apply_filters(job, preferences, score=50)
    assert not kept
    assert reasons


def test_sqlite_pipeline_schema(tmp_path, monkeypatch):
    from src import database

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "pipeline.db")
    database.init_db()
    source_id = database.upsert_job_source("CSV test", "csv")
    assert source_id > 0
    assert database.job_stats()["total"] == 0
