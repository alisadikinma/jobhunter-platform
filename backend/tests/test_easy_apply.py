"""Easy Apply orchestration + real SMTP send endpoint tests.

Phase 3 — adds:
- POST /api/applications/easy-apply : idempotent per job_id, spawns
  cv-tailor + cold-email skills, returns both agent_job_ids + the new
  generated_cv_id.
- POST /api/emails/{id}/send : REAL SMTP send via mailer_service.send,
  transitions parent application to "applied" + sets email_sent_at.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.agent_job import AgentJob
from app.models.application import Application, ApplicationActivity
from app.models.cv import GeneratedCV, MasterCV
from app.models.email_draft import EmailDraft
from app.models.job import ScrapedJob
from app.models.user import User
from app.services import mailer_service

pytestmark = pytest.mark.integration


_VALID_CV = {
    "basics": {
        "name": "Ali",
        "email": "ali@example.com",
        "summary_variants": {
            "vibe_coding": "v",
            "ai_automation": "a",
            "ai_video": "vi",
        },
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


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Make claude_service.spawn_claude not actually spawn a real subprocess."""
    fake_proc = MagicMock()
    fake_proc.pid = 4242
    monkeypatch.setattr(
        "app.services.claude_service.subprocess.Popen",
        MagicMock(return_value=fake_proc),
    )
    return fake_proc


def _seed_job(SL, title="AI Engineer") -> int:
    with SL() as s:
        job = ScrapedJob(
            source="x",
            title=title,
            company_name="Acme",
            content_hash=f"h-{title}",
            suggested_variant="vibe_coding",
        )
        s.add(job)
        s.commit()
        return job.id


# ---------------------------------------------------------------- easy-apply


def test_easy_apply_creates_application_and_spawns_jobs(api, mock_subprocess):
    client, SL = api
    job_id = _seed_job(SL)

    r = client.post("/api/applications/easy-apply", json={"job_id": job_id})
    assert r.status_code == 201, r.text

    body = r.json()
    assert body["application_id"] > 0
    assert body["cv_agent_job_id"] > 0
    assert body["email_agent_job_id"] > 0
    assert body["generated_cv_id"] > 0
    assert body["cv_agent_job_id"] != body["email_agent_job_id"]

    with SL() as s:
        appl = s.get(Application, body["application_id"])
        assert appl is not None
        assert appl.status == "targeting"
        assert appl.job_id == job_id
        assert appl.targeted_at is not None

        # Activity log entry confirms Easy Apply origin.
        acts = (
            s.query(ApplicationActivity)
            .filter_by(application_id=appl.id, activity_type="created")
            .all()
        )
        assert len(acts) == 1
        assert "Easy Apply" in (acts[0].description or "")
        assert "AI Engineer" in (acts[0].description or "")

        # Both agent_jobs exist.
        cv_aj = s.get(AgentJob, body["cv_agent_job_id"])
        email_aj = s.get(AgentJob, body["email_agent_job_id"])
        assert cv_aj.job_type == "cv_tailor"
        assert cv_aj.reference_id == appl.id
        assert email_aj.job_type == "cold_email"
        assert email_aj.reference_id == appl.id

        # generated_cv row created (pending) by cv_generator.
        cv = s.get(GeneratedCV, body["generated_cv_id"])
        assert cv is not None
        assert cv.application_id == appl.id


def test_easy_apply_is_idempotent_per_job(api, mock_subprocess):
    """Calling Easy Apply twice for the same job returns the SAME application,
    but spawns FRESH agent_jobs each time so the user can re-run generation."""
    client, SL = api
    job_id = _seed_job(SL)

    r1 = client.post("/api/applications/easy-apply", json={"job_id": job_id})
    assert r1.status_code == 201
    b1 = r1.json()

    r2 = client.post("/api/applications/easy-apply", json={"job_id": job_id})
    assert r2.status_code == 201
    b2 = r2.json()

    assert b1["application_id"] == b2["application_id"]
    assert b1["cv_agent_job_id"] != b2["cv_agent_job_id"]
    assert b1["email_agent_job_id"] != b2["email_agent_job_id"]
    assert b1["generated_cv_id"] != b2["generated_cv_id"]

    with SL() as s:
        appls = s.query(Application).filter_by(job_id=job_id).all()
        assert len(appls) == 1


