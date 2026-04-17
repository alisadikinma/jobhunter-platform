"""Scraper control + config CRUD."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.scrape_config import ScrapeConfig
from app.models.user import User
from app.schemas.scrape_config import (
    ScrapeConfigCreate,
    ScrapeConfigResponse,
    ScrapeConfigUpdate,
    ScrapeRunRequest,
    ScrapeRunResponse,
)
from app.services.claude_service import spawn_claude
from app.services.scraper_service import run_ad_hoc, run_scrape_config

router = APIRouter(prefix="/api/scraper", tags=["scraper"])


# ---- configs CRUD ---------------------------------------------------

@router.get("/configs", response_model=list[ScrapeConfigResponse])
def list_configs(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    configs = db.query(ScrapeConfig).order_by(ScrapeConfig.id.asc()).all()
    return [ScrapeConfigResponse.model_validate(c) for c in configs]


@router.post("/configs", response_model=ScrapeConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(
    body: ScrapeConfigCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    config = ScrapeConfig(**body.model_dump())
    db.add(config)
    db.commit()
    db.refresh(config)
    return ScrapeConfigResponse.model_validate(config)


@router.put("/configs/{config_id}", response_model=ScrapeConfigResponse)
def update_config(
    config_id: int,
    body: ScrapeConfigUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    config = db.get(ScrapeConfig, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)
    db.commit()
    db.refresh(config)
    return ScrapeConfigResponse.model_validate(config)


@router.delete("/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    config = db.get(ScrapeConfig, config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="Config not found")
    db.delete(config)
    db.commit()


# ---- runs -----------------------------------------------------------

@router.post("/run", response_model=ScrapeRunResponse)
def run_scraper(
    body: ScrapeRunRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    if body.config_id is not None:
        config = db.get(ScrapeConfig, body.config_id)
        if config is None:
            raise HTTPException(status_code=404, detail="Config not found")
        if not config.is_active:
            raise HTTPException(status_code=409, detail="Config is inactive")
        return run_scrape_config(db, config)

    if not body.keywords or not body.sources:
        raise HTTPException(
            status_code=422,
            detail="Either config_id or (keywords + sources) must be provided",
        )
    return run_ad_hoc(
        db,
        keywords=body.keywords,
        sources=body.sources,
        locations=body.locations,
        variant_target=body.variant_target,
        max_results_per_source=body.max_results_per_source,
    )


@router.post("/score-unscored", status_code=202)
def score_unscored(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """Fire a /job-score skill against the batch of currently-unscored jobs.

    Returns the agent_job id so the caller can poll progress. The actual
    scoring happens in a Claude CLI subprocess; see claude-plugin/skills/
    job-score.md for the contract.
    """
    agent_job = spawn_claude(
        db,
        skill_name="/job-score",
        reference_id=None,
        reference_type="scraped_jobs_batch",
        job_type="job_score",
        model_used="claude-sonnet-4-6",
    )
    return {"agent_job_id": agent_job.id, "status": agent_job.status}


@router.get("/status")
def status_endpoint(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    configs = db.query(ScrapeConfig).all()
    return {
        "configs": [
            {
                "id": c.id,
                "name": c.name,
                "is_active": c.is_active,
                "cron_expression": c.cron_expression,
                "last_run_at": c.last_run_at,
                "last_run_results": c.last_run_results,
            }
            for c in configs
        ]
    }
