"""Apify account pool — 5-account free-tier rotation for Wellfound + emergency.

Contract per MVP plan:
- acquire_account(estimated_cost_usd) picks the oldest-used active account
  whose remaining credit (with 20% safety margin) covers the estimated cost.
  Uses FOR UPDATE SKIP LOCKED so concurrent callers never return the same row.
- record_usage() logs the run to apify_usage_log and transitions account
  status based on outcome: rate_limited -> 1h cooldown, 3+ failures ->
  suspended, credit exhausted -> exhausted (reactivated monthly by
  reset_monthly_quotas).
"""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.apify_account import ApifyAccount, ApifyUsageLog


class ApifyPoolExhausted(RuntimeError):
    """No active account has budget for the requested run."""


ACTIVE_THRESHOLD_WARNING = 2  # <2 active (of 5) -> warning banner
COOLDOWN_AFTER_RATE_LIMIT = timedelta(hours=1)
MAX_CONSECUTIVE_FAILURES = 3
SAFETY_MARGIN = Decimal("1.2")  # require 20% headroom on estimated cost


def _utcnow() -> datetime:
    return datetime.now(UTC)


def acquire_account(db: Session, estimated_cost_usd: float = 0.10) -> ApifyAccount:
    """Reserve an account under row-level lock. Caller must commit or rollback.

    After this returns, the row is locked until the transaction ends — so the
    caller should also update last_used_at / commit promptly. On success the
    returned account has last_used_at refreshed.
    """
    budget = Decimal(str(estimated_cost_usd)) * SAFETY_MARGIN

    stmt = (
        select(ApifyAccount)
        .where(ApifyAccount.status == "active")
        .where(
            (ApifyAccount.cooldown_until.is_(None))
            | (ApifyAccount.cooldown_until <= _utcnow())
        )
        .where(ApifyAccount.credit_used_usd + budget <= ApifyAccount.monthly_credit_usd)
        .order_by(
            ApifyAccount.priority.asc(),
            ApifyAccount.last_used_at.asc().nulls_first(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    account = db.execute(stmt).scalar_one_or_none()
    if account is None:
        raise ApifyPoolExhausted(
            f"No active Apify account has remaining budget for ${estimated_cost_usd:.4f}"
        )

    account.last_used_at = _utcnow()
    db.flush()
    return account


def record_usage(
    db: Session,
    account_id: int,
    *,
    cost_usd: float,
    jobs_scraped: int,
    status: str,
    actor_id: str | None = None,
    compute_units: float | None = None,
    duration_ms: int | None = None,
    error_message: str | None = None,
    scrape_run_id: int | None = None,
) -> ApifyUsageLog:
    """Log the run outcome and advance the account's state machine.

    status values:
        success       — credit deducted, last_success_at updated
        rate_limited  — credit deducted (API usually still charges), 1h cooldown
        quota_exceeded — account marked exhausted immediately
        failure       — consecutive_failures++; at MAX, account suspended
    """
    account = db.get(ApifyAccount, account_id)
    if account is None:
        raise ValueError(f"ApifyAccount id={account_id} not found")

    now = _utcnow()
    cost = Decimal(str(cost_usd))

    if status in {"success", "rate_limited"}:
        account.credit_used_usd = (account.credit_used_usd or Decimal("0")) + cost

    if status == "success":
        account.consecutive_failures = 0
        account.last_success_at = now
        account.last_error = None
    elif status == "rate_limited":
        account.cooldown_until = now + COOLDOWN_AFTER_RATE_LIMIT
        account.last_error = error_message or "rate_limited"
    elif status == "quota_exceeded":
        account.status = "exhausted"
        account.exhausted_at = now
        account.last_error = error_message or "quota_exceeded"
    elif status == "failure":
        account.consecutive_failures = (account.consecutive_failures or 0) + 1
        account.last_error = error_message
        if account.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            account.status = "suspended"

    # Margin-of-safety: if we've consumed most of the budget, mark exhausted
    # early so the next acquire call skips this account.
    if account.monthly_credit_usd and account.credit_used_usd:
        remaining = account.monthly_credit_usd - account.credit_used_usd
        if remaining < Decimal("0.50") and account.status == "active":
            account.status = "exhausted"
            account.exhausted_at = now

    log = ApifyUsageLog(
        account_id=account_id,
        actor_id=actor_id,
        compute_units=Decimal(str(compute_units)) if compute_units is not None else None,
        cost_usd=cost,
        jobs_scraped=jobs_scraped,
        status=status,
        error_message=error_message,
        duration_ms=duration_ms,
        scrape_run_id=scrape_run_id,
        started_at=now,
        completed_at=now,
    )
    db.add(log)
    db.flush()
    return log


def reset_monthly_quotas(db: Session) -> int:
    """Reactivate exhausted accounts whose quota_reset_at is in the past.

    Run via APScheduler daily (Phase 14). Returns the number of accounts
    reactivated.
    """
    now = _utcnow()
    stmt = (
        update(ApifyAccount)
        .where(ApifyAccount.status == "exhausted")
        .where(ApifyAccount.quota_reset_at.is_not(None))
        .where(ApifyAccount.quota_reset_at <= now)
        .values(
            status="active",
            credit_used_usd=Decimal("0"),
            exhausted_at=None,
            last_error=None,
            quota_reset_at=now + timedelta(days=30),
        )
    )
    result = db.execute(stmt)
    return result.rowcount or 0


def active_account_count(db: Session) -> int:
    stmt = select(ApifyAccount).where(ApifyAccount.status == "active")
    return len(db.execute(stmt).scalars().all())
