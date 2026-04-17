"""Aggregator tests — orchestration + dedup + resilience."""
import httpx
import respx

from app.scrapers.aggregator import aggregate

_RO_LISTINGS = [
    {"legal": "header"},
    {
        "id": "r1",
        "position": "AI Engineer",
        "company": "Acme",
        "description": "Build LLMs",
        "url": "https://remoteok.com/r1",
        "tags": ["ai"],
    },
]

_AN_LISTINGS = {
    "data": [
        {
            "slug": "a1",
            "title": "AI Engineer",
            "company_name": "Acme",
            "description": "Build LLMs",
            "url": "https://arbeitnow.com/a1",
            "remote": True,
            "tags": ["ai"],
        },
        {
            "slug": "a2",
            "title": "AI Ops Engineer",
            "company_name": "Beta",
            "description": "AI platform work",
            "url": "https://arbeitnow.com/a2",
            "remote": True,
        },
    ]
}


@respx.mock
def test_aggregate_dedups_across_sources():
    # RemoteOK and Arbeitnow return the same (title, company, desc prefix)
    # — dedup by content_hash should keep only the first.
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(200, json=_RO_LISTINGS))
    respx.get("https://arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json=_AN_LISTINGS)
    )

    jobs = aggregate(keywords=["ai"], sources=["remoteok", "arbeitnow"])
    titles_companies = [(j.title, j.company_name) for j in jobs]

    # "AI Engineer @ Acme" appears twice in input, once in output.
    assert titles_companies.count(("AI Engineer", "Acme")) == 1
    assert ("AI Ops Engineer", "Beta") in titles_companies
    assert len(jobs) == 2


@respx.mock
def test_aggregate_skips_failing_source_without_aborting_batch():
    respx.get("https://remoteok.com/api").mock(return_value=httpx.Response(500))
    respx.get("https://arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json=_AN_LISTINGS)
    )

    jobs = aggregate(keywords=["ai"], sources=["remoteok", "arbeitnow"])
    # RemoteOK failed but Arbeitnow jobs still come through.
    assert any(j.source == "arbeitnow" for j in jobs)
    assert not any(j.source == "remoteok" for j in jobs)


@respx.mock
def test_aggregate_skips_unknown_source():
    respx.get("https://arbeitnow.com/api/job-board-api").mock(
        return_value=httpx.Response(200, json=_AN_LISTINGS)
    )

    jobs = aggregate(keywords=["ai"], sources=["not_a_real_source", "arbeitnow"])
    assert len(jobs) >= 1
    assert all(j.source == "arbeitnow" for j in jobs)


def test_registry_includes_jobspy():
    """Regression: Phase 22 review caught jobspy missing — migration 004
    seeds 'jobspy' as a source, so aggregate() must recognise it."""
    from app.scrapers.aggregator import APIFY_GATED_SOURCES, SCRAPER_REGISTRY
    from app.scrapers.jobspy_scraper import JobSpyScraper

    assert SCRAPER_REGISTRY["jobspy"] is JobSpyScraper
    # Apify-gated sources live outside the free registry — they need the pool.
    assert "wellfound" in APIFY_GATED_SOURCES
    assert "linkedin_apify" in APIFY_GATED_SOURCES
    assert "wellfound" not in SCRAPER_REGISTRY


@respx.mock
def test_aggregate_skips_disabled_scraper_gracefully(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "ADZUNA_APP_ID", "")
    monkeypatch.setattr(settings, "ADZUNA_APP_KEY", "")
    respx.get("https://remoteok.com/api").mock(
        return_value=httpx.Response(200, json=_RO_LISTINGS)
    )

    # Adzuna is disabled → should be skipped, not crash the batch.
    jobs = aggregate(keywords=["ai"], sources=["adzuna", "remoteok"])
    assert any(j.source == "remoteok" for j in jobs)
