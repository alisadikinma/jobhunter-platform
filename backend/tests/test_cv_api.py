"""Master CV CRUD tests — validates the 3-variant schema locks."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.user import User

pytestmark = pytest.mark.integration


def _valid_content() -> dict:
    return {
        "basics": {
            "name": "Ali S.",
            "email": "ali@example.com",
            "summary_variants": {
                "vibe_coding": "Ships fast.",
                "ai_automation": "Pipelines.",
                "ai_video": "Pipelines for video.",
            },
        },
        "work": [
            {
                "company": "Acme",
                "position": "Lead",
                "highlights": [
                    {
                        "text": "Shipped a thing",
                        "tags": ["python", "claude-code"],
                        "relevance_hint": ["vibe_coding", "ai_automation"],
                    }
                ],
            }
        ],
    }


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


def test_get_master_404_when_empty(api):
    assert api.get("/api/cv/master").status_code == 404


def test_put_then_get_returns_active_version(api):
    put = api.put("/api/cv/master", json={"content": _valid_content()})
    assert put.status_code == 200
    assert put.json()["version"] == 1

    got = api.get("/api/cv/master")
    assert got.status_code == 200
    assert got.json()["version"] == 1


def test_put_increments_version_and_deactivates_old(api):
    api.put("/api/cv/master", json={"content": _valid_content()})
    second = api.put("/api/cv/master", json={"content": _valid_content()}).json()
    assert second["version"] == 2
    assert second["is_active"] is True

    got = api.get("/api/cv/master").json()
    assert got["version"] == 2


def test_put_rejects_invalid_relevance_hint(api):
    bad = _valid_content()
    bad["work"][0]["highlights"][0]["relevance_hint"] = ["ai_image"]  # not a real variant
    r = api.put("/api/cv/master", json={"content": bad})
    assert r.status_code == 422
    assert "ai_image" in r.text or "relevance_hint" in r.text


def test_put_rejects_missing_summary_variant(api):
    bad = _valid_content()
    del bad["basics"]["summary_variants"]["ai_video"]
    r = api.put("/api/cv/master", json={"content": bad})
    assert r.status_code == 422


def test_put_rejects_bad_email(api):
    bad = _valid_content()
    bad["basics"]["email"] = "not-an-email"
    r = api.put("/api/cv/master", json={"content": bad})
    assert r.status_code == 422


def test_put_accepts_minimum_valid_content(api):
    minimal = {
        "basics": {
            "name": "X",
            "email": "x@x.com",
            "summary_variants": {
                "vibe_coding": "a", "ai_automation": "b", "ai_video": "c",
            },
        }
    }
    assert api.put("/api/cv/master", json={"content": minimal}).status_code == 200


def test_put_preserves_extra_fields_on_location(api):
    """extra='allow' on LocationModel — future-proofing for stuff like geonameId."""
    content = _valid_content()
    content["basics"]["location"] = {"city": "Jakarta", "country": "ID", "remote": True, "geonameId": 1642911}
    assert api.put("/api/cv/master", json={"content": content}).status_code == 200


def test_get_requires_auth():
    client = TestClient(app)
    assert client.get("/api/cv/master").status_code == 401
