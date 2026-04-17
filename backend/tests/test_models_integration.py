"""Real-Postgres integration tests for model JSONB / ARRAY / TIMESTAMPTZ columns.

These complement tests/test_models.py (import-only smoke) by exercising the
PG-specific types that SQLite cannot represent.
"""
from datetime import UTC, datetime

import pytest

pytestmark = pytest.mark.integration


def test_scraped_job_roundtrips_jsonb_and_array(pg_session):
    from app.models.job import ScrapedJob

    job = ScrapedJob(
        source="remoteok",
        title="Senior AI Engineer",
        company_name="Acme",
        tech_stack=["python", "fastapi", "claude"],
        match_keywords=["llm", "orchestration"],
        score_reasons={"skill_match": 85, "variant": "vibe_coding"},
        content_hash="abc123",
    )
    pg_session.add(job)
    pg_session.commit()

    fetched = pg_session.query(ScrapedJob).filter_by(content_hash="abc123").one()
    assert fetched.tech_stack == ["python", "fastapi", "claude"]
    assert fetched.match_keywords == ["llm", "orchestration"]
    assert fetched.score_reasons["skill_match"] == 85


def test_agent_job_progress_log_defaults_to_empty_jsonb_array(pg_session):
    from app.models.agent_job import AgentJob

    j = AgentJob(job_type="job_score")
    pg_session.add(j)
    pg_session.commit()
    pg_session.refresh(j)
    assert j.progress_log == []


def test_timestamps_are_timezone_aware(pg_session):
    from app.models.user import User

    u = User(email="tz@test.com", password_hash="x")
    pg_session.add(u)
    pg_session.commit()
    pg_session.refresh(u)
    assert u.created_at.tzinfo is not None
    # Sanity: value is close to "now" in UTC terms.
    delta = datetime.now(UTC) - u.created_at
    assert abs(delta.total_seconds()) < 60