def test_easy_apply_404_when_job_missing(api, mock_subprocess):
    client, _ = api
    r = client.post("/api/applications/easy-apply", json={"job_id": 999_999})
    assert r.status_code == 404
    assert "Job not found" in r.json()["detail"]


def test_easy_apply_requires_auth():
    client = TestClient(app)
    r = client.post("/api/applications/easy-apply", json={"job_id": 1})
    assert r.status_code == 401


# ---------------------------------------------------------------- /send


def _seed_application_with_email(SL, recipient_email="hr@acme.com") -> tuple[int, int]:
    """Returns (application_id, email_draft_id)."""
    with SL() as s:
        job = ScrapedJob(
            source="x", title="AI Eng", company_name="Acme",
            content_hash="hsmtp", suggested_variant="vibe_coding",
        )
        s.add(job)
        s.commit()
        appl = Application(job_id=job.id, status="cv_ready")
        s.add(appl)
        s.commit()
        draft = EmailDraft(
            application_id=appl.id,
            job_id=job.id,
            email_type="initial",
            subject="Quick intro re: AI Eng role",
            body="Hi there, …",
            recipient_email=recipient_email,
            recipient_name="Hiring Manager",
            status="approved",
        )
        s.add(draft)
        s.commit()
        return appl.id, draft.id


def test_send_email_invokes_smtp_and_marks_application_applied(
    api, monkeypatch
):
    client, SL = api
    app_id, email_id = _seed_application_with_email(SL)

    captured: dict = {}

    def fake_send(msg, *, db=None):
        captured["msg"] = msg
        captured["db"] = db
        return {"message_id": "<test@local>", "to": msg.to_email}

    monkeypatch.setattr(mailer_service, "send", fake_send)

    r = client.post(f"/api/emails/{email_id}/send")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None

    msg = captured["msg"]
    assert isinstance(msg, mailer_service.MailMessage)
    assert msg.to_email == "hr@acme.com"
    assert msg.to_name == "Hiring Manager"
    assert msg.subject == "Quick intro re: AI Eng role"
    assert msg.body_text.startswith("Hi there")

    with SL() as s:
        draft = s.get(EmailDraft, email_id)
        assert draft.status == "sent"
        assert draft.sent_at is not None

        appl = s.get(Application, app_id)
        assert appl.status == "applied"
        assert appl.email_sent_at is not None
        assert appl.applied_at is not None  # set by transition_status

        types = {
            a.activity_type
            for a in s.query(ApplicationActivity).filter_by(application_id=app_id).all()
        }
        assert "status_change" in types


def test_send_email_404_for_missing_draft(api):
    client, _ = api
    r = client.post("/api/emails/999999/send")
    assert r.status_code == 404


def test_send_email_422_when_no_recipient(api, monkeypatch):
    client, SL = api
    monkeypatch.setattr(mailer_service, "send", MagicMock())
    _, email_id = _seed_application_with_email(SL, recipient_email=None)

    r = client.post(f"/api/emails/{email_id}/send")
    assert r.status_code == 422
    assert "recipient_email" in r.json()["detail"]
    # mailer.send must NOT be called when validation fails.
    mailer_service.send.assert_not_called()


def test_send_email_502_on_smtp_failure(api, monkeypatch):
    client, SL = api
    app_id, email_id = _seed_application_with_email(SL)

    def boom(msg, *, db=None):
        raise mailer_service.MailerError("SMTP authentication failed")

    monkeypatch.setattr(mailer_service, "send", boom)

    r = client.post(f"/api/emails/{email_id}/send")
    assert r.status_code == 502
    assert "SMTP" in r.json()["detail"]

    # Application status MUST NOT have been flipped.
    with SL() as s:
        draft = s.get(EmailDraft, email_id)
        assert draft.status != "sent"
        assert draft.sent_at is None
        appl = s.get(Application, app_id)
        assert appl.status == "cv_ready"
        assert appl.email_sent_at is None


def test_send_endpoint_is_distinct_from_mark_sent(api, monkeypatch):
    """Sanity: existing /sent (flag-only) endpoint must still exist alongside
    the new /send (real-SMTP) endpoint."""
    client, SL = api
    monkeypatch.setattr(mailer_service, "send", MagicMock())
    _, email_id = _seed_application_with_email(SL)

    # Existing flag-only endpoint still works without invoking SMTP.
    r1 = client.post(f"/api/emails/{email_id}/sent")
    assert r1.status_code == 200
    assert r1.json()["status"] == "sent"
    mailer_service.send.assert_not_called()
