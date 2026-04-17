from pydantic import BaseModel, Field


class ProgressUpdate(BaseModel):
    progress_pct: int = Field(ge=0, le=100)
    current_step: str | None = None
    log_message: str | None = None


class CompletionResult(BaseModel):
    status: str = Field(pattern=r"^(completed|failed)$")
    result: dict = Field(default_factory=dict)
    error_message: str | None = None


# --- per-skill result shapes (validated in dispatch) ---

class JobScoreEntry(BaseModel):
    job_id: int
    relevance_score: int = Field(ge=0, le=100)
    suggested_variant: str | None = None
    score_reasons: dict | None = None
    match_keywords: list[str] | None = None


class ContextResponse(BaseModel):
    """Returned by GET /api/callbacks/context/{job_id} for skills to read."""

    job_type: str
    reference_id: int | None
    payload: dict
