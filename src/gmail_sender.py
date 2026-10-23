
import base64
import mimetypes
from email.message import EmailMessage
from pathlib import Path

from src.gmail_reader import get_gmail_service


def send_application_email(
    recipient: str,
    subject: str,
    body: str,
    cv_path: str,
    cover_letter_pdf: bytes,
) -> str:
    """
    Envoie un e-mail avec le CV et la lettre de motivation en PDF.
    Retourne l'identifiant Gmail du message envoyé.
    """

    recipient = recipient.strip()

    if not recipient or "@" not in recipient:
        raise ValueError("Adresse e-mail du destinataire invalide.")

    cv = Path(cv_path)

    if not cv.is_file():
        raise FileNotFoundError(
            f"Le CV sélectionné est introuvable : {cv}"
        )

    if cv.suffix.lower() != ".pdf":
        raise ValueError("Le CV sélectionné doit être un fichier PDF.")

    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    cv_content_type, _ = mimetypes.guess_type(cv.name)
    if not cv_content_type:
        cv_content_type = "application/pdf"

    cv_main_type, cv_sub_type = cv_content_type.split("/", 1)

    message.add_attachment(
        cv.read_bytes(),
        maintype=cv_main_type,
        subtype=cv_sub_type,
        filename=cv.name,
    )

    message.add_attachment(
        cover_letter_pdf,
        maintype="application",
        subtype="pdf",
        filename="Lettre_de_motivation_PFE.pdf",
    )

    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode("ascii")

    service = get_gmail_service()

    result = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={"raw": raw_message},
        )
        .execute()
    )

    return result["id"]
