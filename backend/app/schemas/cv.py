"""Master CV schema — JSON Resume + 3-variant extensions.

`relevance_hint` values are locked to the 3 target variants; anything else
is a 422 from the backend (and a red highlight in the frontend form).
"""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Variant = Literal["vibe_coding", "ai_automation", "ai_video"]


class LocationModel(BaseModel):
    city: str | None = None
    region: str | None = None
    country: str | None = None
    remote: bool = False

    model_config = {"extra": "allow"}


class ProfileLink(BaseModel):
    network: str
    username: str | None = None
    url: str


class SummaryVariants(BaseModel):
    """Three hand-crafted opening paragraphs, one per target variant."""

    vibe_coding: str
    ai_automation: str
    ai_video: str


class Basics(BaseModel):
    name: str = Field(min_length=1)
    label: str | None = None
    email: EmailStr
    phone: str | None = None
    url: str | None = None
    summary: str | None = None
    location: LocationModel | None = None
    profiles: list[ProfileLink] = Field(default_factory=list)
    summary_variants: SummaryVariants


class Highlight(BaseModel):
    text: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    metrics: dict | None = None
    # Locked to the 3 target variants — frontend and backend both enforce.
    relevance_hint: list[Variant] = Field(default_factory=list)


class WorkEntry(BaseModel):
    company: str
    position: str
    start_date: str | None = None
    end_date: str | None = None
    summary: str | None = None
    highlights: list[Highlight] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class EducationEntry(BaseModel):
    institution: str
    area: str | None = None
    study_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None

    model_config = {"extra": "allow"}


class ProjectEntry(BaseModel):
    name: str
    description: str | None = None
    url: str | None = None
    highlights: list[Highlight] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class MasterCVContent(BaseModel):
    """Root schema — stored as master_cv.content JSONB."""

    basics: Basics
    work: list[WorkEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: dict[str, list[str]] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class MasterCVResponse(BaseModel):
    id: int
    version: int
    is_active: bool
    content: MasterCVContent
    source_type: str | None
    synced_at: str | None = None

    model_config = {"from_attributes": True}


class MasterCVUpdateRequest(BaseModel):
    content: MasterCVContent
    raw_markdown: str | None = None


class MasterCVImportURLRequest(BaseModel):
    url: str = Field(min_length=1)


# --- generated CV (Phase 10) ---------------------------------------

class CVGenerateRequest(BaseModel):
    application_id: int


class GeneratedCVResponse(BaseModel):
    id: int
    application_id: int | None
    job_id: int | None
    master_cv_id: int | None
    tailored_markdown: str | None
    variant_used: str | None
    confidence: int | None
    ats_score: int | None
    keyword_matches: list[str] | None
    missing_keywords: list[str] | None
    suggestions: dict | None
    status: str
    docx_path: str | None
    pdf_path: str | None

    model_config = {"from_attributes": True}


class GeneratedCVUpdate(BaseModel):
    tailored_markdown: str | None = None


class CVGenerateEnqueued(BaseModel):
    generated_cv_id: int
    agent_job_id: int
    status: str
