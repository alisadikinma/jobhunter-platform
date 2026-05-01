"""Master CV upload + URL import tests.

Tests cover:
- file upload happy path (mocked parser)
- invalid file types rejected
- URL import happy path (mocked Firecrawl + parser)
- Firecrawl returns empty markdown -> 502
- auth required
- LLM JSON output with ```json fences gets stripped
"""
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.cv import MasterCV
from app.models.user import User

pytestmark = pytest.mark.integration


def _canned_cv() -> dict:
    return {
        "basics": {
            "name": "Ali Sadikin",
            "email": "ali@example.com",
            "summary_variants": {
                "vibe_coding": "Ships fast.",
                "ai_automation": "Pipelines.",
                "ai_video": "Diffusion.",
            },
        },
        "work": [
            {
                "company": "Acme",
                "position": "Engineer",
                "highlights": [
                    {
                        "text": "Built CI",
                        "tags": ["python"],
                        "relevance_hint": ["ai_automation"],
                    }
                ],
            }
        ],
        "projects": [],
        "education": [],
        "skills": {"langs": ["python"]},
    }


@pytest.fixture
def api(pg_engine, monkeypatch):
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


def test_upload_pdf_creates_master_cv(api, monkeypatch):
    client, SessionLocal = api

    # Avoid running pypdf on a fake file — patch the extractor too.
    monkeypatch.setattr(
        "app.api.cv.extract_text_from_upload",
        lambda b, mt, filename="": "Ali Sadikin\nEngineer at Acme",
    )
    monkeypatch.setattr(
        "app.api.cv.parse_cv_to_json_resume",
        lambda raw: _canned_cv(),
    )

    fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
    resp = client.post(
        "/api/cv/master/upload",
        files={"file": ("resume.pdf", fake_pdf, "application/pdf")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == 1
    assert body["is_active"] is True
    assert body["source_type"] == "upload"
    assert body["content"]["basics"]["name"] == "Ali Sadikin"

    with SessionLocal() as s:
        rows = s.query(MasterCV).all()
        assert len(rows) == 1
        assert rows[0].source_type == "upload"
        assert rows[0].is_active is True


def test_upload_invalid_file_returns_422(api, monkeypatch):
    client, _ = api

    # Even with a bad mime type, the parser should never get called.
    def _fail(*_args, **_kw):
        raise AssertionError("parser must not run on rejected uploads")

    monkeypatch.setattr("app.api.cv.parse_cv_to_json_resume", _fail)

    resp = client.post(
        "/api/cv/master/upload",
        files={"file": ("malware.exe", io.BytesIO(b"MZ\x00"), "application/octet-stream")},
    )
    assert resp.status_code == 422
    assert "file type" in resp.text.lower() or "unsupported" in resp.text.lower()


def test_import_url_success(api, monkeypatch):
    client, SessionLocal = api

    class _FakeFirecrawl:
        def __init__(self, **_kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

        def scrape(self, url, opts=None):
            return {"markdown": "# Ali Sadikin\nPortfolio content", "error": None}

    monkeypatch.setattr("app.api.cv.FirecrawlService", _FakeFirecrawl)
    monkeypatch.setattr(
        "app.api.cv.parse_cv_to_json_resume",
        lambda raw: _canned_cv(),
    )

    resp = client.post(
        "/api/cv/master/import-url",
        json={"url": "https://alisadikinma.com/en"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["version"] == 1
    assert body["source_type"].startswith("url:")
    assert "alisadikinma.com" in body["source_type"]

    with SessionLocal() as s:
        rows = s.query(MasterCV).all()
        assert len(rows) == 1
        assert rows[0].source_type.startswith("url:")


def test_import_url_firecrawl_empty_returns_502(api, monkeypatch):
    client, _ = api

    class _EmptyFirecrawl:
        def __init__(self, **_kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

        def scrape(self, url, opts=None):
            return {"markdown": "", "error": "scrape failed"}

    monkeypatch.setattr("app.api.cv.FirecrawlService", _EmptyFirecrawl)

    resp = client.post(
        "/api/cv/master/import-url",
        json={"url": "https://broken.example.com"},
    )
    assert resp.status_code == 502
    assert "firecrawl" in resp.text.lower() or "scrape" in resp.text.lower()


def test_upload_requires_auth():
    client = TestClient(app)
    resp = client.post(
        "/api/cv/master/upload",
        files={"file": ("r.pdf", io.BytesIO(b"x"), "application/pdf")},
    )
    assert resp.status_code == 401


def test_parse_handles_fenced_json(monkeypatch):
    """parse_cv_to_json_resume must strip ```json … ``` fences if the model adds them."""
    from app.services import cv_parser

    monkeypatch.setattr(cv_parser.settings, "ANTHROPIC_API_KEY", "test-key")

    class _FakeResp:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "```json\n"
                        + '{"basics":{"name":"X","email":"x@x.com","summary_variants":'
                        + '{"vibe_coding":"a","ai_automation":"b","ai_video":"c"}}}'
                        + "\n```",
                    }
                ]
            }

    class _FakeClient:
        def __init__(self, *_a, **_kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return None

        def post(self, *_a, **_kw):
            return _FakeResp()

    monkeypatch.setattr(cv_parser.httpx, "Client", _FakeClient)

    out = cv_parser.parse_cv_to_json_resume("Resume body")
    assert out["basics"]["name"] == "X"
    assert out["basics"]["summary_variants"]["ai_video"] == "c"
