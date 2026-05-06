"""Portfolio assets CRUD + hybrid audit trigger + URL import."""
import logging
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.portfolio_asset import PortfolioAsset
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioAssetCreate,
    PortfolioAssetResponse,
    PortfolioAssetUpdate,
    PortfolioAuditResult,
    PortfolioAuditRun,
)
from app.services.portfolio_auditor import scan
from app.services.portfolio_cv_api import (
    PortfolioCVApiError,
    fetch_portfolio_projects,
    host_supports_api,
)
from app.services.portfolio_extractor import (
    PortfolioExtractError,
    extract_portfolio_from_url,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


_VARIANT_VALUES = {"vibe_coding", "ai_automation", "ai_video"}


class PortfolioImportUrlRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2000)


class PortfolioImportUrlResponse(BaseModel):
    count: int
    items: list[PortfolioAssetResponse]
    skipped: int = 0
    skipped_reasons: list[str] = Field(default_factory=list)
    status: Literal["ok", "partial"] = "ok"


def _default_scan_paths() -> list[str]:
    return [p.strip() for p in settings.PORTFOLIO_SCAN_PATHS.split(",") if p.strip()]


@router.get("", response_model=list[PortfolioAssetResponse])
def list_assets(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    q = db.query(PortfolioAsset)
    if status_filter:
        q = q.filter(PortfolioAsset.status == status_filter)
    q = q.order_by(PortfolioAsset.display_priority.desc(), PortfolioAsset.id.asc())
    return [PortfolioAssetResponse.model_validate(a) for a in q.all()]


@router.post("", response_model=PortfolioAssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    body: PortfolioAssetCreate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = PortfolioAsset(
        **body.model_dump(),
        status="published",  # manually-added assets skip the review queue
        auto_generated=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return PortfolioAssetResponse.model_validate(row)


@router.patch("/{asset_id}", response_model=PortfolioAssetResponse)
def update_asset(
    asset_id: int,
    body: PortfolioAssetUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(PortfolioAsset, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return PortfolioAssetResponse.model_validate(row)


@router.post("/{asset_id}/publish", response_model=PortfolioAssetResponse)
def publish_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.get(PortfolioAsset, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    row.status = "published"
    row.reviewed_at = datetime.now(UTC)
    row.reviewed_by = current.id
    db.commit()
    db.refresh(row)
    return PortfolioAssetResponse.model_validate(row)


@router.post("/{asset_id}/skip", response_model=PortfolioAssetResponse)
def skip_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.get(PortfolioAsset, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    row.status = "skipped"
    row.reviewed_at = datetime.now(UTC)
    row.reviewed_by = current.id
    db.commit()
    db.refresh(row)
    return PortfolioAssetResponse.model_validate(row)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(PortfolioAsset, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    db.delete(row)
    db.commit()


@router.post("/audit", response_model=PortfolioAuditResult)
def audit(
    body: PortfolioAuditRun | None = None,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    paths = (body.scan_paths if body and body.scan_paths else None) or _default_scan_paths()
    return scan(db, paths)


@router.post("/import-url", response_model=PortfolioImportUrlResponse)
def import_from_url(
    body: PortfolioImportUrlRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """Import portfolio entries from a URL → bulk-insert as draft assets.

    Path priority (fast -> slow), parallel to the CV import-url flow:

    1. **JSON fast-path** — host on a Portfolio CV API endpoint
       (alisadikinma.com) AND PORTFOLIO_CV_TOKEN set. Pulls
       /api/cv/export, maps `projects[]` directly into asset rows.
       ~1s, deterministic, NO LLM. Skips items whose URL already
       exists in `portfolio_assets` (so re-running the import doesn't
       balloon the drafts queue).

    2. **Firecrawl + LLM** — anywhere else. Scrapes the page,
       extracts projects via Claude CLI. ~20-40s, idempotent against
       the same source markdown. No URL dedup (titles can repeat
       across imports of different sites).

    Imported items get auto_generated=True, status='draft' so the
    operator reviews them in the same flow as auto-scanned plugin /
    project entries.
    """
    api_eligible = host_supports_api(body.url)

    if api_eligible:
        try:
            items = fetch_portfolio_projects()
            via_api = True
        except PortfolioCVApiError as e:
            log.info(
                "Portfolio CV API import failed (%s) — falling back to "
                "Firecrawl+LLM extractor",
                e,
            )
            via_api = False

    if not api_eligible or not via_api:
        try:
            items = extract_portfolio_from_url(db, body.url)
            via_api = False
        except PortfolioExtractError as e:
            # 502 because the upstream (Firecrawl/Anthropic) is the failure source.
            raise HTTPException(status_code=502, detail=str(e)) from e

    # URL dedup is only safe on the API path — Firecrawl item URLs are
    # often null or non-canonical, so we'd silently swallow legitimate
    # repeat imports there. Build the set lazily to avoid a query when
    # not needed.
    existing_urls: set[str] = set()
    if via_api:
        existing_urls = {
            row.url
            for row in db.query(PortfolioAsset.url)
            .filter(PortfolioAsset.url.isnot(None))
            .all()
        }

    created: list[PortfolioAsset] = []
    skipped_reasons: list[str] = []

    for raw in items:
        if not isinstance(raw, dict):
            skipped_reasons.append("non-dict item")
            continue

        title = (raw.get("title") or "").strip()
        if not title:
            skipped_reasons.append("missing title")
            continue

        description = (raw.get("description") or "").strip() or None
        url_field = raw.get("url") or None

        if via_api and url_field and url_field in existing_urls:
            skipped_reasons.append(f"duplicate URL: {url_field}")
            continue

        tech_stack_raw = raw.get("tech_stack") or []
        relevance_raw = raw.get("relevance_hint") or []
        tags_raw = raw.get("tags") or []
        source = raw.get("_source")

        tech_stack = [str(t).strip() for t in tech_stack_raw if str(t).strip()]
        tags = [str(t).strip() for t in tags_raw if str(t).strip()]
        relevance_hint = [
            str(v).strip() for v in relevance_raw if str(v).strip() in _VARIANT_VALUES
        ]

        # API path provides project-level metrics + featured flag; the
        # Firecrawl path doesn't, so its metrics is just the source label.
        if via_api:
            api_metrics = raw.get("metrics") if isinstance(raw.get("metrics"), dict) else None
            metrics: dict | None = {**(api_metrics or {}), "source": source} if (api_metrics or source) else None
            is_featured = bool(raw.get("is_featured", False))
            display_priority = 80 if is_featured else 50
        else:
            metrics = {"source": source} if source else None
            is_featured = False
            display_priority = 50

        row = PortfolioAsset(
            asset_type="external",
            title=title[:255],
            description=description,
            url=url_field,
            tech_stack=tech_stack or None,
            tags=tags or None,
            relevance_hint=relevance_hint or None,
            metrics=metrics,
            is_featured=is_featured,
            status="draft",
            auto_generated=True,
            display_priority=display_priority,
        )
        db.add(row)
        if url_field:
            existing_urls.add(url_field)  # avoid in-batch duplicates too
        created.append(row)

    db.commit()
    for row in created:
        db.refresh(row)

    return PortfolioImportUrlResponse(
        count=len(created),
        items=[PortfolioAssetResponse.model_validate(r) for r in created],
        skipped=len(skipped_reasons),
        skipped_reasons=skipped_reasons,
        status="partial" if skipped_reasons else "ok",
    )
