from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import init_db, insert_job


DEMO_JOBS = [
    {
        "offer_id": "demo-data-engineer",
        "source_name": "Demonstration",
        "company": "Northstar Analytics",
        "title": "PFE Data Engineer",
        "description": "Build ETL pipelines with Python, SQL and Apache Spark. Airflow and cloud experience are appreciated.",
        "location": "Casablanca, Morocco / Remote",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "contract_type": "PFE Internship",
        "application_url": "https://example.invalid/jobs/data-engineer-pfe",
        "hr_email": "",
        "required_skills": '["python","sql","spark","airflow"]',
        "normalized_company": "northstar analytics",
        "normalized_title": "pfe data engineer",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "COLLECTED",
        "is_duplicate": 0,
        "skills": ["python", "sql", "spark", "airflow"],
    },
    {
        "offer_id": "demo-ai-engineer",
        "source_name": "Demonstration",
        "company": "Atlas Intelligent Systems",
        "title": "AI Engineer Intern",
        "description": "Contribute to LLM prototypes, model deployment and MLOps workflows using Python and PyTorch.",
        "location": "Paris, France",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "contract_type": "Internship",
        "application_url": "https://example.invalid/jobs/ai-engineer-intern",
        "hr_email": "",
        "required_skills": '["python","pytorch","llm","mlops"]',
        "normalized_company": "atlas intelligent systems",
        "normalized_title": "ai engineer intern",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "COLLECTED",
        "is_duplicate": 0,
        "skills": ["python", "pytorch", "llm", "mlops"],
    },
]


def main():
    init_db()
    added = 0
    for job in DEMO_JOBS:
        _, duplicate = insert_job(job)
        if not duplicate:
            added += 1
    print(f"Inserted {added} demonstration jobs.")


if __name__ == "__main__":
    main()
