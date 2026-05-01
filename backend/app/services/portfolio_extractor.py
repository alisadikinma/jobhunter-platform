"""Extract portfolio entries from arbitrary URL via Firecrawl + Anthropic.

Firecrawl scrapes the page to clean markdown. Anthropic API parses the
markdown to find project/case-study entries and returns a list. Used by
the /api/portfolio/import-url endpoint.
"""
from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.services.firecrawl_service import FirecrawlService

log = logging.getLogger(__name__)


class PortfolioExtractError(RuntimeError):
    """Raised when Firecrawl returns nothing or the LLM output cannot be parsed."""


_EXTRACTION_SYSTEM_PROMPT = """You parse a personal/portfolio website's markdown content and extract showcased projects.

Return ONLY JSON (no prose, no code fences) of this exact shape:
{
  "items": [
    {
      "title": str,                    // project name
      "description": str,              // 1-3 sentence summary, no fluff
      "url": str | null,               // canonical project URL if mentioned, else null
      "tech_stack": [str],             // tools/frameworks/languages mentioned
      "relevance_hint": [str]          // subset of ["vibe_coding","ai_automation","ai_video"]
                                       //  - ai_automation: AI agents, workflow auto, MCP/n8n/langchain
                                       //  - vibe_coding: claude code, cursor, ai-first dev tools
                                       //  - ai_video: video gen, diffusion video, runway/sora/veo
                                       // Pick 1-2 most-applicable; empty array if none fit.
    }
  ]
}

Rules:
- Only include genuine project showcases (skip About/Contact/Blog index/nav links).
- Skip duplicates.
- DO NOT invent data — if a field isn't in the source, leave empty string or null.
- Return ONLY the JSON object.
"""


def extract_portfolio_from_url(db: Session, url: str) -> list[dict[str, Any]]:
    """Scrape URL via Firecrawl pool, extract projects via Anthropic API.

    Returns list of dicts ready to insert as portfolio_assets rows.
    """
    if not settings.ANTHROPIC_API_KEY:
        raise PortfolioExtractError(
            "ANTHROPIC_API_KEY not configured — set in .env to enable URL import"
        )

    with FirecrawlService(db=db) as service:
        result = service.scrape(url)

    markdown = (result or {}).get("markdown") or ""
    if not markdown:
        err = (result or {}).get("error") or "no error"
        raise PortfolioExtractError(
            f"Firecrawl returned empty content for {url} ({err})"
        )

    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.ANTHROPIC_MODEL_FAST,
        "max_tokens": 4096,
        "system": _EXTRACTION_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Extract portfolio projects from this content:\n\n"
                    + markdown[:50000]
                ),
            }
        ],
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPError as e:
        raise PortfolioExtractError(f"Anthropic API call failed: {e}") from e

    blocks = body.get("content") or []
    raw_json = "\n".join(
        b.get("text", "") for b in blocks if b.get("type") == "text"
    ).strip()

    # Strip code fences if the model decided to wrap the JSON despite the prompt.
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1] if "\n" in raw_json else raw_json
        if raw_json.endswith("```"):
            raw_json = raw_json.rsplit("```", 1)[0]
        raw_json = raw_json.strip()

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        log.warning("LLM returned invalid JSON: %s", raw_json[:500])
        raise PortfolioExtractError(f"Failed to parse LLM output: {e}") from e

    items = parsed.get("items") or []
    if not isinstance(items, list):
        raise PortfolioExtractError("LLM output missing 'items' array")

    domain = urlparse(url).netloc or url
    for item in items:
        if isinstance(item, dict):
            item["_source"] = f"url:{domain}"

    return items
