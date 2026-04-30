"""Scraper orchestration — runs a scrape_config, dedups against DB, inserts jobs."""
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import ScrapedJob
from app.models.scrape_config import ScrapeConfig
from app.schemas.scrape_config import ScrapeRunResponse
from app.schemas.scraper import NormalizedJob
from app.scrapers.aggregator import APIFY_GATED_SOURCES, aggregate
from app.scrapers.linkedin_apify import LinkedInApifyScraper
from app.scrapers.wellfound_apify import WellfoundApifyScraper
from app.services.apify_pool import ApifyPoolExhausted, acquire_account, record_usage
from app.utils.deduplicator import content_hash
from app.utils.html_strip import strip_html
from app.utils.title_filter import is_offtopic_title

log = logging.getLogger(__name__)


def run_scrape_config(db: Session, config: ScrapeConfig) -> ScrapeRunResponse:
    """Run one scrape_config: aggregate sources, dedup vs DB, insert new jobs.

    Updates config.last_run_at and config.last_run_results. Apify-gated
    sources (wellfound, linkedin_apify) are routed through the Apify pool
    so each run acquires a credit-tracked account.
    """
    keywords = list(config.keywords or [])
    requested = list(config.sources or [])
    locations = list(config.locations or [])
    limit = config.max_results_per_source or 30
    variant = config.variant_target

    free_sources = [s for s in requested if s not in APIFY_GATED_SOURCES]
    apify_sources = [s for s in requested if s in APIFY_GATED_SOURCES]

    normalized = list(aggregate(
        keywords=keywords,
        sources=free_sources,
        locations=locations or None,
        limit_per_source=limit,
    ))

    for source_id in apify_sources:
        more = _run_apify_source(
            db,
            source_id=source_id,
            keywords=keywords,
            locations=locations or None,
            limit=limit,
        )
        normalized.extend(more)

    stats = _persist(db, normalized, variant_target=variant)
    _record_run(db, config, stats)
    db.commit()
    return stats


def _run_apify_source(
    db: Session,
    *,
    source_id: str,
    keywords: list[str],
    locations: list[str] | None,
    limit: int,
) -> list[NormalizedJob]:
    """Acquire a pool account, run the Apify-based scraper, record usage.

    Never propagates exceptions — returns [] on any failure so the batch
    keeps running. Estimated cost per run is conservative ($0.15 reserve).
    """
    try:
        account = acquire_account(db, estimated_cost_usd=0.15)
    except ApifyPoolExhausted as e:
        log.warning("apify pool exhausted for %s: %s", source_id, e)
        return []

    scraper_cls = (
        WellfoundApifyScraper
        if source_id == "wellfound"
        else LinkedInApifyScraper
    )

    started = datetime.now(UTC)
    status = "success"
    jobs: list[NormalizedJob] = []
    error_message: str | None = None

    try:
        scraper = scraper_cls(account.api_token)
        jobs = scraper.scrape(keywords=keywords, locations=locations, limit=limit)
    except Exception as e:
        log.exception("apify scraper %s failed: %s", source_id, e)
        status = "failure"
        error_message = str(e)

    duration_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
    # Conservative cost estimate: $0.10 per 100 jobs; min $0.02 per attempt.
    cost = max(0.02, 0.10 * (len(jobs) / 100))
    record_usage(
        db,
        account.id,
        cost_usd=cost,
        jobs_scraped=len(jobs),
        status=status,
        actor_id=source_id,
        duration_ms=duration_ms,
        error_message=error_message,
    )
    return jobs


def run_ad_hoc(
    db: Session,
    *,
    keywords: list[str],
    sources: list[str],
    locations: list[str] | None = None,
    variant_target: str | None = None,
    max_results_per_source: int = 30,
) -> ScrapeRunResponse:
    """Run a scrape without a saved config — used by 'Run Now' from the UI."""
    normalized = aggregate(
        keywords=keywords,
        sources=sources,
        locations=locations,
        limit_per_source=max_results_per_source,
    )
    stats = _persist(db, normalized, variant_target=variant_target)
    db.commit()
    return stats


def _persist(
    db: Session, jobs: list[NormalizedJob], *, variant_target: str | None
) -> ScrapeRunResponse:
    per_source: dict[str, int] = {}
    new_jobs = 0
    duplicates = 0
    errors: list[str] = []

    rejected_offtopic = 0
    for job in jobs:
        per_source[job.source] = per_source.get(job.source, 0) + 1

        # Drop obvious off-topic titles (sales/recruiting/admin roles that
        # slipped through scraper-level keyword matching because the company
        # or description mentioned "AI" or "pipeline"). See utils/title_filter.
        if is_offtopic_title(job.title):
            rejected_offtopic += 1
            continue

        # Convert HTML descriptions to plain text on ingest. RemoteOK + JobSpy
        # emit `<p>...</p>` fragments; storing raw HTML produced literal tags
        # in the UI. One canonical text representation also helps scoring.
        clean_description = strip_html(job.description)

        h = content_hash(job.title, job.company_name, clean_description)

        existing = db.execute(
            select(ScrapedJob.id).where(ScrapedJob.content_hash == h)
        ).scalar_one_or_none()
        if existing is not None:
            duplicates += 1
            continue

        row = ScrapedJob(
            source=job.source,
            source_url=job.source_url,
            external_id=job.external_id,
            title=job.title,
            company_name=job.company_name,
            location=job.location,
            description=clean_description,
            tech_stack=list(job.tech_stack or []),
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            remote_type=job.remote_type,
            job_type=job.job_type,
            posted_at=job.posted_at,
            content_hash=h,
            suggested_variant=variant_target,
            status="new",
        )
        db.add(row)
        try:
            db.flush()
            new_jobs += 1
        except Exception as e:
            db.rollback()
            log.warning("scrape insert collision for hash=%s: %s", h[:8], e)
            errors.append(f"insert collision: {h[:8]}")
            duplicates += 1

    if rejected_offtopic:
        errors.append(f"rejected {rejected_offtopic} off-topic titles")

    return ScrapeRunResponse(
        total_scraped=len(jobs),
        new_jobs=new_jobs,
        duplicates=duplicates,
        per_source=per_source,
        errors=errors,
    )


def _record_run(db: Session, config: ScrapeConfig, stats: ScrapeRunResponse) -> None:
    config.last_run_at = datetime.now(UTC)
    payload: dict[str, Any] = stats.model_dump()
    config.last_run_results = payload
