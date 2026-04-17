from datetime import datetime
from typing import Literal

from pydantic import BaseModel

EmailType = Literal["initial", "follow_up_1", "follow_up_2"]


class EmailDraftResponse(BaseModel):
    id: int
    application_id: int | None
    job_id: int | None
    email_type: str
    subject: str | None
    body: str
    recipient_email: str | None
    recipient_name: str | None
    strategy: str | None
    personalization: dict | None
    status: str
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EmailDraftUpdate(BaseModel):
    subject: str | None = None
    body: str | None = None
    recipient_email: str | None = None
    recipient_name: str | None = None


class EmailGenerateRequest(BaseModel):
    application_id: int
    strategy: str | None = None


class EmailGenerateEnqueued(BaseModel):
    application_id: int
    agent_job_id: int
    status: str


class EmailFollowupRequest(BaseModel):
    application_id: int
    email_type: EmailType = "follow_up_1"
