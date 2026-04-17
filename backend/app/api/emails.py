"""Email drafts — generate + edit + approve."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.email_draft import EmailDraft
from app.models.user import User
from app.schemas.email import (
    EmailDraftResponse,
    EmailDraftUpdate,
    EmailFollowupRequest,
    EmailGenerateEnqueued,
    EmailGenerateRequest,
)
from app.services.email_generator import EmailGenerationError, generate_emails

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.post("/generate", response_model=EmailGenerateEnqueued, status_code=status.HTTP_202_ACCEPTED)
def generate(
    body: EmailGenerateRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    try:
        aj_id = generate_emails(db, body.application_id)
    except EmailGenerationError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return EmailGenerateEnqueued(
        application_id=body.application_id,
        agent_job_id=aj_id,
        status="pending",
    )


@router.post("/generate-followup", response_model=EmailGenerateEnqueued, status_code=status.HTTP_202_ACCEPTED)
def generate_followup(
    body: EmailFollowupRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """Regenerate a specific follow-up. Uses the same /cold-email skill
    but the callback handler will target only the requested email_type row."""
    application = db.get(Application, body.application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    aj_id = generate_emails(db, body.application_id)
    return EmailGenerateEnqueued(
        application_id=body.application_id,
        agent_job_id=aj_id,
        status="pending",
    )


@router.get("", response_model=list[EmailDraftResponse])
def list_by_application(
    application_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    rows = (
        db.query(EmailDraft)
        .filter(EmailDraft.application_id == application_id)
        .order_by(EmailDraft.email_type.asc())
        .all()
    )
    return [EmailDraftResponse.model_validate(r) for r in rows]


@router.get("/{email_id}", response_model=EmailDraftResponse)
def get_email(
    email_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(EmailDraft, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email draft not found")
    return EmailDraftResponse.model_validate(row)


@router.put("/{email_id}", response_model=EmailDraftResponse)
def edit_email(
    email_id: int,
    body: EmailDraftUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(EmailDraft, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email draft not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.status = "edited"
    db.commit()
    db.refresh(row)
    return EmailDraftResponse.model_validate(row)


@router.post("/{email_id}/approve", response_model=EmailDraftResponse)
def approve_email(
    email_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(EmailDraft, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email draft not found")
    row.status = "approved"
    db.commit()
    db.refresh(row)
    return EmailDraftResponse.model_validate(row)


@router.post("/{email_id}/sent", response_model=EmailDraftResponse)
def mark_sent(
    email_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(EmailDraft, email_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Email draft not found")
    row.status = "sent"
    row.sent_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return EmailDraftResponse.model_validate(row)
