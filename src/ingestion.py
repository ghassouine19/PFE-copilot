from __future__ import annotations

import csv
import io
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import pandas as pd
import requests
from bs4 import BeautifulSoup


class BaseConnector(ABC):
    name: str
    source_type: str

    def __init__(self, session: requests.Session | None = None, delay_seconds: float = 1.0):
        self.session = session or requests.Session()
        self.delay_seconds = delay_seconds

    @abstractmethod
    def collect(self) -> list[dict]:
        raise NotImplementedError

    def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return True
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        robots = RobotFileParser()
        try:
            robots.set_url(robots_url)
            robots.read()
            return robots.can_fetch("*", url)
        except Exception:
            return False


class CSVConnector(BaseConnector):
    name = "CSV"
    source_type = "csv"

    def __init__(self, file, name: str = "CSV", delay_seconds: float = 0.0):
        super().__init__(delay_seconds=delay_seconds)
        self.file = file
        self.name = name

    def collect(self) -> list[dict]:
        data = self.file.getvalue() if hasattr(self.file, "getvalue") else self.file
        if isinstance(data, bytes):
            data = io.BytesIO(data)
        elif isinstance(data, str):
            data = io.StringIO(data)
        frame = pd.read_csv(data).fillna("")
        required = {"company", "title", "description"}
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes: {', '.join(sorted(missing))}")
        jobs = frame.to_dict(orient="records")
        return [
            {**job, "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            for job in jobs
        ]


class RSSConnector(BaseConnector):
    name = "RSS"
    source_type = "rss"

    def __init__(self, url: str, session: requests.Session | None = None, delay_seconds: float = 1.0):
        super().__init__(session=session, delay_seconds=delay_seconds)
        self.url = url
        self.name = url

    def collect(self) -> list[dict]:
        if not self._allowed_by_robots(self.url):
            raise PermissionError(f"robots.txt interdit la collecte de {self.url}")
        response = self.session.get(self.url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "xml")
        jobs = []
        for item in soup.find_all(["item", "entry"]):
            title = item.find(["title"])
            link = item.find(["link"])
            if link and link.get("href"):
                application_url = link["href"]
            elif link:
                application_url = link.get_text(strip=True)
            else:
                application_url = ""
            description = item.find(["description", "summary", "content"])
            published = item.find(["pubDate", "published", "updated"])
            jobs.append({
                "company": "",
                "title": title.get_text(" ", strip=True) if title else "",
                "description": description.get_text(" ", strip=True) if description else "",
                "application_url": application_url,
                "published_at": published.get_text(" ", strip=True) if published else "",
                "collected_at": datetime.utcnow().isoformat(timespec="seconds"),
            })
            time.sleep(self.delay_seconds)
        return jobs


class WebConnector(BaseConnector):
    name = "Web"
    source_type = "web"

    def __init__(self, url: str, session: requests.Session | None = None, delay_seconds: float = 1.0):
        super().__init__(session=session, delay_seconds=delay_seconds)
        self.url = url
        self.name = url

    def collect(self) -> list[dict]:
        if not self._allowed_by_robots(self.url):
            raise PermissionError(f"robots.txt interdit la collecte de {self.url}")
        response = self.session.get(self.url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []
        for container in soup.select("[class*=job], article"):
            title_node = container.select_one("h1, h2, h3, [class*=title]")
            if not title_node:
                continue
            link_node = container.find("a", href=True)
            description_node = container.select_one("[class*=description], p")
            location_node = container.select_one("[class*=location]")
            jobs.append({
                "company": self._infer_company(soup),
                "title": title_node.get_text(" ", strip=True),
                "description": description_node.get_text(" ", strip=True) if description_node else "",
                "location": location_node.get_text(" ", strip=True) if location_node else "",
                "application_url": urljoin(self.url, link_node["href"]) if link_node else self.url,
                "collected_at": datetime.utcnow().isoformat(timespec="seconds"),
            })
            time.sleep(self.delay_seconds)
        return jobs

    @staticmethod
    def _infer_company(soup: BeautifulSoup) -> str:
        for node in soup.find_all(["meta", "title"]):
            if node.name == "meta" and node.get("property") in {"og:site_name", "og:title"}:
                return node.get("content", "").strip()
        title = soup.find("title")
        return title.get_text(" ", strip=True).split("|")[0].strip() if title else ""


def collect_and_persist(connector: BaseConnector) -> dict:
    from src.database import (
        init_db,
        insert_raw_job,
        insert_job,
        upsert_job_source,
    )
    from src.processing import deduplicate_jobs, process_job, validate_job
    import json

    init_db()
    source_id = upsert_job_source(connector.name, connector.source_type)
    collected = connector.collect()
    stats = {"collected": len(collected), "raw_saved": 0, "processed": 0, "duplicates": 0, "invalid": 0}
    processed_jobs = []

    for raw in collected:
        offer_id = ""
        temp = process_job(raw, connector.name)
        offer_id = temp["offer_id"]
        insert_raw_job(source_id, json.dumps(raw, ensure_ascii=False), str(raw.get("collected_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))), offer_id, source_id)
        stats["raw_saved"] += 1

        valid, _ = validate_job(temp)
        if valid:
            processed_jobs.append(temp)
        else:
            stats["invalid"] += 1

    from src.database import list_jobs
    deduplicated = deduplicate_jobs(processed_jobs, list_jobs(limit=10000))
    for job in deduplicated:
        _, duplicate = insert_job(job)
        if duplicate or job["is_duplicate"]:
            stats["duplicates"] += 1
        else:
            stats["processed"] += 1
    return stats
