"""Applications tracker — CRUD + Kanban + stats."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.application import Application, ApplicationActivity
from app.models.job import ScrapedJob
from app.models.user import User
from app.schemas.application import (
    KANBAN_STATUSES,
    ApplicationActivityResponse,
    ApplicationCreate,
    ApplicationDetail,
    ApplicationResponse,
    ApplicationStats,
    ApplicationUpdate,
    KanbanBoard,
)
from app.services.application_service import log_activity, transition_status

router = APIRouter(prefix="/api/applications", tags=["applications"])


# ---------------------------------------------------------------- list + stats
# (defined before /{id} routes so Starlette path-matching treats /kanban,
# /stats as literal segments rather than ID fragments.)


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    stmt = select(Application).order_by(Application.created_at.desc())
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(stmt).scalars().all()
    return [ApplicationResponse.model_validate(r) for r in rows]


@router.get("/kanban", response_model=KanbanBoard)
def kanban(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    rows = (
        db.query(Application)
        .order_by(Application.created_at.desc())
        .all()
    )
    columns: dict[str, list[ApplicationResponse]] = {s: [] for s in KANBAN_STATUSES}
    for row in rows:
        key = row.status if row.status in columns else "targeting"
        columns[key].append(ApplicationResponse.model_validate(row))
    return KanbanBoard(columns=columns)


@router.get("/stats", response_model=ApplicationStats)
def stats(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    rows = db.query(Application).all()
    by_status: dict[str, int] = {s: 0 for s in KANBAN_STATUSES}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1

    email_sent = sum(
        1 for r in rows if r.email_sent_at is not None
    )
    replied = sum(1 for r in rows if r.replied_at is not None)
    applied_count = sum(1 for r in rows if r.applied_at is not None)
    offered = sum(1 for r in rows if r.offered_at is not None)

    response_rate = (replied / email_sent) if email_sent else 0.0
    offer_rate = (offered / applied_count) if applied_count else 0.0

    # Avg days between email_sent_at and replied_at (when both present).
    deltas = [
        (r.replied_at - r.email_sent_at).total_seconds() / 86400
        for r in rows
        if r.email_sent_at and r.replied_at
    ]
    avg_days = sum(deltas) / len(deltas) if deltas else None

    active_statuses = {"targeting", "cv_generating", "cv_ready", "applied",
                       "email_sent", "replied", "interview_scheduled", "interviewed"}
    pipeline_value = sum(
        (r.salary_asked or 0) for r in rows if r.status in active_statuses
    )

    return ApplicationStats(
        total=len(rows),
        by_status=by_status,
        response_rate=round(response_rate, 3),
        offer_rate=round(offer_rate, 3),
        avg_days_to_reply=round(avg_days, 2) if avg_days is not None else None,
        pipeline_value_usd=int(pipeline_value),
    )


# ---------------------------------------------------------------- CRUD


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    body: ApplicationCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    job = db.get(ScrapedJob, body.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    row = Application(
        job_id=job.id,
        company_id=job.company_id,
        status="targeting",
        targeted_at=datetime.now(UTC),
    )
    db.add(row)
    db.flush()
    log_activity(
        db,
        application_id=row.id,
        activity_type="created",
        description=f"Targeted from job #{job.id}: {job.title}",
    )
    db.commit()
    db.refresh(row)
    return ApplicationResponse.model_validate(row)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(Application, application_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    activities = (
        db.query(ApplicationActivity)
        .filter(ApplicationActivity.application_id == application_id)
        .order_by(ApplicationActivity.created_at.desc())
        .all()
    )
    return ApplicationDetail(
        **ApplicationResponse.model_validate(row).model_dump(),
        activities=[ApplicationActivityResponse.model_validate(a) for a in activities],
    )


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    body: ApplicationUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(Application, application_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")

    updates = body.model_dump(exclude_unset=True)
    new_status = updates.pop("status", None)

    for field, value in updates.items():
        setattr(row, field, value)

    if new_status is not None:
        transition_status(db, row, new_status)
    elif updates:
        log_activity(
            db,
            application_id=row.id,
            activity_type="edited",
            description=", ".join(updates.keys()),
        )

    db.commit()
    db.refresh(row)
    return ApplicationResponse.model_validate(row)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(Application, application_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Application not found")
    db.delete(row)
    db.commit()
