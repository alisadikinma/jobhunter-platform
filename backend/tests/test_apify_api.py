"""Apify admin API tests — real Postgres + auth + token masking."""
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.user import User

pytestmark = pytest.mark.integration


@pytest.fixture
def api_client(pg_engine, monkeypatch):
    """TestClient wired to the pytest-postgresql DB + seeded admin user."""
    monkeypatch.setattr(settings, "APIFY_FERNET_KEY", Fernet.generate_key().decode())

    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as seed:
        seed.add(User(email="admin@test.local", password_hash=hash_password("x"), name="A"))
        seed.commit()
        admin = seed.query(User).filter_by(email="admin@test.local").one()
        token = create_access_token({"sub": str(admin.id), "email": admin.email})

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client
    finally:
        app.dependency_overrides.clear()


def test_list_accounts_empty_returns_200(api_client):
    r = api_client.get("/api/apify/accounts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_accounts_requires_auth():
    client = TestClient(app)  # no auth header
    r = client.get("/api/apify/accounts")
    assert r.status_code == 401


def test_create_account_encrypts_token_and_masks_response(api_client, pg_engine):
    r = api_client.post(
        "/api/apify/accounts",
        json={
            "label": "apify01",
            "email": "a@b.com",
            "api_token": "apify_real_token_abcdef9999",
            "priority": 50,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["label"] == "apify01"
    assert body["token_masked"].endswith("9999")
    assert "apify_real_token" not in body["token_masked"]
    assert body["status"] == "active"

    # Verify at the DB level that the stored token is ciphertext, not plain.
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from app.models.apify_account import ApifyAccount

    with Session(pg_engine) as session:
        stored = session.execute(select(ApifyAccount.api_token)).scalar_one()
        assert stored != "apify_real_token_abcdef9999"
        assert "apify_real_token" not in stored


def test_bulk_create_parses_csv_lines(api_client):
    r = api_client.post(
        "/api/apify/accounts/bulk",
        json={
            "lines": [
                "apify02,a2@x.com,token2",
                "apify03,a3@x.com,token3",
            ]
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert len(body) == 2
    assert {a["label"] for a in body} == {"apify02", "apify03"}


def test_bulk_create_rejects_malformed_line(api_client):
    r = api_client.post(
        "/api/apify/accounts/bulk",
        json={"lines": ["only,two"]},
    )
    assert r.status_code == 422


def test_patch_updates_priority_and_status(api_client):
    created = api_client.post(
        "/api/apify/accounts",
        json={"label": "p1", "email": "p1@x.com", "api_token": "tok"},
    ).json()

    r = api_client.patch(
        f"/api/apify/accounts/{created['id']}",
        json={"priority": 10, "status": "suspended"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["priority"] == 10
    assert body["status"] == "suspended"


def test_delete_removes_account(api_client):
    created = api_client.post(
        "/api/apify/accounts",
        json={"label": "d1", "email": "d1@x.com", "api_token": "tok"},
    ).json()

    r = api_client.delete(f"/api/apify/accounts/{created['id']}")
    assert r.status_code == 204

    r2 = api_client.get("/api/apify/accounts")
    assert all(a["id"] != created["id"] for a in r2.json())


def test_delete_missing_returns_404(api_client):
    assert api_client.delete("/api/apify/accounts/99999").status_code == 404


def test_test_connection_returns_success_on_valid_token(api_client):
    created = api_client.post(
        "/api/apify/accounts",
        json={"label": "t1", "email": "t1@x.com", "api_token": "good"},
    ).json()

    with patch("app.api.apify.ApifyClient") as mock_cls:
        mock_user = MagicMock()
        mock_user.get.return_value = {"username": "alice"}
        mock_cls.return_value.user.return_value = mock_user

        r = api_client.post(f"/api/apify/accounts/{created['id']}/test")

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "alice" in body["message"]


def test_test_connection_returns_failure_on_exception(api_client):
    created = api_client.post(
        "/api/apify/accounts",
        json={"label": "t2", "email": "t2@x.com", "api_token": "bad"},
    ).json()

    with patch("app.api.apify.ApifyClient") as mock_cls:
        mock_cls.return_value.user.side_effect = RuntimeError("401 Unauthorized")

        r = api_client.post(f"/api/apify/accounts/{created['id']}/test")

    body = r.json()
    assert body["ok"] is False
    assert "Unauthorized" in body["message"]
