"""Scraper aggregator — run N sources, dedup by content_hash, return union.

This is a thin orchestrator. Individual scrapers own their HTTP logic; the
aggregator just loops, catches failures per-source (one broken scraper must
not kill the batch), and de-duplicates across sources.
"""
import logging
from collections.abc import Iterable

from app.schemas.scraper import NormalizedJob
from app.scrapers.adzuna import AdzunaScraper
from app.scrapers.arbeitnow import ArbeitnowScraper
from app.scrapers.base import BaseScraper, ScraperDisabled
from app.scrapers.hiring_cafe import HiringCafeScraper
from app.scrapers.hn_algolia import HnAlgoliaScraper
from app.scrapers.jobspy_scraper import JobSpyScraper
from app.scrapers.remoteok import RemoteOKScraper
from app.utils.deduplicator import content_hash

log = logging.getLogger(__name__)


# source id → no-auth scraper class. JobSpy is here because it reaches
# LinkedIn/Indeed/Glassdoor directly without an Apify account.
#
# Sources that need an Apify pool account (wellfound, linkedin_apify) are
# NOT in this registry — scraper_service routes them through the pool
# because they require a DB session to acquire + record credit.
SCRAPER_REGISTRY: dict[str, type[BaseScraper]] = {
    "remoteok": RemoteOKScraper,
    "hn_algolia": HnAlgoliaScraper,
    "arbeitnow": ArbeitnowScraper,
    "adzuna": AdzunaScraper,
    "hiring_cafe": HiringCafeScraper,
    "jobspy": JobSpyScraper,
}


# Sources routed through scraper_service._run_apify_sources (need DB + pool).
APIFY_GATED_SOURCES: frozenset[str] = frozenset({"wellfound", "linkedin_apify"})


def aggregate(
    keywords: list[str],
    sources: Iterable[str],
    locations: list[str] | None = None,
    limit_per_source: int = 50,
) -> list[NormalizedJob]:
    """Run each source in sequence, merging results and dropping duplicates.

    Returns jobs in insertion order (first source to produce a given
    content_hash wins). Scrapers that raise ScraperDisabled (e.g. Adzuna
    without creds) are logged and skipped; other exceptions are caught to
    avoid killing the whole run.
    """
    seen: set[str] = set()
    out: list[NormalizedJob] = []

    for source_id in sources:
        scraper_cls = SCRAPER_REGISTRY.get(source_id)
        if scraper_cls is None:
            log.warning("Unknown scraper source: %s", source_id)
            continue

        try:
            with scraper_cls() as scraper:
                jobs = scraper.scrape(
                    keywords=keywords,
                    locations=locations,
                    limit=limit_per_source,
                )
        except ScraperDisabled as e:
            log.info("Scraper %s skipped: %s", source_id, e)
            continue
        except Exception as e:
            log.exception("Scraper %s failed: %s", source_id, e)
            continue

        for job in jobs:
            h = content_hash(job.title, job.company_name, job.description)
            if h in seen:
                continue
            seen.add(h)
            out.append(job)

    return out
