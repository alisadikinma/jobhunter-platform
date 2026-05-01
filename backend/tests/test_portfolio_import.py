"""Portfolio URL-import API tests — Firecrawl + Anthropic both mocked.

Mocks `extract_portfolio_from_url` directly (the route's only external
seam) so the tests don't need either Firecrawl or the Anthropic API
running. The extractor's own happy-path is verified separately by
exercising its code-fence stripping branch through the same monkeypatch
mechanism (see `test_import_url_strips_code_fences`).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api import portfolio as portfolio_api
from app.core.security import create_access_token, hash_password
from app.database import get_db
from app.main import app
from app.models.portfolio_asset import PortfolioAsset
from app.models.user import User

pytestmark = pytest.mark.integration


@pytest.fixture
def api(pg_engine):
    SessionLocal = sessionmaker(bind=pg_engine, autoflush=False, autocommit=False)
    with SessionLocal() as s:
        s.add(User(email="b@t.local", password_hash=hash_password("x"), name="B"))
        s.commit()
        user = s.query(User).filter_by(email="b@t.local").one()
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


def test_import_url_creates_assets(api, monkeypatch):
    client, SessionLocal = api

    fake_items = [
        {
            "title": "Project Alpha",
            "description": "An AI agent that automates onboarding emails.",
            "url": "https://example.com/alpha",
            "tech_stack": ["Python", "LangChain"],
            "relevance_hint": ["ai_automation"],
            "_source": "url:example.com",
        },
        {
            "title": "Project Beta",
            "description": "A cinematic AI video pipeline.",
            "url": None,
            "tech_stack": ["Veo", "ffmpeg"],
            "relevance_hint": ["ai_video"],
            "_source": "url:example.com",
        },
    ]

    monkeypatch.setattr(
        portfolio_api,
        "extract_portfolio_from_url",
        lambda db, url: fake_items,
    )

    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://example.com/portfolio"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    assert len(body["items"]) == 2

    titles = {item["title"] for item in body["items"]}
    assert titles == {"Project Alpha", "Project Beta"}

    # All imported items go through the draft review flow.
    for item in body["items"]:
        assert item["status"] == "draft"
        assert item["auto_generated"] is True

    with SessionLocal() as s:
        rows = s.query(PortfolioAsset).all()
        assert len(rows) == 2


def test_import_url_empty_firecrawl_returns_502(api, monkeypatch):
    client, _ = api
    from app.services.portfolio_extractor import PortfolioExtractError

    def boom(db, url):
        raise PortfolioExtractError("Firecrawl returned empty content")

    monkeypatch.setattr(portfolio_api, "extract_portfolio_from_url", boom)

    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://example.com/portfolio"},
    )
    assert r.status_code == 502
    assert "Firecrawl" in (r.json().get("detail") or "")


def test_import_url_invalid_llm_json_returns_502(api, monkeypatch):
    client, _ = api
    from app.services.portfolio_extractor import PortfolioExtractError

    def boom(db, url):
        raise PortfolioExtractError("Failed to parse LLM output: invalid JSON")

    monkeypatch.setattr(portfolio_api, "extract_portfolio_from_url", boom)

    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://example.com/portfolio"},
    )
    assert r.status_code == 502
    assert "LLM" in (r.json().get("detail") or "")


def test_import_url_requires_auth():
    client = TestClient(app)
    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://example.com/portfolio"},
    )
    assert r.status_code == 401


def test_import_url_strips_code_fences(api, monkeypatch):
    """Hits the real extractor with mocked Firecrawl + Claude CLI so the
    code-fence-stripping branch in `llm_extractor` is exercised.
    """
    client, SessionLocal = api

    from app.services import portfolio_extractor, llm_extractor
    from app.services.firecrawl_service import FirecrawlService
    from unittest.mock import MagicMock

    # Mock Firecrawl to return non-empty markdown.
    fake_firecrawl = MagicMock(spec=FirecrawlService)
    fake_firecrawl.scrape.return_value = {
        "markdown": "# Portfolio\n\nAn entry.",
        "html": "",
        "title": "Portfolio",
        "description": "",
        "metadata": {},
        "extract": None,
        "error": None,
    }
    fake_firecrawl.__enter__.return_value = fake_firecrawl
    fake_firecrawl.__exit__.return_value = None

    monkeypatch.setattr(
        portfolio_extractor,
        "FirecrawlService",
        lambda db: fake_firecrawl,
    )

    # Mock Claude CLI subprocess to return JSON wrapped in ```json fences.
    fenced_response = (
        "```json\n"
        '{"items": [{"title": "Fenced Project", "description": "x", '
        '"url": null, "tech_stack": ["Go"], "relevance_hint": ["vibe_coding"]}]}\n'
        "```"
    )

    class _FakeRun:
        returncode = 0
        stdout = fenced_response
        stderr = ""

    monkeypatch.setattr(
        llm_extractor.subprocess, "run", lambda *_a, **_kw: _FakeRun()
    )
    monkeypatch.setattr(
        llm_extractor, "_resolve_claude_binary", lambda: "claude"
    )

    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://alisadikinma.com/en"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Fenced Project"
    assert body["items"][0]["status"] == "draft"

    with SessionLocal() as s:
        row = s.query(PortfolioAsset).one()
        assert row.title == "Fenced Project"
        # Tech stack survives the round-trip.
        assert row.tech_stack == ["Go"]
