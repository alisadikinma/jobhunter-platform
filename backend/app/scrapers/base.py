"""BaseScraper — every source implements this contract.

Scrapers are sync (matches the rest of the app's sync-SQLAlchemy choice);
the caller aggregates them in a threadpool if parallelism is needed.
"""
from abc import ABC, abstractmethod

import httpx

from app.schemas.scraper import NormalizedJob


class BaseScraper(ABC):
    source: str  # short id stored in scraped_jobs.source (e.g. "remoteok")
    timeout_s: float = 30.0

    def __init__(self, client: httpx.Client | None = None) -> None:
        # Injected in tests with a MockTransport; production uses a shared client.
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self.timeout_s, follow_redirects=True)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "BaseScraper":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @abstractmethod
    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]: ...


class ScraperDisabled(RuntimeError):
    """Raised when a scraper cannot run (missing creds, feature flag off)."""
