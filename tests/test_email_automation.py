from src import email_automation


def test_recipient_allowlist(monkeypatch):
    monkeypatch.setenv("EMAIL_RECIPIENT_ALLOWLIST", "jobs@example.com")
    assert email_automation.verify_recipient("jobs@example.com")
    assert not email_automation.verify_recipient("other@example.com")


def test_duplicate_send_guard(tmp_path, monkeypatch):
    from src import database
    from src import email_automation

    monkeypatch.setattr(database, "DB_PATH", tmp_path / "email.db")
    monkeypatch.setattr(email_automation, "DB_PATH", tmp_path / "email.db")
    database.init_db()
    application_id = database.add_application({
        "company": "Acme",
        "title": "Data Engineer",
        "recipient": "jobs@example.com",
        "role": "data_engineer",
        "score": 80,
        "language": "fr",
        "subject": "Candidature",
        "body": "Bonjour",
        "cv_path": "",
        "status": "draft",
    })
    assert not email_automation.already_sent(application_id)
