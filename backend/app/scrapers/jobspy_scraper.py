"""JobSpy primary scraper for LinkedIn / Indeed / Glassdoor.

Strategy:
- Fan out keywords across per-city location variants (bypasses LinkedIn
  1000-cap per search).
- 2-5s sleep between calls to avoid detection.
- Optional residential proxy from env vars (PROXY_URL + credentials).
- Best-effort: if a single variant fails, log and continue with the rest.

python-jobspy's scrape_jobs() returns a pandas DataFrame; we normalize each
row into NormalizedJob and de-dup within this run via a (title, company)
tuple — the aggregator handles cross-source dedup later.
"""
import logging
import random
import time
from datetime import datetime
from typing import Any

from app.config import settings
from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper
from app.utils.location_splitter import generate_location_variants

log = logging.getLogger(__name__)


_SUPPORTED_SITES = ("linkedin", "indeed", "glassdoor")


class JobSpyScraper(BaseScraper):
    """Wraps python-jobspy.scrape_jobs. No shared httpx.Client needed."""

    source = "jobspy"
    _min_delay_s: float = 2.0
    _max_delay_s: float = 5.0

    def __init__(
        self,
        site_names: tuple[str, ...] = _SUPPORTED_SITES,
        scrape_fn: Any = None,
        sleep_fn: Any = None,
    ) -> None:
        # Deliberately skip super().__init__ — we don't use httpx here.
        self._owns_client = False
        self._client = None  # type: ignore[assignment]  # jobspy owns its own transport
        self.site_names = site_names
        self._scrape_fn = scrape_fn or _import_scrape_jobs()
        self._sleep_fn = sleep_fn or time.sleep

    def close(self) -> None:  # pragma: no cover — no client to close
        return

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        variants = generate_location_variants(locations)
        search_term = " ".join(keywords)
        per_variant_cap = max(1, limit // max(1, len(variants)))
        proxies = _build_proxies()

        seen: set[tuple[str, str]] = set()
        out: list[NormalizedJob] = []

        for idx, variant in enumerate(variants):
            if idx > 0:
                self._sleep_fn(random.uniform(self._min_delay_s, self._max_delay_s))
            try:
                df = self._scrape_fn(
                    site_name=list(self.site_names),
                    search_term=search_term,
                    location=variant.location,
                    results_wanted=per_variant_cap,
                    linkedin_fetch_description=True,
                    hours_old=168,  # 7 days
                    proxies=proxies,
                )
            except Exception as e:
                log.warning("jobspy scrape failed for %s: %s", variant.location, e)
                continue

            for row in _iter_rows(df):
                job = _row_to_normalized(row)
                if job is None:
                    continue
                key = (job.title.lower(), job.company_name.lower())
                if key in seen:
                    continue
                seen.add(key)
                out.append(job)
                if len(out) >= limit:
                    return out

        return out


def _import_scrape_jobs() -> Any:
    # Late import so tests that inject `scrape_fn` don't require the lib.
    from jobspy import scrape_jobs  # type: ignore[import-not-found]

    return scrape_jobs


def _build_proxies() -> list[str] | None:
    if not settings.PROXY_URL:
        return None
    url = settings.PROXY_URL
    if settings.PROXY_USERNAME and settings.PROXY_PASSWORD:
        # jobspy expects a list of URL strings; embed creds.
        creds = f"{settings.PROXY_USERNAME}:{settings.PROXY_PASSWORD}"
        if "://" in url:
            scheme, rest = url.split("://", 1)
            url = f"{scheme}://{creds}@{rest}"
        else:
            url = f"http://{creds}@{url}"
    return [url]


def _iter_rows(df: Any) -> list[dict[str, Any]]:
    """Accept either a DataFrame (jobspy default) or a plain list[dict] (tests)."""
    if df is None:
        return []
    if isinstance(df, list):
        return df
    if hasattr(df, "to_dict"):
        return df.to_dict(orient="records")
    return []


def _row_to_normalized(row: dict[str, Any]) -> NormalizedJob | None:
    title = str(row.get("title") or "").strip()
    company = str(row.get("company") or "").strip()
    if not title or not company:
        return None

    site = str(row.get("site") or "").lower() or "jobspy"
    source = f"jobspy_{site}" if site in _SUPPORTED_SITES else "jobspy"

    posted_at: datetime | None = None
    if raw := row.get("date_posted"):
        try:
            posted_at = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            posted_at = None

    return NormalizedJob(
        source=source,
        external_id=str(row.get("id") or row.get("job_url") or "") or None,
        source_url=row.get("job_url") or row.get("url"),
        title=title,
        company_name=company,
        location=row.get("location"),
        description=row.get("description"),
        salary_min=_as_int(row.get("min_amount") or row.get("salary_min")),
        salary_max=_as_int(row.get("max_amount") or row.get("salary_max")),
        remote_type="remote" if "remote" in str(row.get("location", "")).lower() else None,
        job_type=row.get("job_type"),
        posted_at=posted_at,
    )


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None
