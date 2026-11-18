from __future__ import annotations

from pathlib import Path

from src.config import ROOT
from src.cover_letter_generator import create_cover_letter_pdf, generate_cover_letter
from src.cv_selector import select_cv
from src.email_generator import generate_email
from src.database import add_application, save_application_document


def generate_application(job: dict, match: dict, candidate: str = "Candidat", language: str = "fr") -> dict:
    role = match["role"]
    cv_path = select_cv(role)
    if cv_path is None:
        raise FileNotFoundError(f"Aucun CV disponible pour le profil {role}")

    letter_text = generate_cover_letter(
        candidate,
        match["role_label"],
        job["company"],
        language,
    )
    email = generate_email(
        job["company"],
        match["role_label"],
        language,
        candidate,
        use_ai=False,
    )
    application_id = add_application({
        "company": job["company"],
        "title": job["title"],
        "recipient": job.get("hr_email", ""),
        "source_url": job.get("application_url", ""),
        "description": job.get("description", ""),
        "role": role,
        "score": int(match["score"]),
        "language": language,
        "subject": email["subject"],
        "body": email["body"],
        "cv_path": str(cv_path),
        "status": "draft",
    })

    document_dir = ROOT / "data" / "generated"
    document_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = document_dir / f"application_{application_id}.pdf"
    pdf_path.write_bytes(create_cover_letter_pdf(
        letter_text,
        candidate=candidate,
        company=job["company"],
        position=job["title"],
    ))
    save_application_document(application_id, job["id"], "motivation_letter_pdf", str(pdf_path), letter_text)
    save_application_document(application_id, job["id"], "email", "", email["body"])
    save_application_document(application_id, job["id"], "cv", str(cv_path), "")
    return {
        "application_id": application_id,
        "subject": email["subject"],
        "body": email["body"],
        "letter": letter_text,
        "letter_pdf": str(pdf_path),
        "cv_path": str(cv_path),
    }
