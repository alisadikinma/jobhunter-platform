"""Enrichment API tests — real Postgres + mocked Firecrawl."""
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.enrichment import _get_firecrawl
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.company import Company
from app.models.job import ScrapedJob
from app.models.user import User
from app.services.firecrawl_service import FirecrawlService

pytestmark = pytest.mark.integration


@pytest.fixture
def api_client(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)

    with SessionLocal() as s:
        s.add(User(email="admin@test.local", password_hash=hash_password("x"), name="A"))
        s.commit()
        user = s.query(User).filter_by(email="admin@test.local").one()
        token = create_access_token({"sub": str(user.id), "email": user.email})

    def _override_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    try:
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, SessionLocal
    finally:
        app.dependency_overrides.clear()


def _stub_firecrawl(markdown: str = "", error: str | None = None) -> FirecrawlService:
    stub = MagicMock(spec=FirecrawlService)
    stub.scrape.return_value = {
        "markdown": markdown,
        "html": "",
        "title": "Scraped Title",
        "description": "Scraped Description",
        "metadata": {},
        "extract": None,
        "error": error,
    }
    stub.__enter__.return_value = stub
    stub.__exit__.return_value = None
    return stub


def test_enrich_job_updates_description_when_firecrawl_returns_longer_content(api_client):
    client, SessionLocal = api_client
    with SessionLocal() as s:
        job = ScrapedJob(
            source="remoteok",
            title="AI Engineer",
            company_name="Acme",
            source_url="https://example.com/job/1",
            description="short JD",
        )
        s.add(job)
        s.commit()
        job_id = job.id

    long_md = "# Full JD\n\n" + ("detailed paragraph " * 50)
    fake = _stub_firecrawl(markdown=long_md)
    app.dependency_overrides[_get_firecrawl] = lambda: fake

    try:
        r = client.post(f"/api/enrichment/job/{job_id}")
    finally:
        app.dependency_overrides.pop(_get_firecrawl, None)

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["length_after"] > body["length_before"]
    assert body["source"] == "firecrawl_enriched"

    with SessionLocal() as s:
        job = s.get(ScrapedJob, job_id)
        assert job.description.startswith("# Full JD")
        assert job.description_source == "firecrawl_enriched"
        assert job.enriched_at is not None


def test_enrich_job_keeps_original_when_firecrawl_returns_shorter(api_client):
    client, SessionLocal = api_client
    with SessionLocal() as s:
        long_existing = "x" * 2000
        job = ScrapedJob(
            source="remoteok",
            title="AI Engineer",
            company_name="Acme",
            source_url="https://example.com/job/2",
            description=long_existing,
        )
        s.add(job)
        s.commit()
        job_id = job.id

    fake = _stub_firecrawl(markdown="short")
    app.dependency_overrides[_get_firecrawl] = lambda: fake
    try:
        r = client.post(f"/api/enrichment/job/{job_id}")
    finally:
        app.dependency_overrides.pop(_get_firecrawl, None)

    body = r.json()
    assert body["length_after"] == body["length_before"]


def test_enrich_job_returns_ok_false_on_firecrawl_failure(api_client):
    client, SessionLocal = api_client
    with SessionLocal() as s:
        job = ScrapedJob(
            source="remoteok",
            title="X",
            company_name="Y",
            source_url="https://example.com/job/3",
            description="x",
        )
        s.add(job)
        s.commit()
        job_id = job.id

    fake = _stub_firecrawl(markdown="", error="timeout")
    app.dependency_overrides[_get_firecrawl] = lambda: fake
    try:
        r = client.post(f"/api/enrichment/job/{job_id}")
    finally:
        app.dependency_overrides.pop(_get_firecrawl, None)

    body = r.json()
    assert body["ok"] is False
    assert "timeout" in (body["message"] or "")


def test_enrich_job_404_when_missing(api_client):
    client, _ = api_client
    assert client.post("/api/enrichment/job/99999").status_code == 404


def test_enrich_job_422_when_no_source_url(api_client):
    client, SessionLocal = api_client
    with SessionLocal() as s:
        job = ScrapedJob(source="x", title="t", company_name="c")
        s.add(job)
        s.commit()
        job_id = job.id

    r = client.post(f"/api/enrichment/job/{job_id}")
    assert r.status_code == 422


def test_enrich_company_stores_enriched_context(api_client):
    client, SessionLocal = api_client
    with SessionLocal() as s:
        company = Company(name="Gamma", domain="gamma.example")
        s.add(company)
        s.commit()
        cid = company.id

    fake = _stub_firecrawl(markdown="## About Gamma\nWe do AI.")
    app.dependency_overrides[_get_firecrawl] = lambda: fake
    try:
        r = client.post(f"/api/enrichment/company/{cid}")
    finally:
        app.dependency_overrides.pop(_get_firecrawl, None)

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["markdown_chars"] > 0

    with SessionLocal() as s:
        c = s.get(Company, cid)
        ctx = (c.metadata_ or {}).get("enriched_context")
        assert ctx is not None
        assert ctx["markdown"].startswith("## About Gamma")
        assert "fetched_at" in ctx


def test_enrich_company_422_when_no_domain(api_client):
    client, SessionLocal = api_client
    with SessionLocal() as s:
        company = Company(name="NoDomain")
        s.add(company)
        s.commit()
        cid = company.id

    r = client.post(f"/api/enrichment/company/{cid}")
    assert r.status_code == 422
