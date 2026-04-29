"""AI-focused job boards — aijobs.net + aicareers.io.

Both sites are SSR with HTML listings. We GET each listing page, parse
with BeautifulSoup, and emit `NormalizedJob`s. The selectors are kept
deliberately liberal so a markup tweak on either site degrades to "fewer
jobs returned" rather than a hard failure.

If you find another AI-only job board that's worth aggregating, add it
to `_BOARDS` below — same shape (listing URL + per-card selector
pattern). For boards that need JS rendering, route them through
Firecrawl instead via a separate scraper.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper

log = logging.getLogger(__name__)


# Per-board config. `card_selector` matches each job entry; the helper
# `_extract_card` then pulls fields from within. Keep selectors loose.
_BOARDS: list[dict[str, Any]] = [
    {
        "id": "aijobs.net",
        "listing_url": "https://aijobs.net/",
        "card_selector": "li.list-group-item, article.job-listing, a.bg-light",
        "fallback_card_selector": "a[href*='/job/']",
    },
    {
        "id": "aicareers.io",
        "listing_url": "https://aicareers.io/",
        "card_selector": "a[href*='/jobs/'], li.job-item, article.job",
        "fallback_card_selector": "a[href*='/jobs/']",
    },
]


class AIJobsScraper(BaseScraper):
    """Fetches both aijobs.net and aicareers.io as a single composite source."""

    source = "aijobs"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        keywords_lc = [k.lower() for k in keywords]
        seen_urls: set[str] = set()
        out: list[NormalizedJob] = []

        for board in _BOARDS:
            try:
                resp = self._client.get(board["listing_url"])
                resp.raise_for_status()
            except Exception as e:
                log.warning("AIJobs fetch %s failed: %s", board["id"], e)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = _select_cards(soup, board)
            if not cards:
                log.info("AIJobs %s: zero cards parsed (selector drift?)", board["id"])
                continue

            for card in cards:
                job = _extract_card(card, board)
                if job is None:
                    continue
                # Deduplicate by source_url within this run.
                if job.source_url and job.source_url in seen_urls:
                    continue
                if not _matches(job, keywords_lc):
                    continue
                if job.source_url:
                    seen_urls.add(job.source_url)
                out.append(job)
                if len(out) >= limit:
                    return out

        return out


def _select_cards(soup: BeautifulSoup, board: dict[str, Any]) -> list[Tag]:
    cards = soup.select(board["card_selector"])
    if cards:
        return cards
    fallback = board.get("fallback_card_selector")
    if fallback:
        return soup.select(fallback)
    return []


def _extract_card(card: Tag, board: dict[str, Any]) -> NormalizedJob | None:
    base = board["listing_url"]

    # 1. Job link.
    href: str | None = None
    if card.name == "a" and card.get("href"):
        href = str(card.get("href"))
    else:
        link = card.find("a", href=True)
        if isinstance(link, Tag):
            href = str(link.get("href"))
    if not href:
        return None
    source_url = urljoin(base, href)

    # 2. Title — try heading-like elements first, fall back to the link text.
    title_el = card.find(["h2", "h3", "h4", "h5"]) or card.find(class_=re.compile(r"title", re.I))
    title = (title_el.get_text(" ", strip=True) if isinstance(title_el, Tag) else "").strip()
    if not title:
        link = card.find("a", href=True)
        if isinstance(link, Tag):
            title = link.get_text(" ", strip=True)
    if not title:
        return None

    # 3. Company.
    company_el = card.find(class_=re.compile(r"compan(y|ies)", re.I))
    company = (
        company_el.get_text(" ", strip=True) if isinstance(company_el, Tag) else ""
    ).strip()
    if not company:
        # Some sites embed company in a `<small>` near the title.
        small = card.find("small")
        if isinstance(small, Tag):
            company = small.get_text(" ", strip=True)
    if not company:
        company = "Unknown"

    # 4. Location (best-effort).
    location_el = card.find(class_=re.compile(r"location|geo", re.I))
    location = (
        location_el.get_text(" ", strip=True) if isinstance(location_el, Tag) else None
    )

    # 5. Tech stack (badges / chip-style elements).
    tech_stack: list[str] = []
    for chip in card.find_all(class_=re.compile(r"tag|chip|badge|skill", re.I)):
        if isinstance(chip, Tag):
            t = chip.get_text(" ", strip=True)
            if 1 < len(t) < 40 and t not in tech_stack:
                tech_stack.append(t)
        if len(tech_stack) >= 12:
            break

    # 6. Posted date — usually a `<time datetime=...>` or text "Today", "2d ago".
    posted_at: datetime | None = None
    time_el = card.find("time")
    if isinstance(time_el, Tag):
        dt_attr = time_el.get("datetime")
        if dt_attr:
            try:
                posted_at = datetime.fromisoformat(str(dt_attr).replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

    # 7. Description: card text minus the title (gives Sonnet enough to score on).
    description = card.get_text(" ", strip=True)
    if title and description.startswith(title):
        description = description[len(title):].strip()
    description = description[:2000] if description else None  # cap

    return NormalizedJob(
        source=f"aijobs:{board['id']}",
        external_id=source_url,
        source_url=source_url,
        title=title[:200],
        company_name=company[:150],
        location=location,
        description=description,
        remote_type="remote",  # both boards are remote-only by editorial policy
        posted_at=posted_at,
        tech_stack=tech_stack,
    )


def _matches(job: NormalizedJob, keywords_lc: list[str]) -> bool:
    if not keywords_lc:
        return True
    haystack = (
        f"{job.title} {job.company_name} {job.description or ''} "
        f"{' '.join(job.tech_stack)}"
    ).lower()
    return any(kw in haystack for kw in keywords_lc)
