"""Enrichment endpoints — hydrate scraped_jobs + companies via Firecrawl."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.company import Company
from app.models.job import ScrapedJob
from app.models.user import User
from app.schemas.firecrawl import CompanyResearchResponse, EnrichmentResponse
from app.services.firecrawl_service import FirecrawlService

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


def _get_firecrawl() -> FirecrawlService:
    return FirecrawlService()


@router.post("/job/{job_id}", response_model=EnrichmentResponse)
def enrich_job(
    job_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
    firecrawl: FirecrawlService = Depends(_get_firecrawl),
) -> EnrichmentResponse:
    job = db.get(ScrapedJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.source_url:
        raise HTTPException(status_code=422, detail="Job has no source_url to enrich from")

    length_before = len(job.description or "")

    with firecrawl:
        result = firecrawl.scrape(job.source_url)

    markdown = result.get("markdown") or ""
    if not markdown:
        return EnrichmentResponse(
            ok=False,
            source=job.description_source or "aggregator",
            length_before=length_before,
            length_after=length_before,
            message=result.get("error") or "empty response",
        )

    # Only overwrite if Firecrawl produced something longer than what we had.
    if len(markdown) > length_before:
        job.description = markdown
        job.description_source = "firecrawl_enriched"
        job.enriched_at = datetime.now(UTC)
        db.commit()
        length_after = len(markdown)
    else:
        length_after = length_before

    return EnrichmentResponse(
        ok=True,
        source=job.description_source or "aggregator",
        length_before=length_before,
        length_after=length_after,
    )


@router.post("/company/{company_id}", response_model=CompanyResearchResponse)
def enrich_company(
    company_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
    firecrawl: FirecrawlService = Depends(_get_firecrawl),
) -> CompanyResearchResponse:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.domain:
        raise HTTPException(status_code=422, detail="Company has no domain to research")

    target_url = company.domain
    if not target_url.startswith(("http://", "https://")):
        target_url = f"https://{target_url}"

    with firecrawl:
        result = firecrawl.scrape(target_url)

    markdown = result.get("markdown") or ""
    if not markdown:
        return CompanyResearchResponse(
            ok=False,
            domain=company.domain,
            title=None,
            markdown_chars=0,
            message=result.get("error") or "empty response",
        )

    # Merge into companies.metadata JSONB under 'enriched_context' key.
    current = dict(company.metadata_ or {})
    current["enriched_context"] = {
        "markdown": markdown,
        "title": result.get("title"),
        "description": result.get("description"),
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    company.metadata_ = current
    db.commit()

    return CompanyResearchResponse(
        ok=True,
        domain=company.domain,
        title=result.get("title"),
        markdown_chars=len(markdown),
    )
