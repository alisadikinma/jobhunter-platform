"""Firecrawl pool — multi-account rotation for JD/company enrichment.

Same shape as `apify_pool.py`: when an account hits its credit cap or
rate-limit, the pool acquires the next active account. Each row holds
its own api_url so a single pool can mix self-hosted + SaaS Firecrawl
endpoints.

`FirecrawlService` becomes a *call-site* helper that:
  1. Acquires an account from the pool under FOR UPDATE SKIP LOCKED.
  2. Issues the HTTP scrape.
  3. Records usage outcome → credits used, cooldown, suspension.
  4. On 401/429/quota errors, mark + retry against the next account
     (up to MAX_POOL_RETRIES).

If no DB row exists, falls back to `settings.FIRECRAWL_*` env vars so
the system still works pre-UI-setup (e.g. CI tests).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.firecrawl_account import FirecrawlAccount
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)


COOLDOWN_AFTER_RATE_LIMIT = timedelta(hours=1)
MAX_CONSECUTIVE_FAILURES = 3
MAX_POOL_RETRIES = 3
SAFETY_MARGIN = Decimal("1.2")
DEFAULT_COST_PER_SCRAPE = Decimal("0.001")  # 1 credit / page on Firecrawl SaaS


class FirecrawlPoolExhausted(RuntimeError):
    """No active Firecrawl account has budget for the requested scrape."""


@dataclass
class _ResolvedConfig:
    """Resolved config used for a single scrape — either pool account or env."""

    account_id: int | None
    api_url: str
    api_token: str
    timeout_s: int


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _env_fallback() -> _ResolvedConfig:
    return _ResolvedConfig(
        account_id=None,
        api_url=settings.FIRECRAWL_API_URL,
        api_token=settings.FIRECRAWL_API_KEY,
        timeout_s=settings.FIRECRAWL_TIMEOUT_S,
    )


def acquire_account(db: Session, *, estimated_cost_usd: Decimal = DEFAULT_COST_PER_SCRAPE) -> FirecrawlAccount:
    """Reserve an account under row-level lock. Caller commits/rollbacks.

    Picks the lowest-priority, oldest-used active account that has budget
    (with 20% safety margin) for the cost. Accounts with
    `monthly_credit_usd=0` are treated as unlimited (self-hosted).
    """
    budget = estimated_cost_usd * SAFETY_MARGIN

    stmt = (
        select(FirecrawlAccount)
        .where(FirecrawlAccount.status == "active")
        .where(
            (FirecrawlAccount.cooldown_until.is_(None))
            | (FirecrawlAccount.cooldown_until <= _utcnow())
        )
        .where(
            # Either unlimited (monthly_credit_usd <= 0) or has budget
            (FirecrawlAccount.monthly_credit_usd <= 0)
            | (FirecrawlAccount.credit_used_usd + budget <= FirecrawlAccount.monthly_credit_usd)
        )
        .order_by(
            FirecrawlAccount.priority.asc(),
            FirecrawlAccount.last_used_at.asc().nulls_first(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    account = db.execute(stmt).scalar_one_or_none()
    if account is None:
        raise FirecrawlPoolExhausted(
            f"No active Firecrawl account has budget for ${estimated_cost_usd}"
        )

    account.last_used_at = _utcnow()
    db.flush()
    return account


def record_usage(
    db: Session,
    account_id: int,
    *,
    status: str,
    cost_usd: Decimal = DEFAULT_COST_PER_SCRAPE,
    error_message: str | None = None,
) -> None:
    """Advance the account's state machine after a scrape attempt.

    status:
        success        — credit deducted, last_success_at updated
        rate_limited   — credit deducted, 1h cooldown
        quota_exceeded — account marked exhausted immediately
        failure        — consecutive_failures++; at MAX, account suspended
    """
    account = db.get(FirecrawlAccount, account_id)
    if account is None:
        return

    now = _utcnow()
    cost = cost_usd

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

    # Margin-of-safety: drop to exhausted when budget nearly gone.
    if account.monthly_credit_usd and account.monthly_credit_usd > 0:
        remaining = account.monthly_credit_usd - (account.credit_used_usd or Decimal("0"))
        if remaining < Decimal("0.05") and account.status == "active":
            account.status = "exhausted"
            account.exhausted_at = now

    db.flush()


def active_account_count(db: Session) -> int:
    stmt = select(FirecrawlAccount).where(FirecrawlAccount.status == "active")
    return len(db.execute(stmt).scalars().all())


# --- HTTP layer --------------------------------------------------------------


class FirecrawlService:
    """Stateless wrapper over the pool. Each scrape acquires an account
    from `acquire_account` and records the outcome via `record_usage`.

    If `db is None`, falls back to env-var single-config mode so legacy
    callers (and tests) keep working.
    """

    def __init__(
        self,
        client: httpx.Client | None = None,
        db: Session | None = None,
    ) -> None:
        self._db = db
        self._owns_client = client is None
        # Default 30s timeout; per-scrape we honour per-account if available.
        self._client = client or httpx.Client(timeout=30)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "FirecrawlService":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def scrape(self, url: str, opts: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True,
        }
        if opts:
            payload.update(opts)
        return self._post_with_pool(payload)

    def scrape_with_extraction(
        self, url: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "url": url,
            "formats": ["extract"],
            "extract": {"schema": schema},
        }
        return self._post_with_pool(payload)

    # --- internals -------------------------------------------------

    def _post_with_pool(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Env-fallback path: no DB, single-config mode.
        if self._db is None:
            cfg = _env_fallback()
            return self._post_once(payload, cfg)

        last_error: str | None = None
        for _ in range(MAX_POOL_RETRIES):
            try:
                account = acquire_account(self._db)
            except FirecrawlPoolExhausted as e:
                # Pool has nothing left → fall back to env once and stop.
                cfg = _env_fallback()
                if cfg.api_url:
                    return self._post_once(payload, cfg)
                return _empty_response(str(e))

            try:
                api_token = decrypt_token(account.api_token) if account.api_token else ""
            except Exception as e:
                record_usage(self._db, account.id, status="failure", error_message=f"decrypt: {e}")
                self._db.commit()
                last_error = str(e)
                continue

            cfg = _ResolvedConfig(
                account_id=account.id,
                api_url=account.api_url,
                api_token=api_token,
                timeout_s=30,
            )
            result = self._post_once(payload, cfg)

            outcome = _classify(result)
            record_usage(self._db, account.id, status=outcome, error_message=result.get("error"))
            self._db.commit()

            if outcome == "success":
                return result
            last_error = result.get("error") or outcome
            # Loop body picks up the next account.

        return _empty_response(last_error or "all pool retries exhausted")

    def _post_once(self, payload: dict[str, Any], cfg: _ResolvedConfig) -> dict[str, Any]:
        endpoint = f"{cfg.api_url.rstrip('/')}/v1/scrape"
        headers = {"Content-Type": "application/json"}
        if cfg.api_token:
            headers["Authorization"] = f"Bearer {cfg.api_token}"

        try:
            resp = self._client.post(endpoint, json=payload, headers=headers, timeout=cfg.timeout_s)
            if resp.status_code == 429:
                return _empty_response("rate_limited", status_code=429)
            if resp.status_code == 402:
                return _empty_response("quota_exceeded", status_code=402)
            if resp.status_code in {401, 403}:
                return _empty_response(f"auth failed ({resp.status_code})", status_code=resp.status_code)
            resp.raise_for_status()
            body = resp.json()
        except httpx.HTTPError as e:
            log.warning("firecrawl: HTTP error for %s: %s", payload.get("url"), e)
            return _empty_response(str(e))
        except ValueError as e:
            log.warning("firecrawl: malformed JSON for %s: %s", payload.get("url"), e)
            return _empty_response("malformed response")

        if not body.get("success", True):
            return _empty_response(body.get("error", "scrape failed"))

        data = body.get("data") or {}
        metadata = data.get("metadata") or {}
        return {
            "markdown": data.get("markdown", "") or "",
            "html": data.get("html", "") or "",
            "title": metadata.get("title") or metadata.get("ogTitle"),
            "description": metadata.get("description") or metadata.get("ogDescription"),
            "metadata": metadata,
            "extract": data.get("extract"),
            "error": None,
            "status_code": 200,
        }


def _classify(result: dict[str, Any]) -> str:
    if result.get("error") is None:
        return "success"
    code = result.get("status_code")
    if code == 429:
        return "rate_limited"
    if code == 402:
        return "quota_exceeded"
    return "failure"


def test_account_connection(
    db: Session,
    account_id: int,
    *,
    sample_url: str = "https://example.com",
) -> tuple[bool, str, int]:
    """Live scrape against `sample_url` for ONE account — used by per-account
    Test button in the UI.
    """
    account = db.get(FirecrawlAccount, account_id)
    if account is None:
        return False, "account not found", 0

    try:
        token = decrypt_token(account.api_token) if account.api_token else ""
    except Exception as e:
        return False, f"failed to decrypt token: {e}", 0

    endpoint = f"{account.api_url.rstrip('/')}/v1/scrape"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"url": sample_url, "formats": ["markdown"], "onlyMainContent": True}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPStatusError as e:
        return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}", 0
    except httpx.HTTPError as e:
        return False, f"connection failed: {e}", 0
    except ValueError:
        return False, "malformed JSON response", 0

    if not body.get("success", True):
        return False, body.get("error", "scrape failed"), 0

    data = body.get("data") or {}
    md = data.get("markdown", "") or ""
    return True, f"OK — fetched {len(md)} chars from {sample_url}", len(md)


def _empty_response(error: str, *, status_code: int | None = None) -> dict[str, Any]:
    return {
        "markdown": "",
        "html": "",
        "title": None,
        "description": None,
        "metadata": {},
        "extract": None,
        "error": error,
        "status_code": status_code,
    }
