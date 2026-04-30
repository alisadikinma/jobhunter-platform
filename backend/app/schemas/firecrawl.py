from datetime import datetime
from decimal import Decimal

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


# --- Firecrawl pool schemas (mirror Apify) -----------------------------------


class FirecrawlAccountCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    email: str = Field(default="", max_length=255)
    api_url: str = Field(min_length=1, max_length=500, default="https://api.firecrawl.dev")
    api_token: str = Field(default="", max_length=500)
    priority: int = 100
    monthly_credit_usd: Decimal = Decimal("0.50")
    notes: str | None = None


class FirecrawlAccountUpdate(BaseModel):
    label: str | None = None
    email: str | None = None
    api_url: str | None = None
    priority: int | None = None
    status: str | None = None
    monthly_credit_usd: Decimal | None = None
    notes: str | None = None


class FirecrawlAccountBulkCreate(BaseModel):
    """One-shot import: textarea of `label,api_url,token[,email]` lines."""

    lines: list[str] = Field(min_length=1, max_length=50)


class FirecrawlAccountResponse(BaseModel):
    id: int
    label: str
    email: str
    api_url: str
    token_masked: str
    priority: int
    status: str
    monthly_credit_usd: Decimal
    credit_used_usd: Decimal
    cooldown_until: datetime | None
    last_used_at: datetime | None
    last_success_at: datetime | None
    consecutive_failures: int
    last_error: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class FirecrawlTestResult(BaseModel):
    ok: bool
    message: str
    sample_chars: int = 0
