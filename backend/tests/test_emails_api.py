"""Cold email API tests — generation + dispatch + CRUD."""
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
from app.models.cv import MasterCV
from app.models.email_draft import EmailDraft
from app.models.job import ScrapedJob
from app.models.user import User

pytestmark = pytest.mark.integration


_VALID_CV = {
    "basics": {
        "name": "A",
        "email": "a@a.com",
        "summary_variants": {"vibe_coding": "v", "ai_automation": "au", "ai_video": "vi"},
    },
    "work": [],
}


@pytest.fixture
def api(pg_engine, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "AGENT_JOB_LOG_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "CALLBACK_SECRET", "sec")

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


def _seed_app(SL, variant="vibe_coding") -> int:
    with SL() as s:
        job = ScrapedJob(
            source="x", title="AI Eng", company_name="Acme",
            content_hash="he", suggested_variant=variant,
        )
        s.add(job)
        s.commit()
        appl = Application(job_id=job.id, status="cv_ready")
        s.add(appl)
        s.commit()
        return appl.id


def test_generate_creates_agent_job(api, monkeypatch):
    client, SL = api
    app_id = _seed_app(SL)

    fake_proc = MagicMock()
    fake_proc.pid = 1
    monkeypatch.setattr(
        "app.services.claude_service.subprocess.Popen",
        MagicMock(return_value=fake_proc),
    )

    r = client.post("/api/emails/generate", json={"application_id": app_id})
    assert r.status_code == 202
    body = r.json()
    assert body["application_id"] == app_id
    assert body["agent_job_id"] > 0

    with SL() as s:
        aj = s.get(AgentJob, body["agent_job_id"])
        assert aj.job_type == "cold_email"
        assert aj.reference_id == app_id


def test_generate_404_missing_application(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(
        "app.services.claude_service.subprocess.Popen", MagicMock(),
    )
    assert client.post("/api/emails/generate", json={"application_id": 99999}).status_code == 404


def test_callback_creates_three_email_drafts(api):
    client, SL = api
    app_id = _seed_app(SL)

    with SL() as s:
        aj = AgentJob(job_type="cold_email", reference_id=app_id, status="running")
        s.add(aj)
        s.commit()
        aj_id = aj.id

    result = {
        "initial": {"subject": "Quick note", "body": "Body of the initial email here."},
        "follow_up_1": {"subject": "Quick note", "body": "Body of follow-up 1."},
        "follow_up_2": {"subject": "Quick note", "body": "Body of follow-up 2."},
        "strategy": "vibe_coding/velocity",
        "personalization_notes": ["referenced their Claude CLI migration post"],
    }
    r = client.put(
        f"/api/callbacks/complete/{aj_id}",
        json={"status": "completed", "result": result},
        headers={"X-Callback-Secret": "sec"},
    )
    assert r.status_code == 200
    assert "cold_email:3" in r.json()["dispatched"]

    with SL() as s:
        drafts = s.query(EmailDraft).filter_by(application_id=app_id).order_by(EmailDraft.email_type).all()
        assert [d.email_type for d in drafts] == ["follow_up_1", "follow_up_2", "initial"]  # alpha sort
        assert all(d.status == "draft" for d in drafts)
        assert drafts[0].strategy == "vibe_coding/velocity"


def test_callback_upserts_on_regeneration(api):
    client, SL = api
    app_id = _seed_app(SL)

    with SL() as s:
        aj = AgentJob(job_type="cold_email", reference_id=app_id, status="running")
        s.add(aj)
        s.commit()
        aj_id = aj.id

    def _post(v):
        return client.put(
            f"/api/callbacks/complete/{aj_id}",
            json={
                "status": "completed",
                "result": {
                    "initial": {"subject": f"s-{v}", "body": f"body v{v} content"},
                    "follow_up_1": {"subject": f"f1-{v}", "body": f"fu1 v{v} body"},
                    "follow_up_2": {"subject": f"f2-{v}", "body": f"fu2 v{v} body"},
                },
            },
            headers={"X-Callback-Secret": "sec"},
        )

    _post(1)
    _post(2)

    with SL() as s:
        drafts = s.query(EmailDraft).filter_by(application_id=app_id).all()
        assert len(drafts) == 3  # upserted, not duplicated
        subjects = {d.subject for d in drafts}
        assert all(s.endswith("-2") for s in subjects)  # second payload won


def test_list_by_application(api):
    client, SL = api
    app_id = _seed_app(SL)
    with SL() as s:
        s.add(EmailDraft(application_id=app_id, email_type="initial", body="b1", subject="s1"))
        s.add(EmailDraft(application_id=app_id, email_type="follow_up_1", body="b2", subject="s2"))
        s.commit()

    r = client.get(f"/api/emails?application_id={app_id}")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_edit_email_flips_status(api):
    client, SL = api
    app_id = _seed_app(SL)
    with SL() as s:
        d = EmailDraft(application_id=app_id, email_type="initial", body="b", subject="s", status="draft")
        s.add(d)
        s.commit()
        eid = d.id

    r = client.put(f"/api/emails/{eid}", json={"subject": "new subject", "body": "new body"})
    body = r.json()
    assert body["subject"] == "new subject"
    assert body["status"] == "edited"


def test_approve_email(api):
    client, SL = api
    app_id = _seed_app(SL)
    with SL() as s:
        d = EmailDraft(application_id=app_id, email_type="initial", body="b", subject="s", status="draft")
        s.add(d)
        s.commit()
        eid = d.id

    assert client.post(f"/api/emails/{eid}/approve").json()["status"] == "approved"


def test_mark_sent_sets_sent_at(api):
    client, SL = api
    app_id = _seed_app(SL)
    with SL() as s:
        d = EmailDraft(application_id=app_id, email_type="initial", body="b", subject="s", status="approved")
        s.add(d)
        s.commit()
        eid = d.id

    body = client.post(f"/api/emails/{eid}/sent").json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None


def test_context_cold_email_includes_variant_and_company(api):
    client, SL = api
    app_id = _seed_app(SL, variant="ai_automation")

    with SL() as s:
        aj = AgentJob(job_type="cold_email", reference_id=app_id, status="running")
        s.add(aj)
        s.commit()
        aj_id = aj.id

    r = client.get(f"/api/callbacks/context/{aj_id}", headers={"X-Callback-Secret": "sec"})
    body = r.json()
    assert body["job_type"] == "cold_email"
    payload = body["payload"]
    assert payload["application_id"] == app_id
    assert payload["variant_used"] == "ai_automation"
    assert payload["job"]["title"] == "AI Eng"
    assert payload["master_cv_summary"] is not None
