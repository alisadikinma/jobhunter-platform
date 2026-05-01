"""Scraped jobs browsing API."""
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.job import ScrapedJob
from app.models.user import User
from app.schemas.job import (
    JobListResponse,
    JobResponse,
    JobSortField,
    JobSortOrder,
    JobStats,
    JobUpdate,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(
    status: str | None = None,
    source: str | None = None,
    variant: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    is_favorite: bool | None = None,
    include_irrelevant: bool = Query(False),
    search: str | None = None,
    sort: JobSortField = "relevance_score",
    order: JobSortOrder = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    stmt = select(ScrapedJob)
    if not include_irrelevant:
        stmt = stmt.where(ScrapedJob.user_irrelevant == False)  # noqa: E712
    if status:
        stmt = stmt.where(ScrapedJob.status == status)
    if source:
        stmt = stmt.where(ScrapedJob.source == source)
    if variant:
        stmt = stmt.where(ScrapedJob.suggested_variant == variant)
    if min_score is not None:
        stmt = stmt.where(ScrapedJob.relevance_score >= min_score)
    if is_favorite is not None:
        stmt = stmt.where(ScrapedJob.is_favorite == is_favorite)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (ScrapedJob.title.ilike(like)) | (ScrapedJob.company_name.ilike(like))
        )

    sort_col = getattr(ScrapedJob, sort)
    stmt = stmt.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()

    items = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=JobStats)
def job_stats(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    jobs = db.query(ScrapedJob).all()
    by_status = Counter(j.status or "unknown" for j in jobs)
    by_source = Counter(j.source for j in jobs)
    by_variant = Counter(j.suggested_variant or "unclassified" for j in jobs)
    high_score = sum(1 for j in jobs if (j.relevance_score or 0) >= 80)
    return JobStats(
        total=len(jobs),
        by_status=dict(by_status),
        by_source=dict(by_source),
        by_variant=dict(by_variant),
        high_score_count=high_score,
    )


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    job = db.get(ScrapedJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.patch("/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    body: JobUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    job = db.get(ScrapedJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=204)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    job = db.get(ScrapedJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()


@router.post("/{job_id}/favorite", response_model=JobResponse)
def toggle_favorite(
    job_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    job = db.get(ScrapedJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job.is_favorite = not (job.is_favorite or False)
    db.commit()
    db.refresh(job)
    return JobResponse.model_validate(job)
