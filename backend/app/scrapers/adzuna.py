"""Adzuna job search API.

Docs: https://developer.adzuna.com/docs/search
Endpoint: https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
Requires `app_id` + `app_key`. Free tier allows ~250 calls/day.

Country is inferred per target region; default is "us". Uses `what` param
for keyword search and `where` for location.
"""
from datetime import datetime
from typing import Any

from app.config import settings
from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper, ScraperDisabled

_DEFAULT_COUNTRY = "us"
_ENDPOINT = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"


class AdzunaScraper(BaseScraper):
    source = "adzuna"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            raise ScraperDisabled(
                "Adzuna requires ADZUNA_APP_ID and ADZUNA_APP_KEY (register at "
                "https://developer.adzuna.com)"
            )

        country = _pick_country(locations)
        where = locations[0] if locations else ""
        params: dict[str, Any] = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": min(limit, 50),
            "what": " ".join(keywords),
            "content-type": "application/json",
        }
        if where:
            params["where"] = where

        resp = self._client.get(
            _ENDPOINT.format(country=country, page=1),
            params=params,
        )
        resp.raise_for_status()
        results = resp.json().get("results", []) or []
        return [_to_normalized(item) for item in results[:limit]]


def _pick_country(locations: list[str] | None) -> str:
    """Infer the 2-letter country code Adzuna expects from locations hint."""
    if not locations:
        return _DEFAULT_COUNTRY
    joined = " ".join(locations).lower()
    for keyword, code in [
        ("uk", "gb"), ("united kingdom", "gb"), ("britain", "gb"), ("london", "gb"),
        ("germany", "de"), ("berlin", "de"),
        ("netherlands", "nl"), ("amsterdam", "nl"),
        ("australia", "au"), ("sydney", "au"), ("melbourne", "au"),
        ("canada", "ca"), ("toronto", "ca"),
        ("france", "fr"), ("paris", "fr"),
    ]:
        if keyword in joined:
            return code
    return _DEFAULT_COUNTRY


def _to_normalized(item: dict[str, Any]) -> NormalizedJob:
    posted_at: datetime | None = None
    if raw := item.get("created"):
        try:
            posted_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            posted_at = None

    company = (item.get("company") or {}).get("display_name") or "Unknown"
    location = (item.get("location") or {}).get("display_name")

    return NormalizedJob(
        source="adzuna",
        external_id=str(item.get("id")) if item.get("id") is not None else None,
        source_url=item.get("redirect_url"),
        title=(item.get("title") or "").strip() or "Unknown",
        company_name=company.strip(),
        location=location,
        description=item.get("description"),
        salary_min=_as_int(item.get("salary_min")),
        salary_max=_as_int(item.get("salary_max")),
        job_type=item.get("contract_type"),
        posted_at=posted_at,
    )


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
