"""Applications tracker API tests."""
from datetime import UTC

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.application import Application, ApplicationActivity
from app.models.job import ScrapedJob
from app.models.user import User

pytestmark = pytest.mark.integration


@pytest.fixture
def api(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        s.add(User(email="a@t.local", password_hash=hash_password("x"), name="A"))
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


def _seed_job(SL, title="AI Engineer") -> int:
    with SL() as s:
        job = ScrapedJob(source="x", title=title, company_name="Acme", content_hash=f"h-{title}")
        s.add(job)
        s.commit()
        return job.id


def test_create_application_from_job_id(api):
    client, SL = api
    jid = _seed_job(SL)
    r = client.post("/api/applications", json={"job_id": jid})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "targeting"
    assert body["job_id"] == jid

    with SL() as s:
        acts = s.query(ApplicationActivity).filter_by(application_id=body["id"]).all()
        assert len(acts) == 1
        assert acts[0].activity_type == "created"


def test_create_404_for_missing_job(api):
    client, _ = api
    r = client.post("/api/applications", json={"job_id": 99999})
    assert r.status_code == 404


def test_patch_status_logs_activity_and_sets_timestamp(api):
    client, SL = api
    jid = _seed_job(SL)
    app_id = client.post("/api/applications", json={"job_id": jid}).json()["id"]

    r = client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    body = r.json()
    assert body["status"] == "applied"
    assert body["applied_at"] is not None

    with SL() as s:
        acts = s.query(ApplicationActivity).filter_by(application_id=app_id).all()
        # 'created' + 'status_change'
        types = [a.activity_type for a in acts]
        assert "created" in types
        assert "status_change" in types


def test_patch_status_idempotent_no_duplicate_activity(api):
    client, SL = api
    jid = _seed_job(SL)
    app_id = client.post("/api/applications", json={"job_id": jid}).json()["id"]

    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})  # no-op

    with SL() as s:
        count = (
            s.query(ApplicationActivity)
            .filter_by(application_id=app_id, activity_type="status_change")
            .count()
        )
        assert count == 1


def test_patch_notes_logs_edited_activity(api):
    client, SL = api
    jid = _seed_job(SL)
    app_id = client.post("/api/applications", json={"job_id": jid}).json()["id"]

    client.patch(f"/api/applications/{app_id}", json={"notes": "Warm intro via John"})

    with SL() as s:
        acts = s.query(ApplicationActivity).filter_by(application_id=app_id).all()
        types = [a.activity_type for a in acts]
        assert "edited" in types


def test_get_detail_includes_activities_timeline(api):
    client, SL = api
    jid = _seed_job(SL)
    app_id = client.post("/api/applications", json={"job_id": jid}).json()["id"]
    client.patch(f"/api/applications/{app_id}", json={"status": "applied"})

    r = client.get(f"/api/applications/{app_id}")
    body = r.json()
    assert len(body["activities"]) >= 2
    # reverse chronological
    assert body["activities"][0]["activity_type"] in {"status_change", "edited", "created"}


def test_kanban_groups_by_status(api):
    client, SL = api
    j1 = _seed_job(SL, "J1")
    j2 = _seed_job(SL, "J2")
    a1 = client.post("/api/applications", json={"job_id": j1}).json()["id"]
    client.post("/api/applications", json={"job_id": j2})
    client.patch(f"/api/applications/{a1}", json={"status": "applied"})

    r = client.get("/api/applications/kanban")
    cols = r.json()["columns"]
    assert len(cols["targeting"]) == 1
    assert len(cols["applied"]) == 1
    # all 12 keys present
    assert set(cols.keys()) >= {
        "targeting", "cv_generating", "cv_ready", "applied", "email_sent",
        "replied", "interview_scheduled", "interviewed", "offered",
        "accepted", "rejected", "ghosted",
    }


def test_stats_with_no_applications_returns_zero_rates(api):
    client, _ = api
    r = client.get("/api/applications/stats")
    body = r.json()
    assert body["total"] == 0
    assert body["response_rate"] == 0.0
    assert body["offer_rate"] == 0.0
    assert body["avg_days_to_reply"] is None


def test_stats_response_rate_when_emails_sent(api, pg_engine):
    from datetime import datetime, timedelta

    from sqlalchemy.orm import Session

    with Session(pg_engine) as s:
        for _ in range(4):
            s.add(Application(
                status="email_sent",
                email_sent_at=datetime.now(UTC) - timedelta(days=5),
            ))
        # 2 of 4 replied
        for a in s.query(Application).limit(2):
            a.status = "replied"
            a.replied_at = datetime.now(UTC) - timedelta(days=3)
        s.commit()

    client, _ = api
    body = client.get("/api/applications/stats").json()
    assert body["by_status"]["email_sent"] == 2
    assert body["by_status"]["replied"] == 2
    assert body["response_rate"] == 0.5
    assert body["avg_days_to_reply"] is not None


def test_delete_removes_application(api):
    client, SL = api
    jid = _seed_job(SL)
    aid = client.post("/api/applications", json={"job_id": jid}).json()["id"]
    assert client.delete(f"/api/applications/{aid}").status_code == 204
    assert client.get(f"/api/applications/{aid}").status_code == 404


def test_list_filter_by_status(api):
    client, SL = api
    j1 = _seed_job(SL, "J1")
    j2 = _seed_job(SL, "J2")
    a1 = client.post("/api/applications", json={"job_id": j1}).json()["id"]
    client.post("/api/applications", json={"job_id": j2})
    client.patch(f"/api/applications/{a1}", json={"status": "applied"})

    all_r = client.get("/api/applications").json()
    applied_only = client.get("/api/applications?status=applied").json()
    assert len(all_r) == 2
    assert len(applied_only) == 1


def test_list_requires_auth():
    client = TestClient(app)
    assert client.get("/api/applications").status_code == 401
