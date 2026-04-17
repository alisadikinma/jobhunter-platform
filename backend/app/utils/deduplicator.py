"""Content-hash based job deduplication.

Two listings with the same (title, company, first 200 chars of description)
after whitespace/case normalization produce the same SHA256 — that hash
populates scraped_jobs.content_hash (UNIQUE) so dupes are idempotent.
"""
import hashlib
import re

_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return _WHITESPACE.sub(" ", text.strip().lower())


def content_hash(title: str, company_name: str, description: str | None = None) -> str:
    snippet = (description or "")[:200]
    payload = f"{_normalize(title)}|{_normalize(company_name)}|{_normalize(snippet)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
