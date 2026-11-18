from io import BytesIO

import fitz

from src.cover_letter_generator import create_cover_letter_pdf
from src.email_generator import generate_email
from src.job_sources import import_stats
from src.matcher import match_offer


def test_matcher_detects_profile_and_pfe():
    result = match_offer("Data Engineer PFE", "Python, SQL, ETL, Apache Spark and cloud")
    assert result["role"] == "data_engineer"
    assert result["is_pfe"] is True
    assert "etl" in result["matched_keywords"]
    assert result["score"] > 0


def test_email_uses_local_template():
    result = generate_email("Acme", "Data Scientist", "en", "Sam")
    assert result["subject"].startswith("Application")
    assert "Acme" in result["body"]
    assert "Sam" in result["body"]


def test_cover_letter_pdf_is_valid_and_contains_text():
    pdf = create_cover_letter_pdf("Dear team,\n\nMy application.", "Sam", "Acme", "Data Scientist")
    assert pdf.startswith(b"%PDF")
    document = fitz.open(stream=pdf, filetype="pdf")
    text = "".join(page.get_text() for page in document)
    assert "Acme" in text
    assert "Data Scientist" in text


def test_csv_import_reports_invalid_rows_and_duplicates():
    csv = BytesIO(
        b"company,title,description,source_url\n"
        b"Acme,Data Engineer,Python SQL,https://example.com/a\n"
        b"Acme,Data Engineer,,https://example.com/b\n"
        b"Acme,Data Engineer,Python SQL,https://example.com/a\n"
    )
    result = import_stats(csv)
    assert result["total_rows"] == 3
    assert result["invalid_rows"] == 1
    assert result["duplicates"] == 1
    assert len(result["offers"]) == 1
