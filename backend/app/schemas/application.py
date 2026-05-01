from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Kanban columns — ordered; frontend uses this order left → right.
ApplicationStatus = Literal[
    "targeting", "cv_generating", "cv_ready", "applied", "email_sent",
    "replied", "interview_scheduled", "interviewed", "offered",
    "accepted", "rejected", "ghosted",
]


KANBAN_STATUSES: tuple[str, ...] = (
    "targeting", "cv_generating", "cv_ready", "applied", "email_sent",
    "replied", "interview_scheduled", "interviewed", "offered",
    "accepted", "rejected", "ghosted",
)


class ApplicationActivityResponse(BaseModel):
    id: int
    activity_type: str
    description: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationResponse(BaseModel):
    id: int
    job_id: int | None
    company_id: int | None
    status: str
    targeted_at: datetime | None
    applied_at: datetime | None
    email_sent_at: datetime | None
    replied_at: datetime | None
    interview_at: datetime | None
    offered_at: datetime | None
    closed_at: datetime | None
    applied_via: str | None
    applied_url: str | None
    contact_name: str | None
    contact_email: str | None
    contact_title: str | None
    salary_asked: int | None
    salary_offered: int | None
    notes: str | None
    tags: list[str] | None
    cv_id: int | None
    email_draft_id: int | None
    cover_letter_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationDetail(ApplicationResponse):
    activities: list[ApplicationActivityResponse] = Field(default_factory=list)


class ApplicationCreate(BaseModel):
    job_id: int


class EasyApplyRequest(BaseModel):
    job_id: int


class EasyApplyResponse(BaseModel):
    application_id: int
    cv_agent_job_id: int
    email_agent_job_id: int
    generated_cv_id: int


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    tags: list[str] | None = None
    applied_via: str | None = None
    applied_url: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_title: str | None = None
    salary_asked: int | None = None
    salary_offered: int | None = None


class KanbanBoard(BaseModel):
    columns: dict[str, list[ApplicationResponse]]


class ApplicationStats(BaseModel):
    total: int
    by_status: dict[str, int]
    response_rate: float  # replied / email_sent (0.0 when denominator=0)
    offer_rate: float  # offered / applied
    avg_days_to_reply: float | None
    pipeline_value_usd: int  # sum of salary_asked for active applications


class ActivityTimelineDay(BaseModel):
    date: str  # YYYY-MM-DD (UTC)
    count: int


class ActivityTimeline(BaseModel):
    days: list[ActivityTimelineDay]
