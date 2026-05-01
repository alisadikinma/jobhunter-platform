"""Master CV + generated CV endpoints.

Phase 8: master CV CRUD (this file).
Phase 10: generated CV / tailor endpoints extend this router.
"""
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.application import Application
from app.models.cv import GeneratedCV, MasterCV
from app.models.job import ScrapedJob
from app.models.user import User
from app.schemas.cv import (
    CVGenerateEnqueued,
    CVGenerateRequest,
    GeneratedCVResponse,
    GeneratedCVUpdate,
    MasterCVContent,
    MasterCVImportURLRequest,
    MasterCVResponse,
    MasterCVUpdateRequest,
)
from app.services.cv_generator import CVGenerationError, generate_cv
from app.services.cv_parser import (
    CVParseError,
    extract_text_from_upload,
    is_supported_upload,
    parse_cv_to_json_resume,
)
from app.services.docx_service import ConversionError, docx_to_pdf, markdown_to_docx
from app.services.firecrawl_service import FirecrawlService
from app.services.scorer_service import score_cv

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


def _save_new_master(
    db: Session, content_dict: dict, *, source_type: str, raw_markdown: str | None = None
) -> MasterCV:
    """Validate + persist a new master_cv row, deactivating any current active row."""
    try:
        validated = MasterCVContent.model_validate(content_dict)
    except ValidationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Parsed content does not match Master CV schema: {e.errors()}",
        ) from e

    current = _active_master(db)
    next_version = (current.version + 1) if current else 1
    if current is not None:
        current.is_active = False

    new_row = MasterCV(
        version=next_version,
        content=validated.model_dump(mode="json"),
        raw_markdown=raw_markdown,
        is_active=True,
        source_type=source_type,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row


@router.post(
    "/master/upload",
    response_model=MasterCVResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_master(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """Accept a PDF/DOCX/MD/TXT upload, extract text, run LLM parse, save as new active version."""
    filename = file.filename or ""
    mime_type = file.content_type or ""
    if not is_supported_upload(mime_type, filename):
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type: {mime_type or 'unknown'} ({filename}). "
                "Allowed: .pdf, .docx, .md, .txt"
            ),
        )

    file_bytes = file.file.read()
    if not file_bytes:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    try:
        raw_text = extract_text_from_upload(file_bytes, mime_type, filename)
    except CVParseError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No text extracted from upload — file may be image-only or corrupted",
        )

    try:
        parsed = parse_cv_to_json_resume(raw_text)
    except CVParseError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    new_row = _save_new_master(db, parsed, source_type="upload", raw_markdown=raw_text)
    return MasterCVResponse(
        id=new_row.id,
        version=new_row.version,
        is_active=new_row.is_active,
        content=new_row.content,
        source_type=new_row.source_type,
    )


