"""Portfolio API tests — CRUD + publish/skip transitions + audit trigger."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
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
        yield client
    finally:
        app.dependency_overrides.clear()


def _create(api, **overrides):
    body = {
        "title": "Sample",
        "url": "https://example.com",
        "description": "desc",
        "tech_stack": ["python"],
        "relevance_hint": ["vibe_coding"],
    }
    body.update(overrides)
    r = api.post("/api/portfolio", json=body)
    return r


def test_list_empty(api):
    r = api.get("/api/portfolio")
    assert r.status_code == 200
    assert r.json() == []


def test_create_asset_is_published_by_default(api):
    r = _create(api)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "published"
    assert body["auto_generated"] is False


def test_list_filter_by_status(api):
    _create(api, title="P1")
    _create(api, title="P2")

    all_r = api.get("/api/portfolio").json()
    pub = api.get("/api/portfolio?status_filter=published").json()
    assert len(all_r) == 2
    assert len(pub) == 2


def test_patch_updates_fields(api):
    created = _create(api).json()
    r = api.patch(
        f"/api/portfolio/{created['id']}",
        json={"title": "Renamed", "display_priority": 99},
    )
    body = r.json()
    assert body["title"] == "Renamed"
    assert body["display_priority"] == 99


def test_patch_rejects_invalid_relevance_hint(api):
    created = _create(api).json()
    r = api.patch(
        f"/api/portfolio/{created['id']}",
        json={"relevance_hint": ["ai_image"]},
    )
    assert r.status_code == 422


def test_publish_and_skip_transitions_status(api, pg_engine):
    # Seed a draft directly.
    from sqlalchemy.orm import Session

    from app.models.portfolio_asset import PortfolioAsset

    with Session(pg_engine) as s:
        row = PortfolioAsset(title="Draft", status="draft", auto_generated=True)
        s.add(row)
        s.commit()
        aid = row.id

    pub = api.post(f"/api/portfolio/{aid}/publish").json()
    assert pub["status"] == "published"
    assert pub["reviewed_at"] is not None

    skip = api.post(f"/api/portfolio/{aid}/skip").json()
    assert skip["status"] == "skipped"


def test_publish_404_for_missing(api):
    assert api.post("/api/portfolio/99999/publish").status_code == 404


def test_delete_removes_asset(api):
    created = _create(api).json()
    assert api.delete(f"/api/portfolio/{created['id']}").status_code == 204
    assert api.get("/api/portfolio").json() == []


def test_audit_with_custom_scan_path(api, tmp_path):
    (tmp_path / "example-plugin").mkdir()
    (tmp_path / "example-plugin" / "CLAUDE.md").write_text(
        "# Example Plugin\n\nClaude CLI automation tool.\n", encoding="utf-8"
    )

    r = api.post("/api/portfolio/audit", json={"scan_paths": [str(tmp_path)]})
    assert r.status_code == 200
    body = r.json()
    assert body["new_drafts"] == 1

    listed = api.get("/api/portfolio?status_filter=draft").json()
    assert any(a["title"] == "Example Plugin" for a in listed)


def test_list_requires_auth():
    client = TestClient(app)
    assert client.get("/api/portfolio").status_code == 401
