"""CRUD for the singleton mailbox configuration.

Exposes a single mailbox row that drives `mailer_service`. The frontend
combines this with the Apify Pool table on a unified Settings →
Credentials page so the user can manage both from one place.
"""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.mailbox import MailboxConfig
from app.models.user import User
from app.schemas.mailbox import (
    MailboxConfigResponse,
    MailboxConfigUpdate,
    MailboxTestResult,
)
from app.services import mailer_service
from app.services.encryption import encrypt_token

router = APIRouter(prefix="/api/mailbox", tags=["mailbox"])


def _to_response(row: MailboxConfig) -> MailboxConfigResponse:
    return MailboxConfigResponse(
        id=row.id,
        smtp_host=row.smtp_host,
        smtp_port=row.smtp_port,
        imap_host=row.imap_host,
        imap_port=row.imap_port,
        username=row.username,
        # Never echo the encrypted password; UI should treat empty mask = unset.
        password_masked="********" if row.password_encrypted else "",
        from_address=row.from_address,
        from_name=row.from_name,
        drafts_folder=row.drafts_folder,
        is_active=row.is_active,
        last_test_at=row.last_test_at,
        last_test_status=row.last_test_status,
        last_test_message=row.last_test_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _empty() -> MailboxConfig:
    """Construct an in-memory stub matching the column server_defaults."""
    now = datetime.now(UTC)
    return MailboxConfig(
        id=1,
        smtp_host="",
        smtp_port=465,
        imap_host="",
        imap_port=993,
        username="",
        password_encrypted="",
        from_address="",
        from_name="",
        drafts_folder="Drafts",
        is_active=False,
        created_at=now,
        updated_at=now,
    )


@router.get("/config", response_model=MailboxConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(MailboxConfig, 1)
    if row is None:
        # Return a stub so the form has something to render against.
        row = _empty()
    return _to_response(row)


@router.put("/config", response_model=MailboxConfigResponse)
def update_config(
    body: MailboxConfigUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(MailboxConfig, 1)
    created = False
    if row is None:
        row = MailboxConfig(id=1)
        db.add(row)
        created = True

    row.smtp_host = body.smtp_host
    row.smtp_port = body.smtp_port
    row.imap_host = body.imap_host
    row.imap_port = body.imap_port
    row.username = body.username
    row.from_address = body.from_address
    row.from_name = body.from_name
    row.drafts_folder = body.drafts_folder

    # Password: only overwrite if a new one was provided.
    if body.password:
        row.password_encrypted = encrypt_token(body.password)
    elif created:
        # Net-new row with no password is a hard error — can't authenticate.
        raise HTTPException(
            status_code=422,
            detail="password is required when creating mailbox config",
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
    row = db.get(MailboxConfig, 1)
    if row is None:
        return
    db.delete(row)
    db.commit()


@router.post("/test", response_model=MailboxTestResult)
def test_connection(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(MailboxConfig, 1)
    if row is None or not row.username or not row.password_encrypted:
        raise HTTPException(
            status_code=409,
            detail="No mailbox config to test — save credentials first",
        )

    try:
        imap_ok, smtp_ok, message = mailer_service.test_connection(db)
    except mailer_service.MailerDisabled:
        raise HTTPException(status_code=409, detail="Mailbox config not yet saved")
    except mailer_service.MailerError as e:
        imap_ok, smtp_ok, message = False, False, str(e)

    row.last_test_at = datetime.now(UTC)
    row.last_test_status = "ok" if (imap_ok and smtp_ok) else "failed"
    row.last_test_message = message[:1000]
    # Activate only when both legs work — we want IMAP for drafts AND SMTP
    # for follow-ups before flipping the flag.
    row.is_active = imap_ok and smtp_ok
    db.commit()

    return MailboxTestResult(
        ok=imap_ok and smtp_ok,
        imap_ok=imap_ok,
        smtp_ok=smtp_ok,
        message=message,
    )
