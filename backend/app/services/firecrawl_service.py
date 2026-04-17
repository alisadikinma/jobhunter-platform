"""Firecrawl self-hosted wrapper — url -> clean Markdown.

Talks directly to the Firecrawl v1 REST API (works for both self-hosted
and the hosted SaaS). Resilient: any HTTP/timeout error returns a
structured empty response rather than propagating, so enrichment is
best-effort and never blocks the caller.
"""
import logging
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)


class FirecrawlService:
    """Stateless wrapper; safe to instantiate per request."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.FIRECRAWL_TIMEOUT_S)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "FirecrawlService":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def scrape(self, url: str, opts: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch url → `{markdown, html, title, description, metadata, error?}`.

        On any failure, returns `{"markdown": "", "error": str, ...}` rather
        than raising — enrichment is opportunistic.
        """
        payload: dict[str, Any] = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        }
        if opts:
            payload.update(opts)

        return self._post_scrape(payload)

    def scrape_with_extraction(
        self, url: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Firecrawl extract: structured JSON via schema instead of raw markdown."""
        payload: dict[str, Any] = {
            "url": url,
            "formats": ["extract"],
            "extract": {"schema": schema},
        }
        return self._post_scrape(payload)

    # --- internals -------------------------------------------------

    def _post_scrape(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{settings.FIRECRAWL_API_URL.rstrip('/')}/v1/scrape"
        headers = {"Content-Type": "application/json"}
        if settings.FIRECRAWL_API_KEY:
            headers["Authorization"] = f"Bearer {settings.FIRECRAWL_API_KEY}"

        try:
            resp = self._client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPError as e:
            log.warning("firecrawl: HTTP error for %s: %s", payload.get("url"), e)
            return _empty_response(str(e))
        except ValueError as e:
            log.warning("firecrawl: malformed JSON for %s: %s", payload.get("url"), e)
            return _empty_response("malformed response")

        if not body.get("success", True):
            return _empty_response(body.get("error", "scrape failed"))

        data = body.get("data") or {}
        metadata = data.get("metadata") or {}
        return {
            "markdown": data.get("markdown", "") or "",
            "html": data.get("html", "") or "",
            "title": metadata.get("title") or metadata.get("ogTitle"),
            "description": metadata.get("description") or metadata.get("ogDescription"),
            "metadata": metadata,
            "extract": data.get("extract"),
            "error": None,
        }


def _empty_response(error: str) -> dict[str, Any]:
    return {
        "markdown": "",
        "html": "",
        "title": None,
        "description": None,
        "metadata": {},
        "extract": None,
        "error": error,
    }
