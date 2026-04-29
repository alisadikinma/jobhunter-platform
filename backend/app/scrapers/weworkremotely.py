"""WeWorkRemotely — RSS feeds per category.

WWR doesn't expose a JSON API but every category has a stable RSS feed
at `https://weworkremotely.com/categories/<slug>.rss`. RSS items have
the shape:

    <title>Company: Role</title>
    <link>https://weworkremotely.com/remote-jobs/<slug></link>
    <description>HTML blob describing the role</description>
    <pubDate>RFC-2822 timestamp</pubDate>
    <guid>...</guid>

We pull the categories most relevant to Ali's three variants
(programming, devops, design, marketing, product, all-other) and merge
into a single feed pre-keyword-filter.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper

log = logging.getLogger(__name__)

_BASE = "https://weworkremotely.com/categories"
_CATEGORIES = (
    "remote-programming-jobs",
    "remote-devops-sysadmin-jobs",
    "remote-design-jobs",
    "remote-product-jobs",
    "remote-marketing-jobs",
    "all-other-remote-jobs",
)

# Parses the canonical "Company: Role" feed-title format.
_TITLE_RE = re.compile(r"^\s*(?P<company>[^:]{2,80}):\s*(?P<title>.+?)\s*$")


class WeWorkRemotelyScraper(BaseScraper):
    source = "weworkremotely"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        keywords_lc = [k.lower() for k in keywords]
        seen_links: set[str] = set()
        out: list[NormalizedJob] = []

        for category in _CATEGORIES:
            url = f"{_BASE}/{category}.rss"
            try:
                resp = self._client.get(url)
                resp.raise_for_status()
            except Exception as e:
                log.warning("WWR fetch %s failed: %s", category, e)
                continue

            for item in _parse_rss(resp.text):
                link = item.get("link") or ""
                if link in seen_links:
                    continue
                if not _matches(item, keywords_lc):
                    continue
                seen_links.add(link)
                normalized = _to_normalized(item)
                if normalized is not None:
                    out.append(normalized)
                if len(out) >= limit:
                    return out
        return out


def _parse_rss(xml_text: str) -> list[dict[str, str]]:
    """Return one dict per `<item>` with title/link/description/pubDate."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        log.warning("WWR RSS parse failed: %s", e)
        return []

    items: list[dict[str, str]] = []
    for item in root.iter("item"):
        items.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "description": item.findtext("description") or "",
            "pubDate": (item.findtext("pubDate") or "").strip(),
            "guid": (item.findtext("guid") or "").strip(),
        })
    return items


def _matches(item: dict[str, str], keywords_lc: list[str]) -> bool:
    if not keywords_lc:
        return True
    haystack = (item.get("title", "") + " " + item.get("description", "")).lower()
    return any(kw in haystack for kw in keywords_lc)


def _to_normalized(item: dict[str, str]) -> NormalizedJob | None:
    title_raw = item.get("title", "")
    match = _TITLE_RE.match(title_raw)
    if match:
        company = match.group("company").strip()
        title = match.group("title").strip()
    else:
        # Title format diverged — fall back to the whole string as the title.
        company = "Unknown"
        title = title_raw or "Untitled"

    description_html = item.get("description") or ""
    description = BeautifulSoup(description_html, "html.parser").get_text(" ", strip=True)

    posted_at: datetime | None = None
    raw_date = item.get("pubDate") or ""
    if raw_date:
        try:
            posted_at = parsedate_to_datetime(raw_date)
        except (TypeError, ValueError):
            posted_at = None

    link = item.get("link") or ""
    guid = item.get("guid") or link

    return NormalizedJob(
        source="weworkremotely",
        external_id=guid or None,
        source_url=link or None,
        title=title[:200],
        company_name=company[:150],
        location="Remote",
        description=description or None,
        remote_type="remote",
        posted_at=posted_at,
    )
