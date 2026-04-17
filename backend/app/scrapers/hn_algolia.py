"""HN 'Who is hiring?' via Algolia API.

Strategy: find the most recent thread authored by `whoishiring`, then fetch
comments on that thread matching the keywords. Algolia gives us free
full-text search over HN comments with a generous rate limit.
"""
import re
from datetime import UTC, datetime
from typing import Any

from app.schemas.scraper import NormalizedJob
from app.scrapers.base import BaseScraper

_COMMENT_URL = "https://news.ycombinator.com/item?id={id}"
_WHOSHIRING_QUERY = "https://hn.algolia.com/api/v1/search_by_date"

# Loose "COMPANY | ROLE | LOCATION" header parse — HN comments follow this convention.
_HEADER_RE = re.compile(
    r"^\s*(?P<company>[^|·•\n]{2,80})[|·•\-]\s*(?P<title>[^|·•\n]{2,120})",
    re.MULTILINE,
)


class HnAlgoliaScraper(BaseScraper):
    source = "hn_algolia"

    def scrape(
        self,
        keywords: list[str],
        locations: list[str] | None = None,
        limit: int = 50,
    ) -> list[NormalizedJob]:
        story_id = self._latest_whoshiring_id()
        if story_id is None:
            return []

        query = " ".join(keywords) if keywords else "remote"
        resp = self._client.get(
            _WHOSHIRING_QUERY,
            params={
                "query": query,
                "tags": f"comment,story_{story_id}",
                "hitsPerPage": min(limit, 100),
            },
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])

        jobs: list[NormalizedJob] = []
        for hit in hits:
            job = _hit_to_normalized(hit)
            if job is not None:
                jobs.append(job)
            if len(jobs) >= limit:
                break
        return jobs

    def _latest_whoshiring_id(self) -> int | None:
        resp = self._client.get(
            _WHOSHIRING_QUERY,
            params={
                "tags": "story,author_whoishiring",
                "hitsPerPage": 5,
            },
        )
        resp.raise_for_status()
        for hit in resp.json().get("hits", []):
            title = (hit.get("title") or "").lower()
            if "who is hiring" in title:
                return int(hit["objectID"])
        return None


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text)


def _hit_to_normalized(hit: dict[str, Any]) -> NormalizedJob | None:
    raw = hit.get("comment_text") or ""
    if not raw:
        return None
    plain = _strip_html(raw).strip()
    if len(plain) < 40:
        return None

    match = _HEADER_RE.search(plain)
    if match:
        company = match.group("company").strip()
        title = match.group("title").strip()
    else:
        first_line = plain.split("\n", 1)[0][:120]
        company = "Unknown"
        title = first_line or "Hiring post"

    created_at = hit.get("created_at")
    posted_at: datetime | None = None
    if created_at:
        try:
            posted_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            posted_at = None
    if posted_at is None:
        posted_at = datetime.now(UTC)

    object_id = str(hit.get("objectID") or "")
    return NormalizedJob(
        source="hn_algolia",
        external_id=object_id,
        source_url=_COMMENT_URL.format(id=object_id) if object_id else None,
        title=title[:200],
        company_name=company[:150],
        location="Remote" if "remote" in plain.lower() else None,
        description=plain,
        posted_at=posted_at,
        remote_type="remote" if "remote" in plain.lower() else None,
    )
