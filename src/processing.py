from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

from bs4 import BeautifulSoup
import pandas as pd


SKILL_VOCABULARY = [
    "python", "sql", "spark", "apache spark", "airflow", "etl", "elt",
    "pandas", "scikit-learn", "machine learning", "deep learning",
    "tensorflow", "pytorch", "power bi", "tableau", "pentaho",
    "docker", "kubernetes", "aws", "azure", "gcp", "mongodb",
    "postgresql", "mysql", "snowflake", "databricks", "dbt",
    "git", "linux", "api", "rest", "llm", "nlp", "tensorflow",
]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or "").lower())
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = re.sub(r"\s+", " ", value)
    return re.sub(r"[^a-z0-9+#./ -]", " ", value).strip()


def clean_html(value: str) -> str:
    if not value:
        return ""
    return BeautifulSoup(str(value), "html.parser").get_text(" ", strip=True)


def extract_skills(text: str) -> list[str]:
    normalized = normalize_text(text)
    found = []
    for skill in SKILL_VOCABULARY:
        if skill in normalized:
            found.append(skill)
    return sorted(set(found))


def validate_job(job: dict) -> tuple[bool, str]:
    for field in ("company", "title"):
        if not str(job.get(field, "")).strip():
            return False, f"Champ requis manquant: {field}"
    if not str(job.get("description", "")).strip():
        return False, "Champ requis manquant: description"
    url = str(job.get("application_url", "") or job.get("source_url", ""))
    if url and not url.startswith(("http://", "https://")):
        return False, "URL d'application invalide"
    return True, ""


def make_offer_id(job: dict) -> str:
    url = str(job.get("application_url", "") or job.get("source_url", "")).strip()
    identity = url or "|".join(
        (
            normalize_text(job.get("company", "")),
            normalize_text(job.get("title", "")),
            normalize_text(clean_html(job.get("description", "")))[:2000],
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def process_job(job: dict, source_name: str = "unknown") -> dict:
    description = clean_html(job.get("description", ""))
    company = str(job.get("company", "")).strip()
    title = str(job.get("title", "")).strip()
    processed = {
        "offer_id": make_offer_id(job),
        "source_id": job.get("source_id"),
        "source_name": source_name,
        "company": company,
        "title": title,
        "description": description,
        "location": str(job.get("location", "")).strip(),
        "published_at": str(job.get("published_at", "") or job.get("publication_date", "")).strip(),
        "contract_type": str(job.get("contract_type", "")).strip(),
        "application_url": str(job.get("application_url", "") or job.get("source_url", "")).strip(),
        "hr_email": str(job.get("hr_email", "") or job.get("recipient", "")).strip(),
        "required_skills": "[]",
        "normalized_company": normalize_text(company),
        "normalized_title": normalize_text(title),
        "collected_at": str(job.get("collected_at", "") or datetime.now(timezone.utc).isoformat(timespec="seconds")),
        "status": "NORMALIZED",
        "is_duplicate": 0,
        "skills": extract_skills(f"{title} {description}"),
    }
    import json
    processed["required_skills"] = json.dumps(processed["skills"], ensure_ascii=False)
    return processed


def content_similarity(left: dict, right: dict) -> float:
    left_text = normalize_text(f"{left.get('company', '')} {left.get('title', '')} {left.get('description', '')[:1200]}")
    right_text = normalize_text(f"{right.get('company', '')} {right.get('title', '')} {right.get('description', '')[:1200]}")
    return SequenceMatcher(None, left_text, right_text).ratio()


def deduplicate_jobs(new_jobs: list[dict], existing_jobs: list[dict], threshold: float = 0.88) -> list[dict]:
    output = []
    existing_urls = {
        str(job.get("application_url", "")).strip()
        for job in existing_jobs
        if job.get("application_url")
    }
    existing_signatures = [
        (normalize_text(job.get("company", "")), normalize_text(job.get("title", "")), job)
        for job in existing_jobs
    ]
    seen_ids = set()

    for job in new_jobs:
        result = dict(job)
        url = str(job.get("application_url", "")).strip()
        duplicate = url and url in existing_urls
        if not duplicate:
            signature = (normalize_text(job.get("company", "")), normalize_text(job.get("title", "")))
            for company, title, existing in existing_signatures:
                if signature == (company, title) and content_similarity(job, existing) >= threshold:
                    duplicate = True
                    break
        if not duplicate and job["offer_id"] in seen_ids:
            duplicate = True
        if duplicate:
            result["is_duplicate"] = 1
            result["status"] = "DUPLICATE"
        seen_ids.add(job["offer_id"])
        output.append(result)
    return output


def jobs_to_dataframe(jobs: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(jobs)
