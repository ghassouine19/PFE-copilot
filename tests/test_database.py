from src import database


def test_application_lifecycle_uses_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "applications.db")
    database.init_db()
    application_id = database.add_application({
        "company": "Acme",
        "title": "Data Engineer",
        "role": "data_engineer",
        "score": 80,
        "language": "fr",
        "subject": "Candidature",
        "body": "Bonjour",
        "status": "draft",
    })
    assert database.list_applications("Acme")[0]["id"] == application_id
    database.update_status(application_id, "approved")
    assert database.get_application(application_id)["status"] == "approved"
    assert database.application_stats()["total"] == 1
