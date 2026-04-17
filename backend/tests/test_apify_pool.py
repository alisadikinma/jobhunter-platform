"""Apify pool integration tests — run against real Postgres (needs FOR UPDATE SKIP LOCKED)."""
from datetime import UTC, timedelta
from decimal import Decimal

import pytest

from app.models.apify_account import ApifyAccount
from app.services import apify_pool
from app.services.apify_pool import (
    ApifyPoolExhausted,
    acquire_account,
    active_account_count,
    record_usage,
    reset_monthly_quotas,
)

pytestmark = pytest.mark.integration


def _seed_account(
    session, *, label: str, priority: int = 100, credit_used: str = "0.00",
    monthly_credit: str = "5.00", status: str = "active", **kwargs,
) -> ApifyAccount:
    account = ApifyAccount(
        label=label,
        email=f"{label}@test.local",
        api_token=f"enc-{label}",
        priority=priority,
        status=status,
        monthly_credit_usd=Decimal(monthly_credit),
        credit_used_usd=Decimal(credit_used),
        **kwargs,
    )
    session.add(account)
    session.flush()
    return account


def test_acquire_returns_active_account_with_budget(pg_session):
    _seed_account(pg_session, label="a1")
    account = acquire_account(pg_session, estimated_cost_usd=0.10)
    assert account.label == "a1"
    assert account.last_used_at is not None


def test_acquire_raises_when_pool_exhausted(pg_session):
    _seed_account(pg_session, label="exhausted", status="exhausted")
    with pytest.raises(ApifyPoolExhausted):
        acquire_account(pg_session, estimated_cost_usd=0.10)


def test_acquire_skips_account_over_budget(pg_session):
    # Only $0.30 remaining; request with safety margin is $0.12 -> OK
    _seed_account(pg_session, label="tight", credit_used="4.70")
    account = acquire_account(pg_session, estimated_cost_usd=0.10)
    assert account.label == "tight"

    # Request $0.40 -> safety margin $0.48 > $0.30 remaining -> reject
    with pytest.raises(ApifyPoolExhausted):
        acquire_account(pg_session, estimated_cost_usd=0.40)


def test_acquire_uses_lru_across_accounts(pg_session):
    from datetime import datetime

    now = datetime.now(UTC)
    _seed_account(pg_session, label="older", last_used_at=now - timedelta(hours=2))
    _seed_account(pg_session, label="newer", last_used_at=now - timedelta(minutes=10))
    _seed_account(pg_session, label="never_used")  # last_used_at NULL -> first

    # NULLS FIRST: the never-used one wins.
    first = acquire_account(pg_session, estimated_cost_usd=0.05)
    assert first.label == "never_used"


def test_acquire_respects_priority_over_lru(pg_session):
    from datetime import datetime

    now = datetime.now(UTC)
    _seed_account(pg_session, label="low_prio_never_used", priority=200)
    _seed_account(pg_session, label="high_prio_recent", priority=10, last_used_at=now)

    chosen = acquire_account(pg_session, estimated_cost_usd=0.05)
    assert chosen.label == "high_prio_recent"


def test_acquire_skips_cooldown(pg_session):
    from datetime import datetime

    now = datetime.now(UTC)
    _seed_account(pg_session, label="cooling", cooldown_until=now + timedelta(minutes=30))
    _seed_account(pg_session, label="ready")

    chosen = acquire_account(pg_session, estimated_cost_usd=0.05)
    assert chosen.label == "ready"


def test_record_usage_success_deducts_credit_and_logs(pg_session):
    account = _seed_account(pg_session, label="u1")
    record_usage(
        pg_session,
        account.id,
        cost_usd=0.15,
        jobs_scraped=12,
        status="success",
        actor_id="bebity/wellfound-jobs-scraper",
        duration_ms=4200,
    )
    pg_session.refresh(account)
    assert account.credit_used_usd == Decimal("0.15")
    assert account.last_success_at is not None
    assert account.consecutive_failures == 0
    assert account.status == "active"


def test_record_usage_rate_limited_sets_cooldown(pg_session):
    account = _seed_account(pg_session, label="rl")
    record_usage(pg_session, account.id, cost_usd=0.05, jobs_scraped=0, status="rate_limited")
    pg_session.refresh(account)
    assert account.cooldown_until is not None
    assert account.cooldown_until > apify_pool._utcnow()


def test_record_usage_failure_suspends_after_threshold(pg_session):
    account = _seed_account(pg_session, label="flaky")
    for _ in range(apify_pool.MAX_CONSECUTIVE_FAILURES):
        record_usage(
            pg_session, account.id, cost_usd=0, jobs_scraped=0, status="failure",
            error_message="500 Internal",
        )
    pg_session.refresh(account)
    assert account.status == "suspended"


def test_record_usage_quota_exceeded_marks_exhausted(pg_session):
    account = _seed_account(pg_session, label="q")
    record_usage(
        pg_session, account.id, cost_usd=0, jobs_scraped=0, status="quota_exceeded",
    )
    pg_session.refresh(account)
    assert account.status == "exhausted"
    assert account.exhausted_at is not None


def test_record_usage_auto_exhausts_when_below_safety_margin(pg_session):
    account = _seed_account(pg_session, label="near_empty", credit_used="4.60")
    # Spending $0.10 leaves $0.30 remaining — below $0.50 floor.
    record_usage(pg_session, account.id, cost_usd=0.10, jobs_scraped=5, status="success")
    pg_session.refresh(account)
    assert account.status == "exhausted"


def test_reset_monthly_quotas_reactivates_due_accounts(pg_session):
    from datetime import datetime

    now = datetime.now(UTC)
    exhausted_due = _seed_account(
        pg_session, label="due", status="exhausted",
        credit_used="5.00", quota_reset_at=now - timedelta(hours=1),
    )
    exhausted_future = _seed_account(
        pg_session, label="future", status="exhausted",
        credit_used="5.00", quota_reset_at=now + timedelta(days=5),
    )

    count = reset_monthly_quotas(pg_session)
    pg_session.commit()
    pg_session.refresh(exhausted_due)
    pg_session.refresh(exhausted_future)

    assert count == 1
    assert exhausted_due.status == "active"
    assert exhausted_due.credit_used_usd == Decimal("0")
    assert exhausted_future.status == "exhausted"


def test_active_account_count(pg_session):
    _seed_account(pg_session, label="a")
    _seed_account(pg_session, label="b")
    _seed_account(pg_session, label="c", status="exhausted")

    assert active_account_count(pg_session) == 2
