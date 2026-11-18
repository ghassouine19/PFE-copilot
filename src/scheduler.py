from __future__ import annotations

from src.orchestration import run_pipeline


def start_scheduler(interval_minutes: int = 60):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError as exc:
        raise RuntimeError("APScheduler n'est pas installé") from exc

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_pipeline, "interval", minutes=max(5, interval_minutes), id="pfe-copilot-pipeline")
    scheduler.start()
    return scheduler
