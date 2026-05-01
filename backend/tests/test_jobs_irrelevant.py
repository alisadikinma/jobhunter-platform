"""Phase 5 — user_irrelevant flag on scraped_jobs.

Covers:
- PATCH /api/jobs/{id} accepts user_irrelevant.
- GET /api/jobs excludes flagged rows by default.
- GET /api/jobs?include_irrelevant=true returns flagged rows too.
- PATCH can unflag (user_irrelevant=False) — used by Restore action.
"""
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


def _seed_pair(SessionLocal):
    """Two jobs: one relevant, one already-flagged-irrelevant. Returns (relevant_id, irrelevant_id)."""
    with SessionLocal() as s:
        relevant = ScrapedJob(
            source="remoteok",
            title="AI Engineer",
            company_name="Acme",
            relevance_score=90,
            suggested_variant="vibe_coding",
            status="new",
            content_hash="h-rel",
        )
        irrelevant = ScrapedJob(
            source="remoteok",
            title="DevOps Engineer",
            company_name="Beta",
            relevance_score=40,
            suggested_variant=None,
            status="new",
            content_hash="h-irrel",
            user_irrelevant=True,
        )
        s.add_all([relevant, irrelevant])
        s.commit()
        return relevant.id, irrelevant.id


def test_patch_marks_job_irrelevant(api):
    client, SL = api
    with SL() as s:
        job = ScrapedJob(
            source="remoteok",
            title="Some Job",
            company_name="X",
            content_hash="h-patch",
        )
        s.add(job)
        s.commit()
        jid = job.id

    r = client.patch(f"/api/jobs/{jid}", json={"user_irrelevant": True})
    assert r.status_code == 200, r.text
    assert r.json()["user_irrelevant"] is True


def test_list_excludes_irrelevant_by_default(api):
    client, SL = api
    relevant_id, irrelevant_id = _seed_pair(SL)
    r = client.get("/api/jobs")
    assert r.status_code == 200
    ids = [j["id"] for j in r.json()["items"]]
    assert relevant_id in ids
    assert irrelevant_id not in ids


def test_list_includes_irrelevant_when_flag_set(api):
    client, SL = api
    relevant_id, irrelevant_id = _seed_pair(SL)
    r = client.get("/api/jobs?include_irrelevant=true")
    assert r.status_code == 200
    ids = [j["id"] for j in r.json()["items"]]
    assert relevant_id in ids
    assert irrelevant_id in ids


def test_unflag_relevant(api):
    client, SL = api
    _, irrelevant_id = _seed_pair(SL)
    r = client.patch(
        f"/api/jobs/{irrelevant_id}",
        json={"user_irrelevant": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["user_irrelevant"] is False
    # And it now appears in default list.
    listing = client.get("/api/jobs").json()
    assert irrelevant_id in [j["id"] for j in listing["items"]]
