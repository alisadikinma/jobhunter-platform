from datetime import datetime

from pydantic import BaseModel, Field


class NormalizedJob(BaseModel):
    """Normalized job listing that every scraper must return.

    Maps 1:1 to the columns a ScrapedJob row needs (except DB-managed
    fields like id, scraped_at, relevance_score). The content_hash is
    computed by the deduplicator, not by individual scrapers.
    """

    source: str
    external_id: str | None = None
    source_url: str | None = None
    title: str
    company_name: str
    location: str | None = None
    description: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    remote_type: str | None = None
    job_type: str | None = None
    posted_at: datetime | None = None
    tech_stack: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}
