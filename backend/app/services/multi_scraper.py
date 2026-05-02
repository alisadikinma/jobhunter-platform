"""Parallel multi-page Firecrawl scraper for portfolio CV imports.

Scrapes a list of URLs concurrently via the existing FirecrawlService pool,
then concatenates the markdown into one stream with per-URL section headers.
Failed/empty pages are skipped (warn-and-continue); MultiScrapeError is
raised only if every URL fails. Used by `/api/cv/master/import-url` to cover
multi-page portfolios where a single page leaves out work/projects/awards.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.firecrawl_service import FirecrawlService

log = logging.getLogger(__name__)


class MultiScrapeError(RuntimeError):
    """Raised when every URL in a multi-scrape batch returned empty/error."""


def _scrape_one(url: str, *, wait_for_ms: int) -> tuple[str, str | None]:
    """Run a single scrape inside the worker thread. Returns (url, markdown_or_None).

    `markdown_or_None` is None on failure/empty so the caller can filter.
    Each worker opens its OWN SessionLocal — SQLAlchemy sessions are not
    thread-safe, so passing a shared session to N workers triggers
    "Session is already flushing" errors. The Firecrawl pool's
    `acquire_account` uses FOR UPDATE SKIP LOCKED at the row level,
    which is the right concurrency primitive across separate sessions.
    """
    try:
        with SessionLocal() as worker_db:
            with FirecrawlService(db=worker_db) as fc:
                result = fc.scrape(url, opts={"waitFor": wait_for_ms})
    except Exception as e:  # network/pool failure — log and skip
        log.warning("multi-scrape: %s raised: %s", url, e)
        return url, None

    md = (result or {}).get("markdown") or ""
    err = (result or {}).get("error")
    if not md.strip():
        log.warning(
            "multi-scrape: %s returned empty markdown (error=%s)", url, err
        )
        return url, None
    return url, md


def scrape_multiple_pages(
    urls: list[str],
    db: Session,
    *,
    wait_for_ms: int = 8000,
    max_workers: int = 4,
) -> str:
    """Scrape `urls` in parallel, return concatenated markdown.

    Each successful page is wrapped with a `=== Page: <url> ===` delimiter
    so the downstream LLM can attribute content back to its source page.
    Output preserves input URL order regardless of completion order.

    Raises:
        MultiScrapeError: if every URL returns empty/error.
    """
    if not urls:
        raise MultiScrapeError("no URLs provided")

    # url -> markdown, populated as futures complete
    by_url: dict[str, str] = {}

    # `db` is intentionally NOT forwarded to workers — each worker opens
    # its own SessionLocal to avoid cross-thread session sharing
    # ("Session is already flushing" race when multiple threads share one
    # SQLAlchemy session). Parameter kept for API stability.
    _ = db  # mark intentionally unused

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_scrape_one, url, wait_for_ms=wait_for_ms): url
            for url in urls
        }
        for fut in as_completed(futures):
            url = futures[fut]
            try:
                _, md = fut.result()
            except Exception as e:
                log.warning("multi-scrape: future for %s crashed: %s", url, e)
                md = None
            if md:
                by_url[url] = md

    if not by_url:
        raise MultiScrapeError(
            f"all {len(urls)} URLs returned empty/error — check Firecrawl pool health"
        )

    # Reassemble in input order with delimiters.
    parts: list[str] = []
    for url in urls:
        if url in by_url:
            parts.append(f"\n\n=== Page: {url} ===\n\n{by_url[url]}")
    return "".join(parts).strip()


def derive_portfolio_urls(base_url: str) -> list[str]:
    """Auto-derive 4 portfolio sub-pages from a base URL.

    Matches the alisadikinma.com/en convention: home + about + work tabs.
    Output order: [base, /about, /work?tab=awards, /work?tab=projects].
    Trailing slash on the input path is stripped so derived URLs don't
    end up with double slashes.
    """
    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        # Caller validates scheme upstream; defensive fallback returns
        # the input unchanged so the helper never raises.
        return [base_url]

    path = (parsed.path or "").rstrip("/")
    base_no_trail = f"{parsed.scheme}://{parsed.netloc}{path}"

    candidates = [
        base_no_trail,
        f"{base_no_trail}/about",
        f"{base_no_trail}/work?tab=awards",
        f"{base_no_trail}/work?tab=projects",
    ]

    seen: set[str] = set()
    out: list[str] = []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out
