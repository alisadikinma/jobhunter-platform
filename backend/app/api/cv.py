"""Master CV + generated CV endpoints.

Phase 8: master CV CRUD (this file).
Phase 10: generated CV / tailor endpoints extend this router.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.cv import MasterCV
from app.models.user import User
from app.schemas.cv import MasterCVResponse, MasterCVUpdateRequest

router = APIRouter(prefix="/api/cv", tags=["cv"])


def _active_master(db: Session) -> MasterCV | None:
    stmt = (
        select(MasterCV)
        .where(MasterCV.is_active.is_(True))
        .order_by(MasterCV.version.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


@router.get("/master", response_model=MasterCVResponse)
def get_master(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    active = _active_master(db)
    if active is None:
        raise HTTPException(status_code=404, detail="No master CV yet — seed one first")
    return MasterCVResponse(
        id=active.id,
        version=active.version,
        is_active=active.is_active,
        content=active.content,  # pydantic re-validates here
        source_type=active.source_type,
    )


@router.put("/master", response_model=MasterCVResponse)
def update_master(
    body: MasterCVUpdateRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    current = _active_master(db)
    next_version = (current.version + 1) if current else 1
    if current is not None:
        current.is_active = False

    new_row = MasterCV(
        version=next_version,
        content=body.content.model_dump(mode="json"),
        raw_markdown=body.raw_markdown,
        is_active=True,
        source_type="manual",
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return MasterCVResponse(
        id=new_row.id,
        version=new_row.version,
        is_active=new_row.is_active,
        content=new_row.content,
        source_type=new_row.source_type,
    )
