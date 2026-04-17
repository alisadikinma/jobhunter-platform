"""HiringCafe — best-effort scraper against the site's internal JSON API.

hiring.cafe is a JS-rendered SPA; there is no public/documented API. The
site's frontend talks to `https://hiring.cafe/api/search-jobs` (POST) and
that shape is what we target here. This contract is undocumented and
may break at any time — on any error we return `[]` rather than
propagating, so the aggregator keeps running.

If this ever breaks consistently, disable by removing "hiring_cafe" from
scrape_configs.sources rather than raising — other scrapers should not
be gated on this source.
"""
import logging
from datetime import datetime
from typing import Any

import httpx

from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper

log = logging.getLogger(__name__)

_ENDPOINT = "https://hiring.cafe/api/search-jobs"


class HiringCafeScraper(BaseScraper):
    source = "hiring_cafe"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        payload: dict[str, Any] = {
            "size": min(limit, 50),
            "page": 0,
            "searchState": {
                "searchQuery": " ".join(keywords),
                "locations": locations or [],
                "workplaceTypes": ["Remote"],
            },
        }
        try:
            resp = self._client.post(_ENDPOINT, json=payload)
            resp.raise_for_status()
        except (httpx.HTTPError, ValueError) as e:
            log.warning("hiring_cafe: request failed, returning empty (%s)", e)
            return []

        try:
            body = resp.json()
        except ValueError:
            return []

        listings = body.get("results") or body.get("data") or []
        jobs: list[NormalizedJob] = []
        for item in listings:
            job = _to_normalized(item)
            if job is not None:
                jobs.append(job)
            if len(jobs) >= limit:
                break
        return jobs


def _to_normalized(item: dict[str, Any]) -> NormalizedJob | None:
    title = (item.get("job_title") or item.get("title") or "").strip()
    if not title:
        return None
    company = (
        item.get("company_name")
        or (item.get("company") or {}).get("name")
        or "Unknown"
    )
    posted_at: datetime | None = None
    for key in ("posted_at", "created_at", "date_posted"):
        if raw := item.get(key):
            try:
                posted_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                break
            except (ValueError, TypeError):
                continue

    return NormalizedJob(
        source="hiring_cafe",
        external_id=str(item.get("id") or item.get("job_id") or "") or None,
        source_url=item.get("apply_url") or item.get("url"),
        title=title[:200],
        company_name=str(company).strip()[:150],
        location=item.get("location") or "Remote",
        description=item.get("description") or item.get("job_description"),
        remote_type="remote",
        posted_at=posted_at,
        tech_stack=list(item.get("tags") or item.get("skills") or []),
    )
