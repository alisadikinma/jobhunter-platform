"""CV generation tests — cv_generator.service + API + callback dispatch."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.agent_job import AgentJob
from app.models.application import Application
from app.models.cv import GeneratedCV, MasterCV
from app.models.job import ScrapedJob
from app.models.user import User

pytestmark = pytest.mark.integration


_VALID_CV = {
    "basics": {
        "name": "Ali",
        "email": "ali@example.com",
        "summary_variants": {
            "vibe_coding": "a", "ai_automation": "b", "ai_video": "c",
        },
    },
    "work": [],
}


@pytest.fixture
def api(pg_engine, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "AGENT_JOB_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "s")

    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        s.add(User(email="a@t.local", password_hash=hash_password("x"), name="A"))
        s.add(MasterCV(version=1, content=_VALID_CV, is_active=True))
        s.commit()
        user = s.query(User).filter_by(email="a@t.local").one()
        token = create_access_token({"sub": str(user.id), "email": user.email})

    def _db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    try:
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, SessionLocal
    finally:
        app.dependency_overrides.clear()


def _seed_app(SessionLocal) -> int:
    with SessionLocal() as s:
        job = ScrapedJob(source="x", title="AI Eng", company_name="Acme", content_hash="ha")
        s.add(job)
        s.commit()
        appl = Application(job_id=job.id, status="targeting")
        s.add(appl)
        s.commit()
        return appl.id


def test_generate_creates_generated_cv_and_agent_job(api, monkeypatch):
    client, SL = api
    app_id = _seed_app(SL)

    fake_proc = MagicMock()
    fake_proc.pid = 42
    monkeypatch.setattr(
        "app.services.claude_service.subprocess.Popen",
        MagicMock(return_value=fake_proc),
    )

    r = client.post("/api/cv/generate", json={"application_id": app_id})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "pending"
    assert body["generated_cv_id"] > 0
    assert body["agent_job_id"] > 0

    with SL() as s:
        cv = s.get(GeneratedCV, body["generated_cv_id"])
        assert cv.application_id == app_id
        assert cv.master_cv_id is not None
        aj = s.get(AgentJob, body["agent_job_id"])
        assert aj.job_type == "cv_tailor"
        assert aj.reference_id == app_id


def test_generate_400_when_application_missing(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(
        "app.services.claude_service.subprocess.Popen",
        MagicMock(),
    )
    r = client.post("/api/cv/generate", json={"application_id": 99999})
    assert r.status_code == 400


def test_generate_400_when_no_master_cv(pg_engine, monkeypatch, tmp_path):
    """No active master CV → 400 with the seed hint."""
    monkeypatch.setattr(settings, "AGENT_JOB_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "s")

    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        s.add(User(email="a@t.local", password_hash=hash_password("x"), name="A"))
        job = ScrapedJob(source="x", title="T", company_name="C", content_hash="hh")
        s.add(job)
        s.commit()
        appl = Application(job_id=job.id, status="targeting")
        s.add(appl)
        s.commit()
        app_id = appl.id
        user = s.query(User).one()
        token = create_access_token({"sub": str(user.id), "email": user.email})

    def _db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    try:
        client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
        r = client.post("/api/cv/generate", json={"application_id": app_id})
        assert r.status_code == 400
        assert "master CV" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_callback_complete_applies_cv_tailor_result(api, monkeypatch):
    client, SL = api
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "s")
    app_id = _seed_app(SL)

    # Simulate the spawn path by creating agent_job + generated_cv directly.
    with SL() as s:
        aj = AgentJob(job_type="cv_tailor", reference_id=app_id, status="running")
        s.add(aj)
        cv = GeneratedCV(application_id=app_id, status="pending")
        s.add(cv)
        s.commit()
        aj_id = aj.id
        cv_id = cv.id

    result = {
        "tailored_markdown": "# Ali\n\nSummary here...\n",
        "tailored_json": {"basics": {"name": "Ali"}},
        "variant_used": "vibe_coding",
        "confidence": 0.87,
        "keyword_matches": ["claude-code", "fastapi"],
        "missing_keywords": ["kubernetes"],
        "selected_portfolio_ids": [1, 3],
    }
    r = client.put(
        f"/api/callbacks/complete/{aj_id}",
        json={"status": "completed", "result": result},
        headers={"X-Callback-Secret": "s"},
    )
    assert r.status_code == 200
    assert "cv_tailor:ready" in r.json()["dispatched"]

    with SL() as s:
        cv = s.get(GeneratedCV, cv_id)
        assert cv.status == "ready"
        assert cv.variant_used == "vibe_coding"
        assert cv.confidence == 87
        assert cv.tailored_markdown.startswith("# Ali")
        assert cv.keyword_matches == ["claude-code", "fastapi"]


def test_callback_complete_handles_no_match(api, monkeypatch):
    client, SL = api
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "s")
    app_id = _seed_app(SL)

    with SL() as s:
        aj = AgentJob(job_type="cv_tailor", reference_id=app_id, status="running")
        s.add(aj)
        cv = GeneratedCV(application_id=app_id, status="pending")
        s.add(cv)
        s.commit()
        aj_id = aj.id
        cv_id = cv.id

    r = client.put(
        f"/api/callbacks/complete/{aj_id}",
        json={
            "status": "completed",
            "result": {
                "variant_used": "no_match",
                "rejected_keywords_reason": "JD is a sales role",
            },
        },
        headers={"X-Callback-Secret": "s"},
    )
    body = r.json()
    assert "cv_tailor:no_match" in body["dispatched"]

    with SL() as s:
        cv = s.get(GeneratedCV, cv_id)
        assert cv.status == "no_match"
        assert "JD is a sales role" in (cv.suggestions or {}).get("rejected_reason", "")


def test_context_for_cv_tailor_returns_full_payload(api, monkeypatch):
    client, SL = api
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "s")
    app_id = _seed_app(SL)

    with SL() as s:
        aj = AgentJob(job_type="cv_tailor", reference_id=app_id, status="running")
        s.add(aj)
        s.commit()
        aj_id = aj.id

    r = client.get(f"/api/callbacks/context/{aj_id}", headers={"X-Callback-Secret": "s"})
    body = r.json()
    assert body["job_type"] == "cv_tailor"
    payload = body["payload"]
    assert payload["application_id"] == app_id
    assert payload["master_cv"] is not None
    assert payload["job"]["title"] == "AI Eng"


def test_edit_generated_cv_sets_status_edited(api):
    client, SL = api
    app_id = _seed_app(SL)
    with SL() as s:
        cv = GeneratedCV(application_id=app_id, status="ready", tailored_markdown="old")
        s.add(cv)
        s.commit()
        cv_id = cv.id

    r = client.put(f"/api/cv/{cv_id}", json={"tailored_markdown": "# New content"})
    body = r.json()
    assert body["status"] == "edited"
    assert body["tailored_markdown"] == "# New content"


def test_get_generated_404_for_missing(api):
    client, _ = api
    assert client.get("/api/cv/99999").status_code == 404
