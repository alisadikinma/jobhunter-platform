"""Application state transitions + activity log helpers."""
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.application import Application, ApplicationActivity

# Status → timestamp column on Application (if any). Setting a column here
# lets us drive funnel analytics without writing a state machine first.
_STATUS_TIMESTAMPS = {
    "applied": "applied_at",
    "email_sent": "email_sent_at",
    "replied": "replied_at",
    "interview_scheduled": "interview_at",
    "offered": "offered_at",
    "accepted": "closed_at",
    "rejected": "closed_at",
    "ghosted": "closed_at",
}


def log_activity(
    db: Session,
    *,
    application_id: int,
    activity_type: str,
    description: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata: dict | None = None,
) -> ApplicationActivity:
    entry = ApplicationActivity(
        application_id=application_id,
        activity_type=activity_type,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata_=metadata,
    )
    db.add(entry)
    db.flush()
    return entry


def transition_status(
    db: Session,
    application: Application,
    new_status: str,
) -> ApplicationActivity | None:
    """Move the application to `new_status`, updating the matching timestamp
    column and appending an activity entry. Returns None if already at that
    status (idempotent)."""
    old_status = application.status
    if old_status == new_status:
        return None

    application.status = new_status
    ts_column = _STATUS_TIMESTAMPS.get(new_status)
    if ts_column is not None:
        setattr(application, ts_column, datetime.now(UTC))

    return log_activity(
        db,
        application_id=application.id,
        activity_type="status_change",
        old_value=old_status,
        new_value=new_status,
        description=f"{old_status} → {new_status}",
    )
