from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ApifyAccountCreate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    api_token: str = Field(min_length=1, max_length=500)
    priority: int = 100
    monthly_credit_usd: Decimal = Decimal("5.00")
    notes: str | None = None


class ApifyAccountUpdate(BaseModel):
    label: str | None = None
    priority: int | None = None
    status: str | None = None
    monthly_credit_usd: Decimal | None = None
    notes: str | None = None


class ApifyAccountBulkCreate(BaseModel):
    """One-shot import: textarea of `label,email,token` lines."""

    lines: list[str] = Field(min_length=1, max_length=50)


class ApifyAccountResponse(BaseModel):
    id: int
    label: str
    email: str
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


class ApifyTestResult(BaseModel):
    ok: bool
    message: str
