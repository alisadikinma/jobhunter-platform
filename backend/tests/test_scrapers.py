"""Unit tests for each scraper. HTTP calls mocked via respx."""
import httpx
import pytest
import respx

from app.scrapers.adzuna import AdzunaScraper
from app.scrapers.arbeitnow import ArbeitnowScraper
from app.scrapers.base import ScraperDisabled
from app.scrapers.hiring_cafe import HiringCafeScraper
from app.scrapers.hn_algolia import HnAlgoliaScraper
from app.scrapers.remoteok import RemoteOKScraper

# ---- RemoteOK ----

REMOTEOK_SAMPLE = [
    {"legal": "header — ignored"},
    {
        "id": "rok-1",
        "position": "Senior AI Engineer",
        "company": "Acme AI",
        "description": "Build LLM pipelines",
        "url": "https://remoteok.com/remote-jobs/rok-1",
        "location": "Remote",
        "tags": ["python", "llm"],
        "salary_min": 140000,
        "salary_max": 180000,
        "date": "2026-04-10T12:00:00Z",
    },
    {
        "id": "rok-2",
        "position": "Frontend Developer",
        "company": "Beta",
        "description": "React + Tailwind",
        "url": "https://remoteok.com/remote-jobs/rok-2",
        "tags": ["react", "frontend"],
    },
]


@respx.mock
def test_remoteok_filters_by_keyword_and_normalizes():
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=REMOTEOK_SAMPLE)
    )
    jobs = RemoteOKScraper().scrape(keywords=["llm"])
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "remoteok"
    assert job.external_id == "rok-1"
    assert job.title == "Senior AI Engineer"
    assert job.company_name == "Acme AI"
    assert job.salary_min == 140000
    assert "python" in job.tech_stack
    assert job.posted_at is not None


@respx.mock
def test_remoteok_empty_keywords_returns_all():
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=REMOTEOK_SAMPLE)
    )
    jobs = RemoteOKScraper().scrape(keywords=[])
    assert len(jobs) == 2


@respx.mock
def test_remoteok_respects_limit():
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=REMOTEOK_SAMPLE)
    )
    jobs = RemoteOKScraper().scrape(keywords=[], limit=1)
    assert len(jobs) == 1


# ---- HN Algolia ----

HN_WHOSHIRING_STORY = {
    "hits": [
        {"objectID": "42424242", "title": "Ask HN: Who is hiring? (April 2026)"},
    ]
}

HN_COMMENTS = {
    "hits": [
        {
            "objectID": "c1",
            "comment_text": (
                "Acme | Senior Engineer | REMOTE (US)\n\n"
                "We build developer tooling. Python, FastAPI, Postgres. "
                "Send resume to jobs@acme.example."
            ),
            "created_at": "2026-04-10T12:34:56Z",
        },
        {
            "objectID": "c2",
            "comment_text": "too short",  # filtered out by length
        },
    ]
}


@respx.mock
def test_hn_algolia_finds_latest_thread_and_scrapes_comments():
    base = "https://hn.algolia.com/api/v1/search_by_date"
    respx.get(url__startswith=base).mock(
        side_effect=[
            httpx.Response(200, json=HN_WHOSHIRING_STORY),
            httpx.Response(200, json=HN_COMMENTS),
        ]
    )

    jobs = HnAlgoliaScraper().scrape(keywords=["python"])
    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "hn_algolia"
    assert job.external_id == "c1"
    assert "Acme" in job.company_name
    assert "Engineer" in job.title
    assert job.remote_type == "remote"


@respx.mock
def test_hn_algolia_returns_empty_if_no_whoshiring_thread():
    respx.get("https://hn.algolia.com/api/v1/search_by_date").mock(
        return_value=httpx.Response(200, json={"hits": []})
    )
    jobs = HnAlgoliaScraper().scrape(keywords=["python"])
    assert jobs == []


# ---- Arbeitnow ----

