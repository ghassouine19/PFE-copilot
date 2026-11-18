from src import database


def test_opportunity_deduplication_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    offer = {
        "company": "Example",
        "title": "Data Engineer",
        "description": "Python SQL Spark",
        "source": "manual",
    }
    first_id, created = database.upsert_opportunity(offer)
    second_id, duplicate = database.upsert_opportunity(offer)
    assert created is True
    assert duplicate is False
    assert first_id == second_id

    database.update_opportunity(first_id, status="Applied", score=75)
    rows = database.list_opportunities()
    assert len(rows) == 1
    assert rows[0]["status"] == "Applied"
    assert rows[0]["score"] == 75


def test_dashboard_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "metrics.db")
    database.init_db()
    database.upsert_opportunity({
        "company": "A",
        "title": "Engineer",
        "description": "Python",
    })
    metrics = database.dashboard_metrics()
    assert metrics["total"] == 1
    assert metrics["conversion_rate"] == 0.0
