"""Arbeitnow job board — free public JSON API.

API: https://arbeitnow.com/api/job-board-api returns `{data: [jobs], meta}`.
Listings include `slug`, `company_name`, `title`, `description`, `remote`
(bool), `url`, `tags`, `job_types`, `location`, `created_at` (unix seconds).
"""
from datetime import UTC, datetime
from typing import Any

from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper


class ArbeitnowScraper(BaseScraper):
    source = "arbeitnow"
    _endpoint = "https://arbeitnow.com/api/job-board-api"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        resp = self._client.get(self._endpoint)
        resp.raise_for_status()
        listings = resp.json().get("data", []) or []

        keywords_lc = [k.lower() for k in keywords]
        jobs: list[NormalizedJob] = []
        for item in listings:
            if not _matches(item, keywords_lc):
                continue
            jobs.append(_to_normalized(item))
            if len(jobs) >= limit:
                break
        return jobs


def _matches(item: dict[str, Any], keywords_lc: list[str]) -> bool:
    if not keywords_lc:
        return True
    parts = [
        item.get("title", ""),
        item.get("description", ""),
        " ".join(item.get("tags", []) or []),
    ]
    haystack = " ".join(parts).lower()
    return any(kw in haystack for kw in keywords_lc)


def _to_normalized(item: dict[str, Any]) -> NormalizedJob:
    posted_at: datetime | None = None
    created = item.get("created_at")
    if isinstance(created, int | float):
        posted_at = datetime.fromtimestamp(created, tz=UTC)

    return NormalizedJob(
        source="arbeitnow",
        external_id=item.get("slug"),
        source_url=item.get("url"),
        title=(item.get("title") or "").strip() or "Unknown",
        company_name=(item.get("company_name") or "").strip() or "Unknown",
        location=item.get("location"),
        description=item.get("description"),
        remote_type="remote" if item.get("remote") else None,
        job_type=(item.get("job_types") or [None])[0],
        posted_at=posted_at,
        tech_stack=list(item.get("tags", []) or []),
    )
