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
from app.scrapers.aggregator import aggregate
from app.utils.deduplicator import content_hash

log = logging.getLogger(__name__)


def run_scrape_config(db: Session, config: ScrapeConfig) -> ScrapeRunResponse:
    """Run one scrape_config: aggregate sources, dedup vs DB, insert new jobs.

    Updates config.last_run_at and config.last_run_results.
    """
    keywords = list(config.keywords or [])
    sources = list(config.sources or [])
    locations = list(config.locations or [])
    limit = config.max_results_per_source or 30
    variant = config.variant_target

    normalized = aggregate(
        keywords=keywords,
        sources=sources,
        locations=locations or None,
        limit_per_source=limit,
    )

    stats = _persist(db, normalized, variant_target=variant)
    _record_run(db, config, stats)
    db.commit()
    return stats


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

    for job in jobs:
        per_source[job.source] = per_source.get(job.source, 0) + 1
        h = content_hash(job.title, job.company_name, job.description)

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
            description=job.description,
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
