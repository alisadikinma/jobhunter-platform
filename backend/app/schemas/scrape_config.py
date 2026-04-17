from datetime import datetime

from pydantic import BaseModel, Field


class ScrapeConfigResponse(BaseModel):
    id: int
    name: str
    is_active: bool
    variant_target: str | None
    keywords: list[str]
    excluded_keywords: list[str] | None
    locations: list[str] | None
    job_types: list[str] | None
    remote_only: bool
    min_salary: int | None
    sources: list[str]
    max_results_per_source: int
    cron_expression: str
    last_run_at: datetime | None
    last_run_results: dict | None

    model_config = {"from_attributes": True}


class ScrapeConfigCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    variant_target: str | None = None
    keywords: list[str] = Field(min_length=1)
    excluded_keywords: list[str] | None = None
    locations: list[str] | None = None
    job_types: list[str] | None = None
    remote_only: bool = True
    min_salary: int | None = None
    sources: list[str] = Field(default_factory=list)
    max_results_per_source: int = 30
    cron_expression: str = "0 */3 * * *"
    is_active: bool = True


class ScrapeConfigUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    variant_target: str | None = None
    keywords: list[str] | None = None
    excluded_keywords: list[str] | None = None
    locations: list[str] | None = None
    sources: list[str] | None = None
    max_results_per_source: int | None = None
    cron_expression: str | None = None


class ScrapeRunRequest(BaseModel):
    config_id: int | None = None
    # Inline overrides for ad-hoc runs without a saved config:
    keywords: list[str] | None = None
    sources: list[str] | None = None
    locations: list[str] | None = None
    variant_target: str | None = None
    max_results_per_source: int = 30


class ScrapeRunResponse(BaseModel):
    total_scraped: int
    new_jobs: int
    duplicates: int
    per_source: dict[str, int]
    errors: list[str] = Field(default_factory=list)
