from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    source: str
    source_url: str | None
    external_id: str | None
    title: str
    company_name: str
    location: str | None
    description: str | None
    description_source: str | None
    tech_stack: list[str] | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str | None
    remote_type: str | None
    job_type: str | None

    relevance_score: int | None
    score_reasons: dict | None
    match_keywords: list[str] | None
    suggested_variant: str | None

    status: str
    is_favorite: bool
    user_irrelevant: bool = False
    scraped_at: datetime | None
    posted_at: datetime | None
    enriched_at: datetime | None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int


class JobUpdate(BaseModel):
    status: str | None = None
    is_favorite: bool | None = None
    user_irrelevant: bool | None = None
    notes: str | None = None


class JobStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    by_variant: dict[str, int]
    high_score_count: int  # jobs with relevance_score >= 80


JobSortField = Literal["relevance_score", "scraped_at", "posted_at"]
JobSortOrder = Literal["asc", "desc"]
