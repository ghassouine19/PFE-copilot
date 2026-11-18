
import os
from pathlib import Path

import requests

from src.config import TEMPLATES_DIR


def _load_template(language: str) -> str:
    template_name = "email_en.txt" if language == "en" else "email_fr.txt"
    return (TEMPLATES_DIR / template_name).read_text(encoding="utf-8")


def _generate_ai_email(company: str, role: str, language: str, candidate: str) -> dict | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    prompt = (
        f"Write a concise professional job application email in {language}. "
        f"Candidate: {candidate}. Company: {company}. Role: {role}. "
        "Return only two lines prefixed with Subject: and Body:, then the body."
    )
    response = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
        timeout=30,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"].strip()
    subject_line, _, body = content.partition("\n")
    if subject_line.lower().startswith("subject:") and body.strip():
        return {"subject": subject_line.split(":", 1)[1].strip(), "body": body.replace("Body:", "", 1).strip()}
    return None


def generate_email(
    company: str,
    role: str,
    language: str = "fr",
    candidate: str = "[Ton nom]",
    use_ai: bool = False,
) -> dict:
    if language not in {"fr", "en"}:
        raise ValueError("Langue non prise en charge.")
    if use_ai:
        ai_result = _generate_ai_email(company, role, language, candidate)
        if ai_result:
            return ai_result

    template = _load_template(language)
    body = template.format(company=company, role=role, candidate=candidate)
    if language == "en":
        subject = f"Application for a final-year internship - {role}"
    else:
        subject = f"Candidature PFE - {role} - Master BD2C"

    return {"subject": subject, "body": body}
