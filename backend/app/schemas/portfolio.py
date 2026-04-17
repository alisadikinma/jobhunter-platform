from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Variant = Literal["vibe_coding", "ai_automation", "ai_video"]
PortfolioStatus = Literal["draft", "published", "skipped"]


class PortfolioAssetResponse(BaseModel):
    id: int
    asset_type: str | None
    title: str | None
    url: str | None
    thumbnail_url: str | None
    description: str | None
    tech_stack: list[str] | None
    tags: list[str] | None
    metrics: dict | None
    relevance_hint: list[Variant] | None
    display_priority: int
    is_featured: bool
    status: PortfolioStatus
    auto_generated: bool
    source_path: str | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioAssetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    url: str | None = None
    thumbnail_url: str | None = None
    description: str | None = None
    asset_type: str | None = "external"
    tech_stack: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metrics: dict | None = None
    relevance_hint: list[Variant] = Field(default_factory=list)
    display_priority: int = 50
    is_featured: bool = False


class PortfolioAssetUpdate(BaseModel):
    title: str | None = None
    url: str | None = None
    thumbnail_url: str | None = None
    description: str | None = None
    tech_stack: list[str] | None = None
    tags: list[str] | None = None
    metrics: dict | None = None
    relevance_hint: list[Variant] | None = None
    display_priority: int | None = None
    is_featured: bool | None = None


class PortfolioAuditRun(BaseModel):
    """Optional override of scan paths — defaults come from settings."""

    scan_paths: list[str] | None = None


class PortfolioAuditResult(BaseModel):
    new_drafts: int
    updated: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
