from src.email_generator import generate_email, validate_email_address


def test_email_validation():
    assert validate_email_address("recrutement@example.com")
    assert not validate_email_address("not-an-email")


def test_local_email_generator_supports_languages():
    fr = generate_email("CGI", "Data Engineer", "fr", "Candidate")
    en = generate_email("CGI", "Data Engineer", "en", "Candidate")
    assert "Candidature PFE" in fr["subject"]
    assert "Application" in en["subject"]
    assert "CGI" in fr["body"]
