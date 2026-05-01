"""Applications tracker — CRUD + Kanban + stats."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.application import Application, ApplicationActivity
from app.models.job import ScrapedJob
from app.models.user import User
from app.schemas.application import (
    KANBAN_STATUSES,
    ActivityTimeline,
    ActivityTimelineDay,
    ApplicationActivityResponse,
    ApplicationCreate,
    ApplicationDetail,
    ApplicationResponse,
    ApplicationStats,
    ApplicationUpdate,
    EasyApplyRequest,
    EasyApplyResponse,
    KanbanBoard,
)
from app.services.application_service import log_activity, transition_status
from app.services.cv_generator import generate_cv
from app.services.email_generator import generate_emails

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


@router.get("/activity-timeline", response_model=ActivityTimeline)
def activity_timeline(
    days: int = Query(14, ge=1, le=90),
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """Per-day count of application_activities rows over the last N days.

    Empty days are returned with count=0 so the chart never has gaps.
    """
    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=days)

    rows = (
        db.query(
            sa_func.date_trunc("day", ApplicationActivity.created_at).label("day"),
            sa_func.count().label("count"),
        )
        .filter(ApplicationActivity.created_at >= start)
        .filter(ApplicationActivity.created_at < end)
        .group_by("day")
        .all()
    )
    by_day: dict[str, int] = {}
    for day, count in rows:
        # day is timezone-aware (TIMESTAMPTZ); normalise to UTC date string.
        if hasattr(day, "astimezone"):
            day = day.astimezone(UTC)
        by_day[day.date().isoformat()] = int(count)

    out: list[ActivityTimelineDay] = []
    for offset in range(days):
        day_dt = start + timedelta(days=offset)
        key = day_dt.date().isoformat()
        out.append(ActivityTimelineDay(date=key, count=by_day.get(key, 0)))
    return ActivityTimeline(days=out)


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


@router.post(
    "/easy-apply",
    response_model=EasyApplyResponse,
    status_code=status.HTTP_201_CREATED,
)
def easy_apply(
    body: EasyApplyRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """LinkedIn-style Easy Apply — orchestrates the full first-touch flow.

    Idempotent per `job_id`: returns the existing Application if one already
    exists, otherwise creates a fresh `targeting` row + activity entry. Always
    spawns a NEW pair of Claude CLI subprocesses (cv-tailor + cold-email) so
    the user can re-run generation without re-creating the application.
    """
    job = db.get(ScrapedJob, body.job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    application = db.execute(
        select(Application).where(Application.job_id == job.id)
    ).scalar_one_or_none()

    if application is None:
        application = Application(
            job_id=job.id,
            company_id=job.company_id,
            status="targeting",
            targeted_at=datetime.now(UTC),
        )
        db.add(application)
        db.flush()
        log_activity(
            db,
            application_id=application.id,
            activity_type="created",
            description=f"Easy Apply: {job.title}",
        )
        db.commit()
        db.refresh(application)

    generated_cv, cv_aj_id = generate_cv(db, application.id)
    email_aj_id = generate_emails(db, application.id)

    db.commit()
    return EasyApplyResponse(
        application_id=application.id,
        cv_agent_job_id=cv_aj_id,
        email_agent_job_id=email_aj_id,
        generated_cv_id=generated_cv.id,
    )


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