ARBEITNOW_SAMPLE = {
    "data": [
        {
            "slug": "an-1",
            "title": "AI Engineer",
            "company_name": "Gamma",
            "description": "Build RAG pipelines",
            "url": "https://arbeitnow.com/jobs/an-1",
            "remote": True,
            "location": "Berlin",
            "tags": ["python", "ai"],
            "job_types": ["full-time"],
            "created_at": 1744280400,
        },
        {
            "slug": "an-2",
            "title": "Marketing Manager",
            "company_name": "Delta",
            "description": "Growth marketing",
            "url": "https://arbeitnow.com/jobs/an-2",
            "tags": ["marketing"],
        },
    ]
}


@respx.mock
def test_arbeitnow_keyword_filter_and_remote_flag():
    respx.get("https://arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json=ARBEITNOW_SAMPLE)
    )
    jobs = ArbeitnowScraper().scrape(keywords=["ai"])
    assert len(jobs) == 1
    assert jobs[0].remote_type == "remote"
    assert jobs[0].job_type == "full-time"


# ---- Adzuna ----

ADZUNA_SAMPLE = {
    "results": [
        {
            "id": 999,
            "title": "Staff AI Engineer",
            "company": {"display_name": "Epsilon"},
            "location": {"display_name": "New York, NY"},
            "description": "Lead AI initiatives",
            "redirect_url": "https://adzuna.com/land/ad/999",
            "salary_min": 200000,
            "salary_max": 260000,
            "contract_type": "permanent",
            "created": "2026-04-12T09:00:00Z",
        }
    ]
}


@respx.mock
def test_adzuna_raises_when_creds_missing(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(settings, "ADZUNA_APP_KEY", "")
    with pytest.raises(ScraperDisabled, match="ADZUNA_APP_ID"):
        AdzunaScraper().scrape(keywords=["engineer"])


@respx.mock
def test_adzuna_calls_api_with_creds(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "test-id")
    monkeypatch.setattr(settings, "ADZUNA_APP_KEY", "test-key")
    respx.get(url__regex=r"https://api\.adzuna\.com/v1/api/jobs/us/search/1.*").mock(
        return_value=httpx.Response(200, json=ADZUNA_SAMPLE)
    )
    jobs = AdzunaScraper().scrape(keywords=["AI Engineer"])
    assert len(jobs) == 1
    assert jobs[0].company_name == "Epsilon"
    assert jobs[0].salary_min == 200000


def test_adzuna_pick_country_infers_uk():
    from app.scrapers.adzuna import _pick_country

    assert _pick_country(["London"]) == "gb"
    assert _pick_country(["Sydney"]) == "au"
    assert _pick_country(["USA Remote"]) == "us"
    assert _pick_country(None) == "us"


# ---- HiringCafe ----

HIRING_CAFE_SAMPLE = {
    "results": [
        {
            "id": "hc-1",
            "job_title": "ML Engineer",
            "company_name": "Zeta",
            "description": "Train LLMs",
            "apply_url": "https://hiring.cafe/jobs/hc-1",
            "location": "Remote",
            "tags": ["ml", "python"],
            "posted_at": "2026-04-11T00:00:00Z",
        }
    ]
}


@respx.mock
def test_hiring_cafe_parses_success_response():
    respx.post("https://hiring.cafe/api/search-jobs").mock(
        return_value=httpx.Response(200, json=HIRING_CAFE_SAMPLE)
    )
    jobs = HiringCafeScraper().scrape(keywords=["ml"])
    assert len(jobs) == 1
    assert jobs[0].source == "hiring_cafe"
    assert jobs[0].external_id == "hc-1"


@respx.mock
def test_hiring_cafe_returns_empty_on_http_error():
    respx.post("https://hiring.cafe/api/search-jobs").mock(
        return_value=httpx.Response(503)
    )
    jobs = HiringCafeScraper().scrape(keywords=["ml"])
    assert jobs == []


@respx.mock
def test_hiring_cafe_returns_empty_on_malformed_body():
    respx.post("https://hiring.cafe/api/search-jobs").mock(
        return_value=httpx.Response(200, text="not json")
    )
    jobs = HiringCafeScraper().scrape(keywords=["ml"])
    assert jobs == []
