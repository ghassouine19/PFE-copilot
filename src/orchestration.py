from __future__ import annotations

import json
import os
import time
from datetime import datetime

from src.config import DB_PATH, PROFILE_PATH
from src.database import (
    create_pipeline_run,
    finish_pipeline_run,
    get_application,
    get_job,
    init_db,
    list_jobs,
    record_pipeline_task,
    save_matching_result,
    update_job_status,
)
from src.filtering import DEFAULT_PREFERENCES, apply_filters, load_preferences
from src.generation import generate_application
from src.matcher import match_offer
from src.processing import validate_job


STAGE_ORDER = [
    "COLLECTED",
    "NORMALIZED",
    "VALIDATED",
    "FILTERED",
    "MATCHED",
    "CV_SELECTED",
    "APPLICATION_GENERATED",
    "PENDING_APPROVAL",
    "SENT",
    "TRACKED",
]


def run_job_stage(job_id: int, stage: str, run_id: int | None = None, preferences: dict | None = None, max_attempts: int = 2) -> dict:
    preferences = preferences or load_preferences(PROFILE_PATH.with_name("preferences.json"))
    job = get_job(job_id)
    if not job:
        raise ValueError("Offre introuvable")

    last_error = ""
    for attempt in range(1, max_attempts + 1):
        try:
            if stage == "VALIDATED":
                valid, message = validate_job(job)
                if not valid:
                    raise ValueError(message)
                update_job_status(job_id, "VALIDATED")
            elif stage == "FILTERED":
                match = match_offer(job["title"], job["description"])
                kept, reasons = apply_filters(job, preferences, match["score"])
                if not kept:
                    update_job_status(job_id, "REJECTED")
                    if run_id is not None:
                        record_pipeline_task(run_id, job_id, stage, "SUCCESS", "; ".join(reasons), attempts=attempt)
                    return {"job_id": job_id, "stage": stage, "status": "REJECTED", "reasons": reasons}
                update_job_status(job_id, "FILTERED")
            elif stage == "MATCHED":
                match = match_offer(job["title"], job["description"])
                save_matching_result(job_id, match)
                update_job_status(job_id, "MATCHED")
                return {"job_id": job_id, "stage": stage, "status": "SUCCESS", "match": match}
            elif stage == "CV_SELECTED":
                from src.cv_selector import select_cv
                match = match_offer(job["title"], job["description"])
                cv = select_cv(match["role"])
                if cv is None:
                    raise FileNotFoundError("CV absent pour le profil détecté")
                update_job_status(job_id, "CV_SELECTED")
            elif stage == "APPLICATION_GENERATED":
                import sqlite3
                with sqlite3.connect(DB_PATH) as conn:
                    existing = conn.execute(
                        "SELECT id FROM applications WHERE source_url=? AND source_url<>''",
                        (job["application_url"],),
                    ).fetchone()
                if existing:
                    update_job_status(job_id, "PENDING_APPROVAL")
                    return {"job_id": job_id, "stage": stage, "status": "SUCCESS", "application_id": existing[0], "deduplicated": True}
                match = match_offer(job["title"], job["description"])
                application = generate_application(job, match)
                update_job_status(job_id, "APPLICATION_GENERATED")
                update_job_status(job_id, "PENDING_APPROVAL")
                return {"job_id": job_id, "stage": stage, "status": "SUCCESS", "application": application}
            elif stage == "PENDING_APPROVAL":
                update_job_status(job_id, "PENDING_APPROVAL")
            else:
                update_job_status(job_id, stage)

            if run_id is not None:
                record_pipeline_task(run_id, job_id, stage, "SUCCESS", attempts=attempt)
            return {"job_id": job_id, "stage": stage, "status": "SUCCESS"}
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_attempts:
                time.sleep(0.05 * attempt)

    update_job_status(job_id, "FAILED")
    if run_id is not None:
        record_pipeline_task(run_id, job_id, stage, "FAILED", last_error, attempts=max_attempts)
    return {"job_id": job_id, "stage": stage, "status": "FAILED", "error": last_error}


def rerun_failed_job(job_id: int) -> dict:
    job = get_job(job_id)
    if not job:
        raise ValueError("Offre introuvable")
    stage = "VALIDATED" if job["status"] in {"FAILED", "COLLECTED", "NORMALIZED"} else "PENDING_APPROVAL"
    return run_job_stage(job_id, stage)


def run_pipeline(job_ids: list[int] | None = None, preferences: dict | None = None) -> dict:
    init_db()
    run_id = create_pipeline_run()
    statistics = {"COLLECTED": 0, "NORMALIZED": 0, "VALIDATED": 0, "FILTERED": 0,
                  "MATCHED": 0, "CV_SELECTED": 0, "APPLICATION_GENERATED": 0,
                  "PENDING_APPROVAL": 0, "REJECTED": 0, "FAILED": 0, "DUPLICATE": 0}

    jobs = [get_job(job_id) for job_id in job_ids] if job_ids else list_jobs(limit=10000)
    for job in jobs:
        if not job:
            continue
        if job["is_duplicate"]:
            statistics["DUPLICATE"] += 1
            record_pipeline_task(run_id, job["id"], "DUPLICATE", "SUCCESS", "Offre dupliquée")
            continue

        stages = ["VALIDATED", "FILTERED", "MATCHED", "CV_SELECTED", "APPLICATION_GENERATED"]
        stop = False
        for stage in stages:
            result = run_job_stage(job["id"], stage, run_id, preferences)
            status = result["status"]
            if status == "FAILED":
                statistics["FAILED"] += 1
                stop = True
                break
            if stage == "FILTERED" and get_job(job["id"])["status"] == "REJECTED":
                statistics["REJECTED"] += 1
                stop = True
                break
            statistics[stage] = statistics.get(stage, 0) + 1
        if not stop:
            statistics["PENDING_APPROVAL"] += 1

    finish_pipeline_run(run_id, "COMPLETED", json.dumps(statistics, ensure_ascii=False))
    return {"run_id": run_id, "statistics": statistics}
