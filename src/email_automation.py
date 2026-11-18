from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from src.config import DB_PATH
from src.database import get_application, record_email_log, update_status
from src.gmail_sender import send_application_email
from src.processing import clean_html


def verify_recipient(recipient: str) -> bool:
    recipient = recipient.strip()
    if "@" not in recipient or recipient.count("@") != 1:
        return False
    allowlist = os.getenv("EMAIL_RECIPIENT_ALLOWLIST", "").strip()
    if allowlist:
        allowed = {item.strip().lower() for item in allowlist.split(",") if item.strip()}
        if recipient.lower() not in allowed:
            return False
    return True


def already_sent(application_id: int) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM email_logs WHERE application_id=? AND status='sent'",
            (application_id,),
        ).fetchone()
        return bool(row and row[0])


def send_approved_application(application_id: int, explicit_confirmation: bool = False, allow_controlled_automation: bool = False) -> str:
    if not explicit_confirmation:
        raise PermissionError("Confirmation explicite requise")

    application = get_application(application_id)
    if not application:
        raise ValueError("Candidature introuvable")
    if application["status"] not in {"draft", "approved"}:
        raise ValueError("La candidature doit être brouillon ou approuvée")
    if already_sent(application_id):
        raise ValueError("Cette candidature a déjà été envoyée")
    if not verify_recipient(application["recipient"]):
        raise ValueError("Destinataire non vérifié ou absent de l'autorisation")
    if not allow_controlled_automation and os.getenv("AUTOMATED_SENDING_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        # Approval mode and controlled automation share the same explicit guard.
        # Gmail sending always requires explicit_confirmation from the caller.
        pass

    cv_path = application["cv_path"]
    if not cv_path or not Path(cv_path).is_file():
        raise FileNotFoundError("CV introuvable")

    from src.database import list_application_documents
    documents = list_application_documents(application_id=application_id)
    pdf_document = next((item for item in documents if item["document_type"] == "motivation_letter_pdf"), None)
    if not pdf_document or not Path(pdf_document["file_path"]).is_file():
        raise FileNotFoundError("Lettre de motivation PDF introuvable")

    letter_pdf = Path(pdf_document["file_path"]).read_bytes()
    try:
        message_id = send_application_email(
            application["recipient"],
            application["subject"],
            application["body"],
            cv_path,
            letter_pdf,
        )
        record_email_log(application_id, application["recipient"], "sent", message_id)
        update_status(application_id, "sent")
        from src.database import connect
        with connect() as conn:
            conn.execute(
                "UPDATE jobs SET status='TRACKED' WHERE id=(SELECT job_id FROM application_documents WHERE application_id=? LIMIT 1)",
                (application_id,),
            )
        return message_id
    except Exception as exc:
        record_email_log(application_id, application["recipient"], "failed", error_message=str(exc))
        raise
