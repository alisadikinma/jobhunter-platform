"""Mailbox config CRUD + test endpoint."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.mailbox import MailboxConfig
from app.models.user import User
from app.services.encryption import decrypt_token

pytestmark = pytest.mark.integration

_PAYLOAD = {
    "smtp_host": "smtp.example.com",
    "smtp_port": 465,
    "imap_host": "imap.example.com",
    "imap_port": 993,
    "username": "test@example.com",
    "password": "supersecret",
    "from_address": "test@example.com",
    "from_name": "Test User",
    "drafts_folder": "Drafts",
}


@pytest.fixture
def api(pg_engine, monkeypatch):
    monkeypatch.setattr(
        settings, "APIFY_FERNET_KEY", "OwdAUOm691977pZ6oCfdF-HLE64MqP8lgEPNL1k5nss="
    )
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        s.add(User(email="a@t.local", password_hash=hash_password("x"), name="A"))
        s.commit()
        user = s.query(User).filter_by(email="a@t.local").one()
        token = create_access_token({"sub": str(user.id), "email": user.email})

    def _db():
        d = SessionLocal()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _db
    try:
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {token}"})
        yield client, SessionLocal
    finally:
        app.dependency_overrides.clear()


def test_get_returns_empty_stub_when_no_row(api):
    client, _ = api
    r = client.get("/api/mailbox/config")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1
    assert body["username"] == ""
    assert body["password_masked"] == ""
    assert body["is_active"] is False


def test_put_creates_row_and_encrypts_password(api):
    client, SL = api
    r = client.put("/api/mailbox/config", json=_PAYLOAD)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["username"] == "test@example.com"
    assert body["password_masked"] == "********"
    assert body["is_active"] is False  # not active until tested OK

    with SL() as s:
        row = s.get(MailboxConfig, 1)
        # Plaintext password is NOT in DB.
        assert row.password_encrypted != "supersecret"
        # Decrypts back to original.
        assert decrypt_token(row.password_encrypted) == "supersecret"


def test_put_without_password_on_create_is_rejected(api):
    client, _ = api
    payload = {**_PAYLOAD}
    payload.pop("password")
    r = client.put("/api/mailbox/config", json=payload)
    assert r.status_code == 422
    assert "password is required" in r.json()["detail"]


def test_put_without_password_keeps_existing_on_update(api):
    client, SL = api
    # First save: full payload.
    client.put("/api/mailbox/config", json=_PAYLOAD)
    with SL() as s:
        original = s.get(MailboxConfig, 1).password_encrypted

    # Second save: edit metadata, no password — original should be preserved.
    payload2 = {**_PAYLOAD, "from_name": "New Name"}
    payload2.pop("password")
    r = client.put("/api/mailbox/config", json=payload2)
    assert r.status_code == 200
    assert r.json()["from_name"] == "New Name"

    with SL() as s:
        assert s.get(MailboxConfig, 1).password_encrypted == original


def test_put_clears_active_flag_on_edit(api):
    client, SL = api
    client.put("/api/mailbox/config", json=_PAYLOAD)
    with SL() as s:
        row = s.get(MailboxConfig, 1)
        row.is_active = True
        s.commit()

    client.put("/api/mailbox/config", json=_PAYLOAD)
    with SL() as s:
        assert s.get(MailboxConfig, 1).is_active is False


def test_test_endpoint_409_when_no_config(api):
    client, _ = api
    r = client.post("/api/mailbox/test")
    assert r.status_code == 409


def test_test_endpoint_marks_active_on_double_ok(api):
    client, SL = api
    client.put("/api/mailbox/config", json=_PAYLOAD)
    with patch("app.services.mailer_service.test_connection") as fake:
        fake.return_value = (True, True, "IMAP login OK · SMTP login OK")
        r = client.post("/api/mailbox/test")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["imap_ok"] and body["smtp_ok"]
    with SL() as s:
        row = s.get(MailboxConfig, 1)
        assert row.is_active is True
        assert row.last_test_status == "ok"


def test_test_endpoint_keeps_inactive_when_imap_fails(api):
    client, SL = api
    client.put("/api/mailbox/config", json=_PAYLOAD)
    with patch("app.services.mailer_service.test_connection") as fake:
        fake.return_value = (False, True, "IMAP failed: auth · SMTP login OK")
        r = client.post("/api/mailbox/test")
    body = r.json()
    assert body["ok"] is False
    assert body["imap_ok"] is False
    assert body["smtp_ok"] is True
    with SL() as s:
        assert s.get(MailboxConfig, 1).is_active is False


def test_delete_removes_row(api):
    client, SL = api
    client.put("/api/mailbox/config", json=_PAYLOAD)
    r = client.delete("/api/mailbox/config")
    assert r.status_code == 204
    with SL() as s:
        assert s.get(MailboxConfig, 1) is None


def test_unauthenticated_requests_rejected():
    client = TestClient(app)
    assert client.get("/api/mailbox/config").status_code == 401
    assert client.put("/api/mailbox/config", json=_PAYLOAD).status_code == 401
