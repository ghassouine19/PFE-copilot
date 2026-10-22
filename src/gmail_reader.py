
import base64
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(TOKEN_FILE), SCOPES
        )

    if creds and not creds.has_scopes(SCOPES):
        creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    "Ajoute credentials.json à la racine du projet."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def decode_part(part: dict) -> str:
    data = part.get("body", {}).get("data")

    if data:
        return base64.urlsafe_b64decode(data).decode(
            "utf-8", errors="replace"
        )

    return ""


def extract_message(message: dict) -> dict:
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    header_map = {
        h["name"].lower(): h["value"]
        for h in headers
    }

    body_parts = []

    def walk(part):
        mime = part.get("mimeType", "")

        # Priorité au texte brut, sans récupérer les pièces jointes.
        if mime == "text/plain":
            body_parts.append(decode_part(part))

        for child in part.get("parts", []):
            walk(child)

    walk(payload)

    return {
        "message_id": message.get("id", ""),
        "sender": header_map.get("from", ""),
        "subject": header_map.get("subject", ""),
        "date": header_map.get("date", ""),
        "body": "\n".join(body_parts).strip(),
    }


def search_offer_emails(max_results: int = 20) -> list[dict]:
    service = get_gmail_service()

    query = (
        'newer_than:1y '
        '{PFE "stage de fin d études" '
        '"stage de fin d\'études" "stage pré-embauche"}'
    )

    response = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    results = []

    for item in response.get("messages", []):
        message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="full",
        ).execute()

        results.append(extract_message(message))

    return results
