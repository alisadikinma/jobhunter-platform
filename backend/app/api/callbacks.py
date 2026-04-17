"""Callbacks for Claude CLI subprocess.

Skills authenticate via the X-Callback-Secret header (shared secret, NOT
the user JWT) because subprocess has no user session. The secret comes
from CALLBACK_SECRET env.
"""
import logging
import secrets as _secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.agent_job import AgentJob
from app.models.cv import MasterCV
from app.models.job import ScrapedJob
from app.models.portfolio_asset import PortfolioAsset
from app.schemas.callbacks import (
    CompletionResult,
    ContextResponse,
    JobScoreEntry,
    ProgressUpdate,
)

log = logging.getLogger(__name__)


router = APIRouter(prefix="/api/callbacks", tags=["callbacks"])


def _verify_callback_secret(
    x_callback_secret: str = Header(..., alias="X-Callback-Secret"),
) -> None:
    expected = settings.CALLBACK_SECRET
    if not expected:
        raise HTTPException(status_code=503, detail="CALLBACK_SECRET is not configured")
    if not _secrets.compare_digest(x_callback_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid callback secret")


@router.put("/progress/{job_id}")
def update_progress(
    job_id: int,
    body: ProgressUpdate,
    _auth: None = Depends(_verify_callback_secret),
    db: Session = Depends(get_db),
):
    agent_job = db.get(AgentJob, job_id)
    if agent_job is None:
        raise HTTPException(status_code=404, detail="Agent job not found")

    agent_job.progress_pct = body.progress_pct
    if body.current_step is not None:
        agent_job.current_step = body.current_step
    if body.log_message:
        log_entries = list(agent_job.progress_log or [])
        log_entries.append({
            "t": datetime.now(UTC).isoformat(),
            "msg": body.log_message,
        })
        agent_job.progress_log = log_entries
    db.commit()
    return {"ok": True}


@router.put("/complete/{job_id}")
def complete_job(
    job_id: int,
    body: CompletionResult,
    _auth: None = Depends(_verify_callback_secret),
    db: Session = Depends(get_db),
):
    agent_job = db.get(AgentJob, job_id)
    if agent_job is None:
        raise HTTPException(status_code=404, detail="Agent job not found")

    agent_job.status = body.status
    agent_job.result = body.result
    agent_job.completed_at = datetime.now(UTC)
    if body.status == "failed":
        agent_job.error_message = body.error_message or "unspecified failure"
        db.commit()
        return {"ok": True, "dispatched": False}

    # Success: dispatch by job_type into domain tables.
    dispatched = _dispatch_success(db, agent_job, body.result)
    db.commit()
    return {"ok": True, "dispatched": dispatched}


@router.get("/context/{job_id}", response_model=ContextResponse)
def get_context(
    job_id: int,
    _auth: None = Depends(_verify_callback_secret),
    db: Session = Depends(get_db),
):
    agent_job = db.get(AgentJob, job_id)
    if agent_job is None:
        raise HTTPException(status_code=404, detail="Agent job not found")

    payload = _build_context_payload(db, agent_job)
    return ContextResponse(
        job_type=agent_job.job_type,
        reference_id=agent_job.reference_id,
        payload=payload,
    )


# --- dispatchers ---------------------------------------------------

def _dispatch_success(db: Session, agent_job: AgentJob, result: dict) -> str:
    job_type = agent_job.job_type
    if job_type == "job_score":
        return _apply_job_scores(db, result)
    # cv_tailor / cold_email wiring lands in Phase 10 / 13.
    return job_type


def _apply_job_scores(db: Session, result: dict) -> str:
    raw_entries = result.get("scores") or []
    count = 0
    for raw in raw_entries:
        try:
            entry = JobScoreEntry.model_validate(raw)
        except Exception as e:
            log.warning("invalid job score entry skipped: %s (raw=%r)", e, raw)
            continue
        job = db.get(ScrapedJob, entry.job_id)
        if job is None:
            continue
        job.relevance_score = entry.relevance_score
        job.suggested_variant = entry.suggested_variant or job.suggested_variant
        if entry.score_reasons is not None:
            job.score_reasons = entry.score_reasons
        if entry.match_keywords is not None:
            job.match_keywords = list(entry.match_keywords)
        job.status = "scored" if job.status in (None, "new") else job.status
        count += 1
    return f"job_score:{count}"


def _build_context_payload(db: Session, agent_job: AgentJob) -> dict:
    job_type = agent_job.job_type

    if job_type == "job_score":
        # reference_id is an arbitrary batch id (not a DB row); the batch_ids
        # are communicated via extra_args at spawn time and stored in
        # agent_job.result->requested_ids by convention. For a simpler contract:
        # the caller passes the list via a companion /context lookup on the
        # job_ids embedded in extra_args; we return recent unscored jobs when
        # no specific batch is recorded.
        jobs_q = (
            db.query(ScrapedJob)
            .filter(ScrapedJob.relevance_score.is_(None))
            .order_by(ScrapedJob.scraped_at.desc())
            .limit(25)
        )
        master = _active_master_cv(db)
        return {
            "jobs": [_job_as_context(j) for j in jobs_q.all()],
            "master_cv_summary": (master.content or {}).get("basics", {}) if master else None,
        }

    if job_type == "cv_tailor":
        app_id = agent_job.reference_id
        # Phase 10 populates this; stub now returns minimal context.
        return {
            "application_id": app_id,
            "master_cv": _master_cv_content(db),
            "portfolio_assets": _published_portfolio(db),
        }

    return {}


def _active_master_cv(db: Session) -> MasterCV | None:
    return (
        db.query(MasterCV)
        .filter(MasterCV.is_active.is_(True))
        .order_by(MasterCV.version.desc())
        .first()
    )


def _master_cv_content(db: Session) -> dict | None:
    master = _active_master_cv(db)
    return master.content if master else None


def _published_portfolio(db: Session) -> list[dict]:
    rows = (
        db.query(PortfolioAsset)
        .filter(PortfolioAsset.status == "published")
        .order_by(PortfolioAsset.display_priority.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "title": r.title,
            "url": r.url,
            "description": r.description,
            "tech_stack": list(r.tech_stack or []),
            "relevance_hint": list(r.relevance_hint or []),
        }
        for r in rows
    ]


def _job_as_context(job: ScrapedJob) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company_name,
        "location": job.location,
        "description": job.description or "",
        "tech_stack": list(job.tech_stack or []),
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "source": job.source,
    }
