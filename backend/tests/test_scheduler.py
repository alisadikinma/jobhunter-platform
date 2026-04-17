"""APScheduler tests — uses memory jobstore so no real threads/timers run."""
import pytest

from app.models.scrape_config import ScrapeConfig
from app.scheduler import (
    _run_config_job,
    build_scheduler,
    register_scrape_configs,
)

pytestmark = pytest.mark.integration


def _seed_config(session, **overrides) -> int:
    defaults = {
        "name": "Seed",
        "variant_target": "vibe_coding",
        "keywords": ["x"],
        "sources": ["remoteok"],
        "cron_expression": "0 */3 * * *",
        "is_active": True,
    }
    defaults.update(overrides)
    cfg = ScrapeConfig(**defaults)
    session.add(cfg)
    session.commit()
    return cfg.id


def test_register_installs_one_job_per_active_config(pg_session, monkeypatch):
    # Point scheduler's SessionLocal at the test engine.
    monkeypatch.setattr(
        "app.scheduler.SessionLocal",
        lambda: pg_session.__class__(bind=pg_session.get_bind()),
    )
    _seed_config(pg_session, name="A")
    _seed_config(pg_session, name="B")
    _seed_config(pg_session, name="Inactive", is_active=False)

    scheduler = build_scheduler()
    count = register_scrape_configs(scheduler)
    try:
        assert count == 2
        ids = [j.id for j in scheduler.get_jobs()]
        assert "scrape-config-1" in ids or len(ids) == 2
    finally:
        # Scheduler never started → nothing to shut down.
        pass


def test_register_skips_invalid_cron(pg_session, monkeypatch, caplog):
    import logging
    caplog.set_level(logging.WARNING)
    monkeypatch.setattr(
        "app.scheduler.SessionLocal",
        lambda: pg_session.__class__(bind=pg_session.get_bind()),
    )
    _seed_config(pg_session, name="Bad", cron_expression="not a cron")
    _seed_config(pg_session, name="Good")

    scheduler = build_scheduler()
    count = register_scrape_configs(scheduler)
    assert count == 1
    assert any("invalid cron" in rec.message.lower() for rec in caplog.records)


def test_run_config_job_invokes_scraper_service(pg_session, monkeypatch):
    cfg_id = _seed_config(pg_session, name="R")

    called = {"with_id": None}

    def fake_run(db, config):
        called["with_id"] = config.id
        from app.schemas.scrape_config import ScrapeRunResponse

        return ScrapeRunResponse(total_scraped=0, new_jobs=0, duplicates=0, per_source={})

    monkeypatch.setattr("app.scheduler.run_scrape_config", fake_run)
    monkeypatch.setattr(
        "app.scheduler.SessionLocal",
        lambda: pg_session.__class__(bind=pg_session.get_bind()),
    )

    _run_config_job(cfg_id)
    assert called["with_id"] == cfg_id


def test_run_config_job_skips_inactive(pg_session, monkeypatch):
    cfg_id = _seed_config(pg_session, name="Off", is_active=False)

    called = {"n": 0}

    def fake_run(*_a, **_k):
        called["n"] += 1

    monkeypatch.setattr("app.scheduler.run_scrape_config", fake_run)
    monkeypatch.setattr(
        "app.scheduler.SessionLocal",
        lambda: pg_session.__class__(bind=pg_session.get_bind()),
    )

    _run_config_job(cfg_id)
    assert called["n"] == 0  # skipped


def test_scheduler_status_endpoint_empty_when_disabled(pg_session, monkeypatch):
    """/api/scheduler/status returns empty when the scheduler never started."""
    from fastapi.testclient import TestClient

    from app.core.security import create_access_token, hash_password
    from app.database import get_db
    from app.main import app
    from app.models.user import User

    # Reuse the pg_engine-backed session.
    with pg_session.__class__(bind=pg_session.get_bind()) as s:
        s.add(User(email="s@t.local", password_hash=hash_password("x"), name="S"))
        s.commit()
        user = s.query(User).filter_by(email="s@t.local").one()
        token = create_access_token({"sub": str(user.id), "email": user.email})

    SL = pg_session.__class__

    def _db():
        db = SL(bind=pg_session.get_bind())
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    try:
        client = TestClient(app)
        r = client.get(
            "/api/scheduler/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        # No auth gate on scheduler status — matches plan (admin-only app).
        assert r.status_code == 200
        body = r.json()
        assert body["running"] is False
        assert body["jobs"] == []
    finally:
        app.dependency_overrides.clear()
