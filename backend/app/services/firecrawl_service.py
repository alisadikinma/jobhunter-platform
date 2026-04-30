"""Firecrawl wrapper — url -> clean Markdown.

Reads credentials from the `firecrawl_config` singleton row (id=1) when
present and active; falls back to `settings.FIRECRAWL_*` env vars
otherwise. Talks directly to the Firecrawl v1 REST API (works for both
self-hosted and the hosted SaaS).

Resilient: any HTTP/timeout error returns a structured empty response
rather than propagating, so enrichment is best-effort and never blocks.
"""
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.firecrawl_config import FirecrawlConfig
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)


@dataclass
class _ResolvedConfig:
    api_url: str
    api_key: str
    timeout_s: int


def _resolve(db: Session | None, *, require_active: bool = True) -> _ResolvedConfig:
    """DB-first, fall back to env. `require_active=False` lets the test
    endpoint validate freshly-saved creds before the flag flips.
    """
    if db is not None:
        row = db.get(FirecrawlConfig, 1)
        if row is not None and row.api_url and (row.is_active or not require_active):
            api_key = ""
            if row.api_key_encrypted:
                try:
                    api_key = decrypt_token(row.api_key_encrypted)
                except Exception as e:
                    log.warning("firecrawl: failed to decrypt api_key: %s", e)
            return _ResolvedConfig(
                api_url=row.api_url,
                api_key=api_key,
                timeout_s=row.timeout_s or 60,
            )

    return _ResolvedConfig(
        api_url=settings.FIRECRAWL_API_URL,
        api_key=settings.FIRECRAWL_API_KEY,
        timeout_s=settings.FIRECRAWL_TIMEOUT_S,
    )


class FirecrawlService:
    """Stateless wrapper; safe to instantiate per request."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        db: Session | None = None,
    ) -> None:
        self._db = db
        self._cfg = _resolve(db)
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=self._cfg.timeout_s)

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
        endpoint = f"{self._cfg.api_url.rstrip('/')}/v1/scrape"
        headers = {"Content-Type": "application/json"}
        if self._cfg.api_key:
            headers["Authorization"] = f"Bearer {self._cfg.api_key}"

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


def test_connection(db: Session, *, sample_url: str = "https://example.com") -> tuple[bool, str, int]:
    """Live scrape against `sample_url` to verify Firecrawl creds work.

    Returns `(ok, message, sample_chars)`. Used by the test endpoint
    BEFORE marking `is_active=true`.
    """
    cfg = _resolve(db, require_active=False)
    endpoint = f"{cfg.api_url.rstrip('/')}/v1/scrape"
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"

    payload = {"url": sample_url, "formats": ["markdown"], "onlyMainContent": True}
    try:
        with httpx.Client(timeout=min(cfg.timeout_s, 30)) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPStatusError as e:
        return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}", 0
    except httpx.HTTPError as e:
        return False, f"connection failed: {e}", 0
    except ValueError:
        return False, "malformed JSON response", 0

    if not body.get("success", True):
        return False, body.get("error", "scrape failed"), 0

    data = body.get("data") or {}
    md = data.get("markdown", "") or ""
    return True, f"OK — fetched {len(md)} chars from {sample_url}", len(md)


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
