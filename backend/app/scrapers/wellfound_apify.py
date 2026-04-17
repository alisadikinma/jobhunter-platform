"""Wellfound (AngelList Talent) scraper via Apify actor.

Wellfound blocks direct scraping aggressively; JobSpy doesn't cover it. An
Apify actor with residential proxies handles it cleanly. This is the primary
use-case for the Apify pool.

Unlike the free-API scrapers, this one:
- requires a reserved account from ApifyPool.acquire_account() before calling
- calls record_usage() with the run's actual cost and status
- is typically invoked by services/scraper_service.py, not directly
"""
from datetime import datetime
from typing import Any

from apify_client import ApifyClient

from app.config import settings
from app.schemas.scraper import NormalizedJob
from app.services.encryption import decrypt_token


class WellfoundApifyScraper:
    """Caller must supply a decrypted token and handle credit accounting."""

    source = "wellfound"

    def __init__(self, api_token_encrypted: str, client_factory=ApifyClient) -> None:
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
            "keywords": keywords,
            "locations": locations or ["Remote"],
            "maxItems": limit,
        }
        run = client.actor(settings.APIFY_WELLFOUND_ACTOR).call(run_input=run_input)
        if run is None:
            return []

        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return []

        items = client.dataset(dataset_id).list_items().items
        return [_to_normalized(item) for item in items[:limit]]


def _to_normalized(item: dict[str, Any]) -> NormalizedJob:
    posted_at: datetime | None = None
    for key in ("postedAt", "created_at", "datePosted"):
        if raw := item.get(key):
            try:
                posted_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                break
            except (ValueError, TypeError):
                continue

    return NormalizedJob(
        source="wellfound",
        external_id=str(item.get("id") or item.get("slug") or "") or None,
        source_url=item.get("url") or item.get("applyUrl"),
        title=(item.get("title") or item.get("jobTitle") or "").strip() or "Unknown",
        company_name=(
            item.get("companyName")
            or (item.get("company") or {}).get("name")
            or "Unknown"
        ).strip(),
        location=item.get("location") or "Remote",
        description=item.get("description") or item.get("jobDescription"),
        salary_min=_as_int(item.get("salaryMin") or item.get("salary_min")),
        salary_max=_as_int(item.get("salaryMax") or item.get("salary_max")),
        remote_type="remote" if item.get("remote") or "remote" in str(item.get("location", "")).lower() else None,
        posted_at=posted_at,
        tech_stack=list(item.get("skills") or item.get("tags") or []),
    )


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