@router.post(
    "/master/import-url",
    response_model=MasterCVResponse,
    status_code=status.HTTP_201_CREATED,
)
def import_master_from_url(
    body: MasterCVImportURLRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    """Scrape a portfolio URL via Firecrawl, parse to JSON Resume, save as new active version."""
    parsed_url = urlparse(body.url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(status_code=422, detail="URL must be an absolute http(s) URL")

    try:
        with FirecrawlService(db=db) as fc:
            # waitFor lets JS-rendered SPAs (Next/Nuxt/React) finish hydrating
            # before Firecrawl reads the DOM. 5s is enough for most sites.
            result = fc.scrape(body.url, opts={"waitFor": 5000})
    except Exception as e:  # network/pool failure — surface as 502
        raise HTTPException(
            status_code=502,
            detail=(
                f"Firecrawl scrape failed: {e}. "
                "Tip: try the 'Upload file' option instead — it parses your "
                "CV directly without needing Firecrawl."
            ),
        ) from e

    markdown = (result or {}).get("markdown") or ""
    if not markdown.strip():
        err = (result or {}).get("error") or "empty response"
        raise HTTPException(
            status_code=502,
            detail=(
                f"Firecrawl returned no content for {body.url}: {err}. "
                "Tip: try uploading your CV as PDF/DOCX directly instead — "
                "the 'Upload file' button parses local files without "
                "depending on Firecrawl SaaS."
            ),
        )

    try:
        parsed = parse_cv_to_json_resume(markdown)
    except CVParseError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    domain = parsed_url.netloc.lower()
    new_row = _save_new_master(
        db, parsed, source_type=f"url:{domain}", raw_markdown=markdown
    )
    return MasterCVResponse(
        id=new_row.id,
        version=new_row.version,
        is_active=new_row.is_active,
        content=new_row.content,
        source_type=new_row.source_type,
    )


# --- generated CV endpoints (Phase 10) ----------------------------

@router.post("/generate", response_model=CVGenerateEnqueued, status_code=status.HTTP_202_ACCEPTED)
def generate(
    body: CVGenerateRequest,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    try:
        row, agent_job_id = generate_cv(db, body.application_id)
    except CVGenerationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return CVGenerateEnqueued(
        generated_cv_id=row.id,
        agent_job_id=agent_job_id,
        status=row.status,
    )


@router.get("/{cv_id}", response_model=GeneratedCVResponse)
def get_generated(
    cv_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(GeneratedCV, cv_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated CV not found")
    return GeneratedCVResponse.model_validate(row)


@router.put("/{cv_id}", response_model=GeneratedCVResponse)
def edit_generated(
    cv_id: int,
    body: GeneratedCVUpdate,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(GeneratedCV, cv_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated CV not found")
    if body.tailored_markdown is not None:
        row.tailored_markdown = body.tailored_markdown
        row.status = "edited"
        # Invalidate any rendered artifacts — they're now stale.
        row.docx_path = None
        row.pdf_path = None
    db.commit()
    db.refresh(row)
    return GeneratedCVResponse.model_validate(row)


# --- Phase 11: score + render + download -------------------------

def _jd_for(cv: GeneratedCV, db: Session) -> str:
    """Fetch JD text for ATS scoring — either from the linked scraped job or
    (fallback) from the application's job."""
    if cv.job_id:
        job = db.get(ScrapedJob, cv.job_id)
        if job and job.description:
            return job.description
    if cv.application_id:
        appl = db.get(Application, cv.application_id)
        if appl and appl.job_id:
            job = db.get(ScrapedJob, appl.job_id)
            if job and job.description:
                return job.description
    return ""


@router.post("/{cv_id}/score", response_model=GeneratedCVResponse)
def rescore_cv(
    cv_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(GeneratedCV, cv_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated CV not found")
    if not row.tailored_markdown:
        raise HTTPException(status_code=409, detail="CV has no content to score")

    jd = _jd_for(row, db)
    breakdown = score_cv(row.tailored_markdown, jd)
    row.ats_score = breakdown.score
    row.keyword_matches = list(breakdown.keyword_matches)
    row.missing_keywords = list(breakdown.missing_keywords)
    row.suggestions = {
        **(row.suggestions or {}),
        "ats": breakdown.suggestions,
    }
    db.commit()
    db.refresh(row)
    return GeneratedCVResponse.model_validate(row)


def _render_artifacts(cv: GeneratedCV) -> tuple[Path, Path]:
    storage = Path(settings.CV_STORAGE_DIR).resolve()
    storage.mkdir(parents=True, exist_ok=True)

    if not cv.tailored_markdown:
        raise ConversionError("CV has no markdown content yet")

    docx_path = storage / f"cv-{cv.id}.docx"
    pdf_path = storage / f"cv-{cv.id}.pdf"

    ref = Path(settings.CV_REFERENCE_DOCX) if settings.CV_REFERENCE_DOCX else None
    markdown_to_docx(cv.tailored_markdown, docx_path, reference_docx=ref)
    docx_to_pdf(docx_path, pdf_path)
    return docx_path, pdf_path


@router.get("/{cv_id}/download/{fmt}")
def download_cv(
    cv_id: int,
    fmt: str,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    if fmt not in {"docx", "pdf"}:
        raise HTTPException(status_code=422, detail="fmt must be 'docx' or 'pdf'")
    row = db.get(GeneratedCV, cv_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated CV not found")

    current = Path(row.docx_path) if fmt == "docx" and row.docx_path else None
    if fmt == "pdf" and row.pdf_path:
        current = Path(row.pdf_path)

    if current is None or not current.exists():
        try:
            docx_path, pdf_path = _render_artifacts(row)
        except ConversionError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        row.docx_path = str(docx_path)
        row.pdf_path = str(pdf_path)
        db.commit()
        current = docx_path if fmt == "docx" else pdf_path

    media_type = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if fmt == "docx"
        else "application/pdf"
    )
    return FileResponse(
        path=str(current),
        media_type=media_type,
        filename=f"cv-{cv_id}.{fmt}",
    )


@router.get("/{cv_id}/preview")
def preview_cv(
    cv_id: int,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    row = db.get(GeneratedCV, cv_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Generated CV not found")
    return {
        "markdown": row.tailored_markdown or "",
        "variant_used": row.variant_used,
        "ats_score": row.ats_score,
        "keyword_matches": list(row.keyword_matches or []),
        "missing_keywords": list(row.missing_keywords or []),
    }
