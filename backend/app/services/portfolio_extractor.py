"""Extract portfolio entries from arbitrary URL via Firecrawl + Claude CLI.

Firecrawl scrapes the page to clean markdown. Claude CLI parses the
markdown to find project/case-study entries and returns a list. Used by
the /api/portfolio/import-url endpoint.
"""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.services.firecrawl_service import FirecrawlService
from app.services.llm_extractor import LLMExtractError, extract_json_via_cli

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
    """Scrape URL via Firecrawl pool, extract projects via Claude CLI.

    Returns list of dicts ready to insert as portfolio_assets rows.
    Auth: host's `claude` CLI OAuth login. No API key required.
    """
    with FirecrawlService(db=db) as service:
        # waitFor=5000 lets JS-rendered SPAs (Next/Nuxt/React) finish
        # hydration before Firecrawl reads the DOM. Without this, modern
        # portfolio sites return empty markdown because the actual content
        # injects after initial HTML load.
        result = service.scrape(url, opts={"waitFor": 5000})

    markdown = (result or {}).get("markdown") or ""
    if not markdown:
        err = (result or {}).get("error") or "no error"
        raise PortfolioExtractError(
            f"Firecrawl returned no content for {url} ({err}). "
            "If the site is JS-rendered, the wait timeout may need to be "
            "increased. Otherwise try adding entries via the 'Add asset' "
            "button manually."
        )

    try:
        parsed = extract_json_via_cli(
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            user_message=(
                "Extract portfolio projects from this content:\n\n"
                + markdown[:50000]
            ),
        )
    except LLMExtractError as e:
        raise PortfolioExtractError(str(e)) from e

    items = parsed.get("items") or []
    if not isinstance(items, list):
        raise PortfolioExtractError("LLM output missing 'items' array")

    domain = urlparse(url).netloc or url
    for item in items:
        if isinstance(item, dict):
            item["_source"] = f"url:{domain}"

    return items
