import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.database import get_db
from app.main import app
from app.models.user import User


@pytest.fixture
def auth_client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    User.__table__.create(engine)

    session = TestingSession()
    session.add(User(email="admin@example.com", password_hash=hash_password("secret123"), name="Admin"))
    session.commit()
    session.close()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_login_returns_jwt_for_valid_credentials(auth_client):
    response = auth_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert len(body["access_token"]) > 0


def test_login_returns_401_for_invalid_credentials(auth_client):
    response = auth_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_login_returns_401_for_unknown_email(auth_client):
    response = auth_client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "secret123"})
    assert response.status_code == 401


def test_me_returns_user_with_valid_jwt(auth_client):
    login = auth_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "admin@example.com"
    assert body["name"] == "Admin"
    assert "id" in body


def test_me_returns_401_without_jwt(auth_client):
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_401_with_invalid_jwt(auth_client):
    response = auth_client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_refresh_returns_new_token_for_valid_jwt(auth_client):
    login = auth_client.post("/api/auth/login", json={"email": "admin@example.com", "password": "secret123"})
    token = login.json()["access_token"]

    response = auth_client.post("/api/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json()["access_token"], str)
