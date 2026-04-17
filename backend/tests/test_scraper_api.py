"""Scraper configs CRUD + run endpoint tests."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.scrape_config import ScrapeConfig
from app.models.user import User
from app.schemas.scraper import NormalizedJob

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


def _stub_jobs() -> list[NormalizedJob]:
    return [
        NormalizedJob(source="remoteok", title="AI Engineer", company_name="Acme", description="Build LLMs"),
        NormalizedJob(source="arbeitnow", title="ML Engineer", company_name="Beta", description="Train models"),
    ]


def test_create_config(api):
    client, _ = api
    r = client.post(
        "/api/scraper/configs",
        json={
            "name": "Test Vibe",
            "variant_target": "vibe_coding",
            "keywords": ["AI Engineer"],
            "sources": ["remoteok"],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Test Vibe"
    assert body["variant_target"] == "vibe_coding"
    assert body["cron_expression"] == "0 */3 * * *"


def test_list_configs_returns_seeded(api):
    client, SL = api
    with SL() as s:
        s.add(ScrapeConfig(name="Seed 1", variant_target="vibe_coding", keywords=["x"], sources=["remoteok"]))
        s.commit()
    r = client.get("/api/scraper/configs")
    assert len(r.json()) >= 1


def test_update_config_mutates_fields(api):
    client, _ = api
    created = client.post(
        "/api/scraper/configs",
        json={"name": "Original", "keywords": ["x"], "sources": ["remoteok"]},
    ).json()
    r = client.put(f"/api/scraper/configs/{created['id']}", json={"is_active": False, "name": "Renamed"})
    body = r.json()
    assert body["is_active"] is False
    assert body["name"] == "Renamed"


def test_delete_config(api):
    client, _ = api
    c = client.post(
        "/api/scraper/configs",
        json={"name": "del", "keywords": ["x"], "sources": ["remoteok"]},
    ).json()
    assert client.delete(f"/api/scraper/configs/{c['id']}").status_code == 204


def test_run_with_config_id_populates_suggested_variant(api):
    client, SL = api
    with SL() as s:
        cfg = ScrapeConfig(
            name="Vibe", variant_target="vibe_coding",
            keywords=["AI"], sources=["remoteok"],
        )
        s.add(cfg)
        s.commit()
        cfg_id = cfg.id

    with patch("app.services.scraper_service.aggregate", return_value=_stub_jobs()):
        r = client.post("/api/scraper/run", json={"config_id": cfg_id})

    assert r.status_code == 200
    body = r.json()
    assert body["new_jobs"] == 2
    assert body["duplicates"] == 0

    # Verify suggested_variant was populated from config.
    from app.models.job import ScrapedJob

    with SL() as s:
        rows = s.query(ScrapedJob).all()
        assert all(r.suggested_variant == "vibe_coding" for r in rows)


def test_run_deduplicates_on_rerun(api):
    client, SL = api
    with SL() as s:
        cfg = ScrapeConfig(
            name="X", variant_target="ai_automation",
            keywords=["AI"], sources=["remoteok"],
        )
        s.add(cfg)
        s.commit()
        cfg_id = cfg.id

    with patch("app.services.scraper_service.aggregate", return_value=_stub_jobs()):
        first = client.post("/api/scraper/run", json={"config_id": cfg_id}).json()
        second = client.post("/api/scraper/run", json={"config_id": cfg_id}).json()

    assert first["new_jobs"] == 2
    assert second["new_jobs"] == 0
    assert second["duplicates"] == 2


def test_run_ad_hoc_without_config(api):
    client, _ = api
    with patch("app.services.scraper_service.aggregate", return_value=_stub_jobs()):
        r = client.post(
            "/api/scraper/run",
            json={"keywords": ["AI"], "sources": ["remoteok"]},
        )
    assert r.status_code == 200
    assert r.json()["new_jobs"] == 2


def test_run_422_without_config_or_inline(api):
    client, _ = api
    # Authed, but no config_id and no inline keywords+sources → 422.
    assert client.post("/api/scraper/run", json={}).status_code == 422


def test_run_404_for_missing_config(api):
    client, _ = api
    assert client.post("/api/scraper/run", json={"config_id": 99999}).status_code == 404


def test_run_409_for_inactive_config(api):
    client, SL = api
    with SL() as s:
        cfg = ScrapeConfig(
            name="off", is_active=False, keywords=["x"], sources=["remoteok"],
        )
        s.add(cfg)
        s.commit()
        cfg_id = cfg.id

    assert client.post("/api/scraper/run", json={"config_id": cfg_id}).status_code == 409


def test_status_endpoint_lists_configs(api):
    client, SL = api
    with SL() as s:
        s.add(ScrapeConfig(name="S", keywords=["x"], sources=["remoteok"]))
        s.commit()
    r = client.get("/api/scraper/status")
    body = r.json()
    assert "configs" in body
    assert len(body["configs"]) >= 1
