"""Fetch the master CV from the Portfolio CV API.

First-party authenticated endpoint at alisadikinma.com/api/cv/*.

Two surfaces:
  - /api/cv/master.md  → ready-to-parse markdown (legacy fallback path).
  - /api/cv/export     → JSON Resume v2.0.0 — validates DIRECTLY against
                         MasterCVContent, no LLM parse needed (~1s import).

The JSON path is preferred when the API schema_version is 2.0.0+ because
it skips the entire Claude CLI call (~5-10s) and produces deterministic
output (same response → same content rows, no per-import drift). Caller
short-circuits to JSON when host matches AND token is set AND no
explicit `urls` list was supplied.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings

log = logging.getLogger(__name__)

PORTFOLIO_API_HOSTS = {"alisadikinma.com", "www.alisadikinma.com"}

PORTFOLIO_EXPORT_PATH = "/api/cv/export"
SUPPORTED_SCHEMA_PREFIX = "2."  # accept any 2.x — 1.x lacked summary_variants


class PortfolioCVApiError(RuntimeError):
    pass


def host_supports_api(url: str) -> bool:
    """True iff the URL host matches a Portfolio CV API endpoint AND the
    token is configured. Caller uses this to decide whether to skip the
    Firecrawl path."""
    if not settings.PORTFOLIO_CV_TOKEN:
        return False
    try:
        host = (urlparse(url).netloc or "").lower()
    except ValueError:
        return False
    return host in PORTFOLIO_API_HOSTS


def fetch_master_markdown(*, compact: bool = False) -> str:
    """GET /api/cv/master.md with the bearer token. Returns the raw markdown.

    Raises PortfolioCVApiError on missing token, non-2xx response, or empty
    body. We don't bother with ETag caching here — the caller persists the
    parsed result to master_cv (versioned) and the Pydantic validator runs
    on every save anyway, so a second fetch in the same minute is cheap
    enough at ~10k tokens.
    """
    if not settings.PORTFOLIO_CV_TOKEN:
        raise PortfolioCVApiError("PORTFOLIO_CV_TOKEN is not configured")

    url = settings.PORTFOLIO_CV_API_URL
    if compact:
        url += ("&" if "?" in url else "?") + "compact=1"

    headers = {
        "Authorization": f"Bearer {settings.PORTFOLIO_CV_TOKEN}",
        "Accept": "text/markdown, application/json",
    }

    try:
        with httpx.Client(timeout=settings.PORTFOLIO_CV_TIMEOUT_S) as client:
            r = client.get(url, headers=headers)
    except httpx.HTTPError as e:
        raise PortfolioCVApiError(f"Portfolio CV API network error: {e}") from e

    if r.status_code == 401:
        raise PortfolioCVApiError(
            "Portfolio CV API rejected the token (401). "
            "Regenerate at https://alisadikinma.com/admin/automation/tokens "
            "and update PORTFOLIO_CV_TOKEN."
        )
    if r.status_code == 403:
        raise PortfolioCVApiError(
            "Portfolio CV API token lacks the 'cv:read' ability (403). "
            "Recreate the token with category=cv, ability=cv:read."
        )
    if r.status_code == 429:
        raise PortfolioCVApiError(
            "Portfolio CV API rate limit hit (429, 30 req/min). "
            "Retry in 60s."
        )
    if r.status_code >= 400:
        raise PortfolioCVApiError(
            f"Portfolio CV API returned {r.status_code}: {r.text[:200]}"
        )

    body = r.text
    if not body.strip():
        raise PortfolioCVApiError("Portfolio CV API returned empty body")
    return body


def _api_base() -> str:
    """Derive the API root from PORTFOLIO_CV_API_URL by stripping the
    /api/cv/master.md suffix (operator may have customized the path).
    Falls back to the production host when the URL is unparseable."""
    url = settings.PORTFOLIO_CV_API_URL
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return "https://alisadikinma.com"


def fetch_master_export() -> dict[str, Any]:
    """GET /api/cv/export → JSON Resume v2.0.0 dict.

    The response shape validates directly against
    `app.schemas.cv.MasterCVContent` (the import endpoint runs
    `MasterCVContent.model_validate(...)` on the result and persists
    it). No LLM parse, no markdown re-shaping — ~1s round-trip vs
    ~5-10s for the markdown→Claude path.

    Raises PortfolioCVApiError on:
      - missing token (caller should check host_supports_api first)
      - network / non-2xx response
      - empty body or non-JSON
      - unsupported schema_version (refuse rather than silently
        downgrade — 1.x payload would fail summary_variants validation
        downstream).
    """
    if not settings.PORTFOLIO_CV_TOKEN:
        raise PortfolioCVApiError("PORTFOLIO_CV_TOKEN is not configured")

    url = _api_base() + PORTFOLIO_EXPORT_PATH
    headers = {
        "Authorization": f"Bearer {settings.PORTFOLIO_CV_TOKEN}",
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=settings.PORTFOLIO_CV_TIMEOUT_S) as client:
            r = client.get(url, headers=headers)
    except httpx.HTTPError as e:
        raise PortfolioCVApiError(f"Portfolio CV API network error: {e}") from e

    if r.status_code == 401:
        raise PortfolioCVApiError(
            "Portfolio CV API rejected the token (401). "
            "Regenerate at https://alisadikinma.com/admin/automation/tokens "
            "and update PORTFOLIO_CV_TOKEN."
        )
    if r.status_code == 403:
        raise PortfolioCVApiError(
            "Portfolio CV API token lacks the 'cv:read' ability (403). "
            "Recreate the token with category=cv, ability=cv:read."
        )
    if r.status_code == 429:
        raise PortfolioCVApiError(
            "Portfolio CV API rate limit hit (429, 30 req/min). Retry in 60s."
        )
    if r.status_code >= 400:
        raise PortfolioCVApiError(
            f"Portfolio CV API /export returned {r.status_code}: {r.text[:200]}"
        )

    try:
        data = r.json()
    except ValueError as e:
        raise PortfolioCVApiError(f"Portfolio CV API /export returned non-JSON: {e}") from e

    if not isinstance(data, dict):
        raise PortfolioCVApiError(
            f"Portfolio CV API /export returned {type(data).__name__}, expected object"
        )

    schema_version = str(data.get("schema_version") or "")
    if not schema_version.startswith(SUPPORTED_SCHEMA_PREFIX):
        raise PortfolioCVApiError(
            f"Portfolio CV API /export schema_version {schema_version!r} is "
            f"unsupported (need {SUPPORTED_SCHEMA_PREFIX}x). "
            "Falling back to markdown->LLM import path is automatic."
        )

    return data


_VARIANT_WHITELIST = {"vibe_coding", "ai_automation", "ai_video"}


def fetch_portfolio_projects() -> list[dict]:
    """Fetch /api/cv/export and re-shape `projects[]` into the dict format
    the /api/portfolio/import-url endpoint expects.

    Returned shape per item — drop-in compatible with the existing
    Firecrawl+LLM extractor output, plus extra fields the consumer's
    PortfolioAsset model already has columns for (`tags`, `metrics`,
    `is_featured`):

        {
          "title": str,
          "description": str | None,
          "url": str | None,
          "tech_stack": list[str],
          "tags": list[str],
          "metrics": dict | None,        # API project-level metrics
          "relevance_hint": list[str],   # filtered to the strict 3 variants
          "is_featured": bool,           # surfaces awards-style flagship marker
          "_source": "portfolio-api:<host>",
        }

    Same auth model + error semantics as fetch_master_export — caller
    short-circuits to this when host_supports_api(url) is true.
    """
    data = fetch_master_export()
    projects = data.get("projects") or []

    host = urlparse(_api_base()).netloc.lower() or "alisadikinma.com"
    source_label = f"portfolio-api:{host}"

    items: list[dict] = []
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        title = (proj.get("name") or "").strip()
        if not title:
            continue

        # Prefer strict variant_hint; fall back to legacy relevance_hint
        # filtered to the 3 valid values. The consumer enforces the
        # whitelist again at insert time, but pre-filtering keeps the
        # response payload honest.
        variant_raw = proj.get("variant_hint") or proj.get("relevance_hint") or []
        variant = [
            str(v).strip()
            for v in variant_raw
            if isinstance(v, str) and str(v).strip() in _VARIANT_WHITELIST
        ]

        tech_stack = [
            str(t).strip()
            for t in (proj.get("tech_stack") or [])
            if isinstance(t, str) and str(t).strip()
        ]
        tags = [
            str(t).strip()
            for t in (proj.get("tags") or [])
            if isinstance(t, str) and str(t).strip()
        ]

        # API may return metrics as {} (empty object). Normalize to None
        # so the consumer doesn't store a noisy empty JSONB row.
        metrics_raw = proj.get("metrics")
        metrics = metrics_raw if isinstance(metrics_raw, dict) and metrics_raw else None

        items.append({
            "title": title,
            "description": (proj.get("description") or "").strip() or None,
            "url": proj.get("url") or None,
            "tech_stack": tech_stack,
            "tags": tags,
            "metrics": metrics,
            "relevance_hint": variant,
            "is_featured": bool(proj.get("is_featured", False)),
            "_source": source_label,
        })
    return items
