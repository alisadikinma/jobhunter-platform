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
from app.models.application import Application
from app.models.company import Company
from app.models.cv import GeneratedCV, MasterCV
from app.models.email_draft import EmailDraft
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
    if job_type == "cv_tailor":
        return _apply_cv_tailor(db, agent_job, result)
    if job_type == "cold_email":
        return _apply_cold_email(db, agent_job, result)
    return job_type


def _apply_cold_email(db: Session, agent_job: AgentJob, result: dict) -> str:
    from app.services import mailer_service

    app_id = agent_job.reference_id
    if app_id is None:
        return "cold_email:no_reference"

    strategy = result.get("strategy")
    personalization = {"notes": result.get("personalization_notes") or []}

    application = db.get(Application, app_id) if app_id else None
    contact_email = application.contact_email if application else None
    contact_name = application.contact_name if application else None

    upserted = 0
    initial_draft_record: dict[str, str] | None = None

    for email_type in ("initial", "follow_up_1", "follow_up_2"):
        payload = result.get(email_type)
        if not isinstance(payload, dict):
            continue
        subject = payload.get("subject") or ""
        body = payload.get("body") or ""
        if not body:
            continue

        existing = (
            db.query(EmailDraft)
            .filter(
                EmailDraft.application_id == app_id,
                EmailDraft.email_type == email_type,
            )
            .one_or_none()
        )
        if existing is None:
            row = EmailDraft(
                application_id=app_id,
                email_type=email_type,
                subject=subject,
                body=body,
                strategy=strategy,
                personalization=personalization,
                status="draft",
            )
            db.add(row)
        else:
            existing.subject = subject
            existing.body = body
            existing.strategy = strategy
            existing.personalization = personalization
            existing.status = "draft"
            row = existing
        upserted += 1

        # Push the *initial* email into the IMAP Drafts folder so the user
        # can review + send from their mail client. Follow-ups stay
        # DB-only — they're scheduled, not human-reviewed at this step.
        if email_type == "initial" and contact_email:
            try:
                ack = mailer_service.append_draft(
                    mailer_service.MailMessage(
                        to_email=contact_email,
                        to_name=contact_name,
                        subject=subject,
                        body_text=body,
                    ),
                    db=db,
                )
                row.imap_uid = ack.get("uid") or None
                row.imap_message_id = ack.get("message_id") or None
                row.imap_folder = ack.get("folder") or None
                initial_draft_record = ack
            except mailer_service.MailerDisabled:
                log.info("mailer disabled — skipping IMAP draft append for app=%s", app_id)
            except mailer_service.MailerError as e:
                log.warning("IMAP draft append failed for app=%s: %s", app_id, e)

    suffix = ""
    if initial_draft_record:
        suffix = f" imap_uid={initial_draft_record.get('uid')}"
    return f"cold_email:{upserted}{suffix}"


def _apply_cv_tailor(db: Session, agent_job: AgentJob, result: dict) -> str:
    app_id = agent_job.reference_id
    if app_id is None:
        return "cv_tailor:no_reference"

    row = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.application_id == app_id)
        .order_by(GeneratedCV.id.desc())
        .first()
    )
    if row is None:
        log.warning("cv_tailor complete callback for app_id=%s with no generated_cvs row", app_id)
        return "cv_tailor:orphan"

    variant = result.get("variant_used")
    if variant == "no_match":
        row.status = "no_match"
        row.variant_used = variant
        row.suggestions = {"rejected_reason": result.get("rejected_keywords_reason")}
        return "cv_tailor:no_match"

    row.tailored_markdown = result.get("tailored_markdown") or ""
    row.tailored_json = result.get("tailored_json") or {}
    row.variant_used = variant
    confidence = result.get("confidence")
    if isinstance(confidence, int | float):
        row.confidence = int(float(confidence) * 100) if confidence <= 1 else int(confidence)
    row.keyword_matches = list(result.get("keyword_matches") or [])
    row.missing_keywords = list(result.get("missing_keywords") or [])
    row.suggestions = {
        "selected_portfolio_ids": result.get("selected_portfolio_ids"),
    }
    row.status = "ready"
    return f"cv_tailor:ready ({variant})"


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
        return _cv_tailor_context(db, agent_job.reference_id)

    if job_type == "cold_email":
        return _cold_email_context(db, agent_job.reference_id)

    return {}


def _cold_email_context(db: Session, application_id: int | None) -> dict:
    if application_id is None:
        return {"application_id": None, "error": "agent_job.reference_id is null"}

    application = db.get(Application, application_id)
    if application is None:
        return {"application_id": application_id, "error": "application not found"}

    job = db.get(ScrapedJob, application.job_id) if application.job_id else None
    company = db.get(Company, application.company_id) if application.company_id else None
    # Derive variant from the associated generated_cv, fall back to the
    # scraped_job's suggested_variant.
    variant_used: str | None = None
    gen_cv = (
        db.query(GeneratedCV)
        .filter(GeneratedCV.application_id == application_id)
        .order_by(GeneratedCV.id.desc())
        .first()
    )
    if gen_cv and gen_cv.variant_used and gen_cv.variant_used != "no_match":
        variant_used = gen_cv.variant_used
    elif job and job.suggested_variant:
        variant_used = job.suggested_variant

    master = _active_master_cv(db)
    master_summary = (master.content or {}).get("basics", {}) if master else None

    return {
        "application_id": application_id,
        "job": _job_as_context(job) if job else None,
        "company": _company_as_context(company) if company else None,
        "master_cv_summary": master_summary,
        "variant_used": variant_used,
    }


def _cv_tailor_context(db: Session, application_id: int | None) -> dict:
    if application_id is None:
        return {"application_id": None, "error": "agent_job.reference_id is null"}

    application = db.get(Application, application_id)
    if application is None:
        return {"application_id": application_id, "error": "application not found"}

    job = db.get(ScrapedJob, application.job_id) if application.job_id else None
    company = db.get(Company, application.company_id) if application.company_id else None

    return {
        "application_id": application_id,
        "master_cv": _master_cv_content(db),
        "job": _job_as_context(job) if job else None,
        "company": _company_as_context(company) if company else None,
        "portfolio_assets": _published_portfolio(db),
    }


def _company_as_context(company: Company) -> dict:
    meta: dict = dict(company.metadata_ or {})
    return {
        "id": company.id,
        "name": company.name,
        "domain": company.domain,
        "industry": company.industry,
        "description": company.description,
        "enriched_context": meta.get("enriched_context"),
    }


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
