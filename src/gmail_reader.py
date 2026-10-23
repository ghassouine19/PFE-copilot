
import base64
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS_FILE = ROOT / "credentials.json"
TOKEN_FILE = ROOT / "token.json"


SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

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
    """Décode le contenu d'une partie MIME Gmail."""
    data = part.get("body", {}).get("data")

    if not data:
        return ""

    try:
        padding = "=" * (-len(data) % 4)
        decoded = base64.urlsafe_b64decode(data + padding)
        return decoded.decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return ""


def extract_message(message: dict) -> dict:
    """Extrait les métadonnées et le texte d'un e-mail Gmail."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    header_map = {
        h["name"].lower(): h["value"]
        for h in headers
    }

    plain_parts = []
    html_parts = []

    def walk(part: dict):
        mime = part.get("mimeType", "").lower()
        content = decode_part(part)

        if content:
            if mime == "text/plain":
                plain_parts.append(content)
            elif mime == "text/html":
                html_parts.append(content)

        for child in part.get("parts", []):
            walk(child)

    walk(payload)

    # Priorité au texte brut.
    plain_text = "\n".join(plain_parts).strip()

    if plain_text:
        body_text = plain_text
    elif html_parts:
        # Utilise le HTML comme solution de repli.
        html = "\n".join(html_parts)
        body_text = BeautifulSoup(html, "html.parser").get_text(
            separator="\n",
            strip=True
        )
    else:
        body_text = ""

    return {
        "message_id": message.get("id", ""),
        "sender": header_map.get("from", ""),
        "subject": header_map.get("subject", ""),
        "date": header_map.get("date", ""),
        "body": body_text
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
