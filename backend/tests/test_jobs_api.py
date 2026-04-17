"""Jobs browsing/filtering/stats API tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
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


def _seed_jobs(SessionLocal):
    with SessionLocal() as s:
        s.add_all([
            ScrapedJob(
                source="remoteok", title="AI Engineer", company_name="Acme",
                relevance_score=90, suggested_variant="vibe_coding",
                status="new", content_hash="h1",
            ),
            ScrapedJob(
                source="remoteok", title="ML Engineer", company_name="Beta",
                relevance_score=70, suggested_variant="ai_automation",
                status="reviewed", content_hash="h2",
            ),
            ScrapedJob(
                source="arbeitnow", title="Video AI Specialist", company_name="Gamma",
                relevance_score=85, suggested_variant="ai_video",
                status="new", content_hash="h3", is_favorite=True,
            ),
        ])
        s.commit()


def test_list_returns_paginated_results(api):
    client, SL = api
    _seed_jobs(SL)
    r = client.get("/api/jobs?page=1&page_size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_filters_by_status(api):
    client, SL = api
    _seed_jobs(SL)
    r = client.get("/api/jobs?status=new")
    assert r.json()["total"] == 2


def test_list_filters_by_min_score(api):
    client, SL = api
    _seed_jobs(SL)
    r = client.get("/api/jobs?min_score=80")
    assert r.json()["total"] == 2


def test_list_filters_by_variant(api):
    client, SL = api
    _seed_jobs(SL)
    r = client.get("/api/jobs?variant=ai_video")
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Video AI Specialist"


def test_list_search_matches_title_or_company(api):
    client, SL = api
    _seed_jobs(SL)
    r = client.get("/api/jobs?search=Acme")
    assert r.json()["total"] == 1


def test_stats_returns_bucketed_counts(api):
    client, SL = api
    _seed_jobs(SL)
    r = client.get("/api/jobs/stats")
    body = r.json()
    assert body["total"] == 3
    assert body["by_status"]["new"] == 2
    assert body["by_source"]["remoteok"] == 2
    assert body["by_variant"]["ai_video"] == 1
    assert body["high_score_count"] == 2


def test_patch_updates_status_and_favorite(api):
    client, SL = api
    _seed_jobs(SL)
    jid = client.get("/api/jobs?status=new&page_size=1").json()["items"][0]["id"]
    r = client.patch(f"/api/jobs/{jid}", json={"status": "applied", "is_favorite": True})
    body = r.json()
    assert body["status"] == "applied"
    assert body["is_favorite"] is True


def test_favorite_toggle_flips_flag(api):
    client, SL = api
    _seed_jobs(SL)
    jid = client.get("/api/jobs?search=Acme").json()["items"][0]["id"]
    assert client.post(f"/api/jobs/{jid}/favorite").json()["is_favorite"] is True
    assert client.post(f"/api/jobs/{jid}/favorite").json()["is_favorite"] is False


def test_get_404_for_missing(api):
    client, _ = api
    assert client.get("/api/jobs/9999").status_code == 404


def test_delete_removes_job(api):
    client, SL = api
    _seed_jobs(SL)
    jid = client.get("/api/jobs?search=Acme").json()["items"][0]["id"]
    assert client.delete(f"/api/jobs/{jid}").status_code == 204
    assert client.get(f"/api/jobs/{jid}").status_code == 404


def test_list_requires_auth():
    client = TestClient(app)
    assert client.get("/api/jobs").status_code == 401
