"""CRUD for the singleton Firecrawl configuration.

Mirrors the mailbox API shape: GET/PUT/DELETE/POST test. The Fernet-
encrypted api_key is never echoed back — UI sees `api_key_masked`.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.firecrawl_config import FirecrawlConfig
from app.models.user import User
from app.schemas.firecrawl import (
    FirecrawlConfigResponse,
    FirecrawlConfigUpdate,
    FirecrawlTestResult,
)
from app.services import firecrawl_service
from app.services.encryption import encrypt_token

router = APIRouter(prefix="/api/firecrawl", tags=["firecrawl"])


def _to_response(row: FirecrawlConfig) -> FirecrawlConfigResponse:
    return FirecrawlConfigResponse(
        id=row.id,
        api_url=row.api_url,
        api_key_masked="********" if row.api_key_encrypted else "",
        timeout_s=row.timeout_s,
        is_active=row.is_active,
        last_test_at=row.last_test_at,
        last_test_status=row.last_test_status,
        last_test_message=row.last_test_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _empty() -> FirecrawlConfig:
    """Stub matching column server_defaults for first-render."""
    now = datetime.now(UTC)
    return FirecrawlConfig(
        id=1,
        api_url="https://api.firecrawl.dev",
        api_key_encrypted="",
        timeout_s=60,
        is_active=False,
        created_at=now,
        updated_at=now,
    )


@router.get("/config", response_model=FirecrawlConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(FirecrawlConfig, 1)
    if row is None:
        row = _empty()
    return _to_response(row)


@router.put("/config", response_model=FirecrawlConfigResponse)
def update_config(
    body: FirecrawlConfigUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(FirecrawlConfig, 1)
    created = False
    if row is None:
        row = FirecrawlConfig(id=1)
        db.add(row)
        created = True

    row.api_url = body.api_url
    row.timeout_s = body.timeout_s

    if body.api_key:
        row.api_key_encrypted = encrypt_token(body.api_key)
    elif created and body.api_url.startswith("https://api.firecrawl.dev"):
        # SaaS Firecrawl requires a key. Self-hosted (api_url like
        # http://firecrawl-api:3002) typically doesn't, so we only error
        # when the user is pointing at the hosted endpoint.
        raise HTTPException(
            status_code=422,
            detail="api_key is required when targeting Firecrawl SaaS",
        )

    # Editing config invalidates any prior 'tested OK' state.
    row.is_active = False
    row.last_test_at = None
    row.last_test_status = None
    row.last_test_message = None

    db.commit()
    db.refresh(row)
    return _to_response(row)


@router.delete("/config", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(FirecrawlConfig, 1)
    if row is None:
        return
    db.delete(row)
    db.commit()


@router.post("/test", response_model=FirecrawlTestResult)
def test_connection(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(FirecrawlConfig, 1)
    if row is None or not row.api_url:
        raise HTTPException(
            status_code=409,
            detail="No Firecrawl config to test — save credentials first",
        )

    ok, message, sample_chars = firecrawl_service.test_connection(db)

    row.last_test_at = datetime.now(UTC)
    row.last_test_status = "ok" if ok else "failed"
    row.last_test_message = message[:1000]
    row.is_active = ok
    db.commit()

    return FirecrawlTestResult(ok=ok, message=message, sample_chars=sample_chars)
