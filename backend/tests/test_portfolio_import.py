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


def test_import_url_json_fast_path_skips_llm(api, monkeypatch):
    """alisadikinma.com + token set -> Portfolio CV API JSON path,
    Firecrawl+LLM extractor stays untouched, items mapped to assets."""
    client, SessionLocal = api

    # host_supports_api gates on PORTFOLIO_CV_TOKEN — set it in the
    # service module's settings instance directly so the eligibility
    # check returns True for alisadikinma.com.
    monkeypatch.setattr(
        "app.services.portfolio_cv_api.settings.PORTFOLIO_CV_TOKEN",
        "cv-test-token",
    )

    fake_items = [
        {
            "title": "AI Visual Inspection",
            "description": "Industrial QC at the line.",
            "url": "https://alisadikinma.com/projects/ai-visual-inspection",
            "tech_stack": ["Python", "PyTorch"],
            "tags": ["computer_vision", "qc"],
            "metrics": {"deployments": 3},
            "relevance_hint": ["ai_automation"],
            "is_featured": True,
            "_source": "portfolio-api:alisadikinma.com",
        },
        {
            "title": "Sparkfluence",
            "description": "Viral content engine.",
            "url": "https://alisadikinma.com/projects/sparkfluence",
            "tech_stack": ["Next.js"],
            "tags": ["content", "ai"],
            "metrics": None,
            "relevance_hint": ["ai_video"],
            "is_featured": False,
            "_source": "portfolio-api:alisadikinma.com",
        },
    ]
    monkeypatch.setattr(portfolio_api, "fetch_portfolio_projects", lambda: fake_items)

    # Tripwire — if the LLM path runs we want loud failure, not silence.
    def _llm_should_not_run(*a, **kw):
        raise AssertionError(
            "Portfolio JSON fast-path failed — fell through to "
            "extract_portfolio_from_url. Check host_supports_api wiring."
        )

    monkeypatch.setattr(portfolio_api, "extract_portfolio_from_url", _llm_should_not_run)

    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://alisadikinma.com/en"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 2
    assert body["skipped"] == 0

    # Verify the API-specific fields landed correctly.
    items = {it["title"]: it for it in body["items"]}
    ai = items["AI Visual Inspection"]
    assert ai["tags"] == ["computer_vision", "qc"]
    assert ai["is_featured"] is True
    assert ai["display_priority"] == 80  # featured boost
    assert ai["metrics"] == {"deployments": 3, "source": "portfolio-api:alisadikinma.com"}
    assert ai["relevance_hint"] == ["ai_automation"]

    sf = items["Sparkfluence"]
    assert sf["is_featured"] is False
    assert sf["display_priority"] == 50  # default
    assert sf["relevance_hint"] == ["ai_video"]

    with SessionLocal() as s:
        rows = s.query(PortfolioAsset).all()
        assert len(rows) == 2


def test_import_url_json_path_dedups_by_url(api, monkeypatch):
    """Re-running the API import doesn't produce duplicates — items whose
    URL already exists in portfolio_assets are skipped with a clear
    skipped_reasons entry."""
    client, SessionLocal = api

    monkeypatch.setattr(
        "app.services.portfolio_cv_api.settings.PORTFOLIO_CV_TOKEN",
        "cv-test-token",
    )

    fake_items = [
        {
            "title": "Stable Project A",
            "description": "x",
            "url": "https://alisadikinma.com/projects/a",
            "tech_stack": [],
            "tags": [],
            "metrics": None,
            "relevance_hint": ["ai_automation"],
            "is_featured": False,
            "_source": "portfolio-api:alisadikinma.com",
        },
        {
            "title": "Stable Project B",
            "description": "y",
            "url": "https://alisadikinma.com/projects/b",
            "tech_stack": [],
            "tags": [],
            "metrics": None,
            "relevance_hint": [],
            "is_featured": False,
            "_source": "portfolio-api:alisadikinma.com",
        },
    ]
    monkeypatch.setattr(portfolio_api, "fetch_portfolio_projects", lambda: fake_items)

    # First import — clean state, both items inserted.
    r1 = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://alisadikinma.com/en"},
    )
    assert r1.status_code == 200
    assert r1.json()["count"] == 2

    # Second import — same response from API, both should dedup by URL.
    r2 = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://alisadikinma.com/en"},
    )
    assert r2.status_code == 200
    body = r2.json()
    assert body["count"] == 0
    assert body["skipped"] == 2
    assert body["status"] == "partial"
    assert all("duplicate URL" in reason for reason in body["skipped_reasons"])

    with SessionLocal() as s:
        # Still 2 rows total — no balloon, no orphan.
        rows = s.query(PortfolioAsset).all()
        assert len(rows) == 2


def test_import_url_json_path_falls_back_to_llm_on_api_error(api, monkeypatch):
    """If /export fails (network / 1.x schema / etc.), fall back to the
    Firecrawl+LLM path silently. Operator never sees a 502 just because
    the fast-path is unavailable."""
    client, _ = api

    monkeypatch.setattr(
        "app.services.portfolio_cv_api.settings.PORTFOLIO_CV_TOKEN",
        "cv-test-token",
    )

    from app.services.portfolio_cv_api import PortfolioCVApiError

    def _api_fail():
        raise PortfolioCVApiError("schema_version '1.0.0' is unsupported")

    monkeypatch.setattr(portfolio_api, "fetch_portfolio_projects", _api_fail)

    fallback_items = [
        {
            "title": "Fallback Item",
            "description": "Came in via Firecrawl + Claude.",
            "url": None,
            "tech_stack": ["Go"],
            "relevance_hint": ["vibe_coding"],
            "_source": "url:alisadikinma.com",
        }
    ]
    monkeypatch.setattr(
        portfolio_api,
        "extract_portfolio_from_url",
        lambda db, url: fallback_items,
    )

    r = client.post(
        "/api/portfolio/import-url",
        json={"url": "https://alisadikinma.com/en"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["count"] == 1
    assert body["items"][0]["title"] == "Fallback Item"
    # Firecrawl path doesn't set is_featured / boosted priority.
    assert body["items"][0]["is_featured"] is False
    assert body["items"][0]["display_priority"] == 50


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
