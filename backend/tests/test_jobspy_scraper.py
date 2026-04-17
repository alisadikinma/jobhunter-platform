"""JobSpy scraper tests — inject fake scrape_fn so jobspy isn't actually called."""
from app.scrapers.jobspy_scraper import JobSpyScraper


def _fake_rows(location_token: str) -> list[dict]:
    return [
        {
            "site": "linkedin",
            "title": f"AI Engineer ({location_token})",
            "company": "Acme",
            "location": location_token,
            "description": "Build LLMs",
            "job_url": f"https://linkedin.com/jobs/{location_token}",
            "min_amount": 140000,
            "max_amount": 180000,
            "job_type": "full-time",
            "date_posted": "2026-04-10T00:00:00Z",
        }
    ]


def test_jobspy_fans_out_across_location_variants():
    calls: list[dict] = []

    def fake_scrape(**kwargs):
        calls.append(kwargs)
        return _fake_rows(kwargs["location"])

    scraper = JobSpyScraper(scrape_fn=fake_scrape, sleep_fn=lambda _s: None)
    jobs = scraper.scrape(keywords=["AI"], locations=["USA"], limit=20)

    # USA split has 5 variants -> 5 distinct API calls.
    assert len(calls) == 5
    locations_called = {c["location"] for c in calls}
    assert "San Francisco" in locations_called
    assert "Remote (USA)" in locations_called
    # One job per variant returned, dedup by (title, company) — distinct titles
    # because _fake_rows embeds the location, so all 5 land.
    assert len(jobs) == 5
    assert all(j.source == "jobspy_linkedin" for j in jobs)


def test_jobspy_dedupes_within_run():
    def fake_scrape(**kwargs):
        # Same title/company across every variant -> dedup keeps only 1.
        return [
            {
                "site": "indeed",
                "title": "ML Engineer",
                "company": "Acme",
                "location": kwargs["location"],
                "description": "desc",
                "job_url": "https://example.com/1",
            }
        ]

    scraper = JobSpyScraper(scrape_fn=fake_scrape, sleep_fn=lambda _s: None)
    jobs = scraper.scrape(keywords=["ML"], locations=["USA"], limit=20)
    assert len(jobs) == 1
    assert jobs[0].source == "jobspy_indeed"


def test_jobspy_survives_per_variant_failure():
    call_idx = iter(range(10))

    def fake_scrape(**kwargs):
        i = next(call_idx)
        if i == 1:
            raise RuntimeError("LinkedIn blocked this one")
        return _fake_rows(kwargs["location"])

    scraper = JobSpyScraper(scrape_fn=fake_scrape, sleep_fn=lambda _s: None)
    jobs = scraper.scrape(keywords=["AI"], locations=["USA"], limit=20)
    # 5 variants, one failed -> 4 jobs.
    assert len(jobs) == 4


def test_jobspy_stops_at_limit():
    def fake_scrape(**kwargs):
        # Return 5 jobs per variant.
        return [
            {
                "site": "linkedin",
                "title": f"Role {i}-{kwargs['location']}",
                "company": f"Co-{kwargs['location']}",
                "location": kwargs["location"],
                "job_url": f"https://example.com/{i}-{kwargs['location']}",
            }
            for i in range(5)
        ]

    scraper = JobSpyScraper(scrape_fn=fake_scrape, sleep_fn=lambda _s: None)
    jobs = scraper.scrape(keywords=["x"], locations=["USA"], limit=7)
    assert len(jobs) == 7


def test_jobspy_unknown_location_passthrough():
    captured = []

    def fake_scrape(**kwargs):
        captured.append(kwargs["location"])
        return []

    scraper = JobSpyScraper(scrape_fn=fake_scrape, sleep_fn=lambda _s: None)
    scraper.scrape(keywords=["x"], locations=["Jakarta"], limit=10)
    assert captured == ["Jakarta"]


def test_jobspy_proxy_env_builds_url(monkeypatch):
    from app.config import settings
    from app.scrapers.jobspy_scraper import _build_proxies

    monkeypatch.setattr(settings, "PROXY_URL", "http://proxy.example.com:7777")
    monkeypatch.setattr(settings, "PROXY_USERNAME", "user1")
    monkeypatch.setattr(settings, "PROXY_PASSWORD", "pw1")

    proxies = _build_proxies()
    assert proxies == ["http://user1:pw1@proxy.example.com:7777"]


def test_jobspy_no_proxy_when_unconfigured(monkeypatch):
    from app.config import settings
    from app.scrapers.jobspy_scraper import _build_proxies

    monkeypatch.setattr(settings, "PROXY_URL", "")
    assert _build_proxies() is None
