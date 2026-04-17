"""Portfolio assets CRUD + hybrid audit trigger."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


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
