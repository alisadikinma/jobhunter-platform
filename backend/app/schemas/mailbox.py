from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class MailboxConfigUpdate(BaseModel):
    smtp_host: str = Field(min_length=1, max_length=255)
    smtp_port: int = Field(ge=1, le=65535, default=465)
    imap_host: str = Field(min_length=1, max_length=255)
    imap_port: int = Field(ge=1, le=65535, default=993)
    username: EmailStr
    password: str | None = Field(default=None, max_length=500)  # null = leave existing
    from_address: EmailStr
    from_name: str = Field(default="", max_length=255)
    drafts_folder: str = Field(default="Drafts", max_length=100)


class MailboxConfigResponse(BaseModel):
    id: int
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    username: str
    password_masked: str  # always "********" when set, "" when empty
    from_address: str
    from_name: str
    drafts_folder: str
    is_active: bool
    last_test_at: datetime | None
    last_test_status: str | None
    last_test_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MailboxTestResult(BaseModel):
    ok: bool
    imap_ok: bool
    smtp_ok: bool
    message: str
