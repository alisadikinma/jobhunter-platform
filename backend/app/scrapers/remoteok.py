"""RemoteOK scraper — free public JSON feed.

API: https://remoteok.com/api returns a JSON array. The first element is a
legal/meta header that must be skipped. Each listing has keys like `id`,
`position`, `company`, `tags`, `description`, `url`, `location`,
`salary_min`, `salary_max`, `date`.
"""
from datetime import datetime
from typing import Any

from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper


class RemoteOKScraper(BaseScraper):
    source = "remoteok"
    _endpoint = "https://remoteok.com/api"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        resp = self._client.get(
            self._endpoint,
            headers={"User-Agent": "JobHunter/0.1 (+https://jobs.alisadikinma.com)"},
        )
        resp.raise_for_status()
        data = resp.json()
        # First element is the legal header; skip it.
        listings = [item for item in data if isinstance(item, dict) and "position" in item]
        jobs: list[NormalizedJob] = []
        keywords_lc = [k.lower() for k in keywords]
        for item in listings:
            if not _matches_keywords(item, keywords_lc):
                continue
            jobs.append(_to_normalized(item))
            if len(jobs) >= limit:
                break
        return jobs


def _matches_keywords(item: dict[str, Any], keywords_lc: list[str]) -> bool:
    if not keywords_lc:
        return True
    haystack_parts = [
        item.get("position", ""),
        item.get("description", ""),
        " ".join(item.get("tags", []) or []),
    ]
    haystack = " ".join(p for p in haystack_parts if p).lower()
    return any(kw in haystack for kw in keywords_lc)


def _to_normalized(item: dict[str, Any]) -> NormalizedJob:
    posted_at: datetime | None = None
    if raw_date := item.get("date"):
        try:
            posted_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            posted_at = None

    return NormalizedJob(
        source="remoteok",
        external_id=str(item.get("id")) if item.get("id") is not None else None,
        source_url=item.get("url"),
        title=item.get("position", "").strip() or "Unknown",
        company_name=item.get("company", "").strip() or "Unknown",
        location=item.get("location") or "Remote",
        description=item.get("description"),
        salary_min=_as_int(item.get("salary_min")),
        salary_max=_as_int(item.get("salary_max")),
        remote_type="remote",
        posted_at=posted_at,
        tech_stack=list(item.get("tags", []) or []),
    )


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
