"""LinkedIn emergency fallback via Apify actor.

JobSpy is the primary LinkedIn scraper (free, direct). This Apify-based
fallback is DISABLED by default (APIFY_LINKEDIN_ENABLED=false) and is only
toggled on manually if JobSpy gets detection-blocked.

Keeping this gated prevents accidental Apify credit burn — the actor is
expensive (~$0.10 per 100 jobs) compared to JobSpy's $0.
"""
from datetime import datetime
from typing import Any

from apify_client import ApifyClient

from app.config import settings
from app.schemas.scraper import NormalizedJob
from app.scrapers.base import ScraperDisabled
from app.services.encryption import decrypt_token


class LinkedInApifyScraper:
    source = "linkedin_apify"

    def __init__(self, api_token_encrypted: str, client_factory=ApifyClient) -> None:
        if not settings.APIFY_LINKEDIN_ENABLED:
            raise ScraperDisabled(
                "LinkedIn Apify fallback is disabled; set APIFY_LINKEDIN_ENABLED=true "
                "only if JobSpy direct scraping is detection-blocked"
            )
        self._token = decrypt_token(api_token_encrypted)
        self._client_factory = client_factory

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        client = self._client_factory(self._token)
        run_input: dict[str, Any] = {
            "keywords": " ".join(keywords),
            "locations": locations or ["Remote"],
            "rows": limit,
        }
        run = client.actor(settings.APIFY_LINKEDIN_ACTOR).call(run_input=run_input)
        if run is None or not run.get("defaultDatasetId"):
            return []

        items = client.dataset(run["defaultDatasetId"]).list_items().items
        return [_to_normalized(item) for item in items[:limit]]


def _to_normalized(item: dict[str, Any]) -> NormalizedJob:
    posted_at: datetime | None = None
    if raw := item.get("postedAt") or item.get("listedAt"):
        try:
            posted_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            posted_at = None

    return NormalizedJob(
        source="linkedin_apify",
        external_id=str(item.get("jobId") or item.get("id") or "") or None,
        source_url=item.get("url") or item.get("jobUrl"),
        title=(item.get("title") or "").strip() or "Unknown",
        company_name=(item.get("companyName") or item.get("company") or "Unknown").strip(),
        location=item.get("location"),
        description=item.get("description") or item.get("jobDescription"),
        remote_type="remote" if "remote" in str(item.get("location", "")).lower() else None,
        posted_at=posted_at,
    )
