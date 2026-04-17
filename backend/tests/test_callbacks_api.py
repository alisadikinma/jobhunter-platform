"""Callbacks API tests — shared-secret auth, progress updates, dispatch."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.agent_job import AgentJob
from app.models.job import ScrapedJob

pytestmark = pytest.mark.integration

_SECRET = "test-callback-secret"


@pytest.fixture
def api(pg_engine, monkeypatch):
    monkeypatch.setattr(settings, "CALLBACK_SECRET", _SECRET)
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)

    def _db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    try:
        yield TestClient(app), SessionLocal
    finally:
        app.dependency_overrides.clear()


def _mk_agent_job(SessionLocal, *, job_type="job_score", reference_id=None) -> int:
    with SessionLocal() as s:
        row = AgentJob(
            job_type=job_type, reference_id=reference_id,
            reference_type="batch", status="running", progress_pct=0,
        )
        s.add(row)
        s.commit()
        return row.id


def test_progress_requires_callback_secret(api):
    client, SL = api
    jid = _mk_agent_job(SL)
    # Missing header → 422 (Pydantic required header)
    assert client.put(f"/api/callbacks/progress/{jid}", json={"progress_pct": 50}).status_code == 422


def test_progress_rejects_wrong_secret(api):
    client, SL = api
    jid = _mk_agent_job(SL)
    r = client.put(
        f"/api/callbacks/progress/{jid}",
        json={"progress_pct": 50},
        headers={"X-Callback-Secret": "wrong"},
    )
    assert r.status_code == 401


def test_progress_updates_and_appends_log(api):
    client, SL = api
    jid = _mk_agent_job(SL)

    client.put(
        f"/api/callbacks/progress/{jid}",
        json={"progress_pct": 25, "current_step": "scoring batch 1", "log_message": "first pass"},
        headers={"X-Callback-Secret": _SECRET},
    )
    client.put(
        f"/api/callbacks/progress/{jid}",
        json={"progress_pct": 50, "current_step": "scoring batch 2", "log_message": "second pass"},
        headers={"X-Callback-Secret": _SECRET},
    )

    with SL() as s:
        row = s.get(AgentJob, jid)
        assert row.progress_pct == 50
        assert row.current_step == "scoring batch 2"
        assert len(row.progress_log) == 2
        assert row.progress_log[0]["msg"] == "first pass"


def test_complete_success_dispatches_job_scores(api):
    client, SL = api
    jid = _mk_agent_job(SL)

    with SL() as s:
        j1 = ScrapedJob(source="x", title="A", company_name="A", content_hash="hA")
        j2 = ScrapedJob(source="x", title="B", company_name="B", content_hash="hB")
        s.add_all([j1, j2])
        s.commit()
        j1_id, j2_id = j1.id, j2.id

    r = client.put(
        f"/api/callbacks/complete/{jid}",
        json={
            "status": "completed",
            "result": {
                "scores": [
                    {
                        "job_id": j1_id, "relevance_score": 85,
                        "suggested_variant": "vibe_coding",
                        "score_reasons": {"skill_match": 35},
                        "match_keywords": ["claude code", "fastapi"],
                    },
                    {
                        "job_id": j2_id, "relevance_score": 40,
                        "suggested_variant": None,
                    },
                ]
            },
        },
        headers={"X-Callback-Secret": _SECRET},
    )
    assert r.status_code == 200
    assert r.json()["dispatched"].startswith("job_score:2")

    with SL() as s:
        j1 = s.get(ScrapedJob, j1_id)
        j2 = s.get(ScrapedJob, j2_id)
        assert j1.relevance_score == 85
        assert j1.suggested_variant == "vibe_coding"
        assert j1.match_keywords == ["claude code", "fastapi"]
        assert j1.status == "scored"
        assert j2.relevance_score == 40


def test_complete_failed_stores_error_no_dispatch(api):
    client, SL = api
    jid = _mk_agent_job(SL)

    r = client.put(
        f"/api/callbacks/complete/{jid}",
        json={"status": "failed", "error_message": "context fetch 401"},
        headers={"X-Callback-Secret": _SECRET},
    )
    assert r.status_code == 200
    assert r.json()["dispatched"] is False

    with SL() as s:
        row = s.get(AgentJob, jid)
        assert row.status == "failed"
        assert row.error_message == "context fetch 401"


def test_context_for_job_score_returns_unscored_jobs(api):
    client, SL = api
    jid = _mk_agent_job(SL, job_type="job_score")

    with SL() as s:
        s.add_all([
            ScrapedJob(source="x", title="Unscored 1", company_name="A", content_hash="u1"),
            ScrapedJob(source="x", title="Scored", company_name="B", content_hash="s1",
                       relevance_score=70),
        ])
        s.commit()

    r = client.get(
        f"/api/callbacks/context/{jid}",
        headers={"X-Callback-Secret": _SECRET},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["job_type"] == "job_score"
    titles = {j["title"] for j in body["payload"]["jobs"]}
    assert "Unscored 1" in titles
    assert "Scored" not in titles


def test_context_404_for_missing_agent_job(api):
    client, _ = api
    r = client.get(
        "/api/callbacks/context/99999",
        headers={"X-Callback-Secret": _SECRET},
    )
    assert r.status_code == 404


def test_progress_rejects_when_callback_secret_not_configured(api, monkeypatch):
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "")
    client, SL = api
    jid = _mk_agent_job(SL)
    r = client.put(
        f"/api/callbacks/progress/{jid}",
        json={"progress_pct": 10},
        headers={"X-Callback-Secret": "anything"},
    )
    assert r.status_code == 503
