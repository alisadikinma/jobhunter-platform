from datetime import datetime

from pydantic import BaseModel, Field


class EnrichmentResponse(BaseModel):
    ok: bool
    source: str  # "aggregator" | "firecrawl_enriched"
    length_before: int
    length_after: int
    message: str | None = None


class CompanyResearchResponse(BaseModel):
    ok: bool
    domain: str | None
    title: str | None
    markdown_chars: int
    message: str | None = None


class FirecrawlConfigUpdate(BaseModel):
    api_url: str = Field(min_length=1, max_length=500)
    api_key: str | None = Field(default=None, max_length=500)  # null = leave existing
    timeout_s: int = Field(ge=5, le=300, default=60)


class FirecrawlConfigResponse(BaseModel):
    id: int
    api_url: str
    api_key_masked: str  # "********" when set, "" when empty
    timeout_s: int
    is_active: bool
    last_test_at: datetime | None
    last_test_status: str | None
    last_test_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FirecrawlTestResult(BaseModel):
    ok: bool
    message: str
    sample_chars: int = 0  # length of markdown sample on success
