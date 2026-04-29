"""WeWorkRemotely RSS scraper tests."""
import httpx
import respx

from app.scrapers.weworkremotely import WeWorkRemotelyScraper, _CATEGORIES, _BASE


_RSS_PROGRAMMING = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Remote Programming Jobs</title>
    <item>
      <title>Acme: Senior AI Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/acme-senior-ai-engineer</link>
      <description><![CDATA[<p>Build LLM-powered tools. <strong>Python</strong>, FastAPI, claude-code.</p>]]></description>
      <pubDate>Tue, 15 Apr 2026 12:00:00 +0000</pubDate>
      <guid>wwr-acme-1</guid>
    </item>
    <item>
      <title>Beta Co: Mobile Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/beta-co-mobile</link>
      <description><![CDATA[<p>iOS Swift role.</p>]]></description>
      <pubDate>Mon, 14 Apr 2026 09:00:00 +0000</pubDate>
      <guid>wwr-beta-1</guid>
    </item>
  </channel>
</rss>
"""

_RSS_OTHER_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Empty</title></channel></rss>
"""


def _stub_all_categories(programming_body: str = _RSS_PROGRAMMING, other_body: str = _RSS_OTHER_EMPTY):
    """All non-programming categories return the empty feed by default."""
    for cat in _CATEGORIES:
        body = programming_body if cat == "remote-programming-jobs" else other_body
        respx.get(f"{_BASE}/{cat}.rss").mock(return_value=httpx.Response(200, text=body))


@respx.mock
def test_scrape_parses_company_role_titles_and_remote_flag():
    _stub_all_categories()
    with WeWorkRemotelyScraper() as scraper:
        jobs = scraper.scrape(keywords=["ai engineer"])

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "weworkremotely"
    assert job.title == "Senior AI Engineer"
    assert job.company_name == "Acme"
    assert job.remote_type == "remote"
    assert job.location == "Remote"
    assert job.source_url == "https://weworkremotely.com/remote-jobs/acme-senior-ai-engineer"
    assert "Python" in (job.description or "")
    assert "<p>" not in (job.description or "")  # HTML stripped
    assert job.posted_at is not None


@respx.mock
def test_keyword_filter_drops_non_matching_listings():
    _stub_all_categories()
    with WeWorkRemotelyScraper() as scraper:
        # Only "iOS" or "swift" matches — should drop the AI engineer.
        jobs = scraper.scrape(keywords=["swift"])
    assert len(jobs) == 1
    assert jobs[0].title == "Mobile Engineer"


@respx.mock
def test_empty_keywords_returns_all_listings():
    _stub_all_categories()
    with WeWorkRemotelyScraper() as scraper:
        jobs = scraper.scrape(keywords=[])
    assert len(jobs) == 2


@respx.mock
def test_individual_category_failure_doesnt_kill_run():
    # Programming returns 200, design returns 500 — should still return programming jobs.
    respx.get(f"{_BASE}/remote-programming-jobs.rss").mock(
        return_value=httpx.Response(200, text=_RSS_PROGRAMMING)
    )
    respx.get(f"{_BASE}/remote-design-jobs.rss").mock(return_value=httpx.Response(500))
    for cat in _CATEGORIES:
        if cat in ("remote-programming-jobs", "remote-design-jobs"):
            continue
        respx.get(f"{_BASE}/{cat}.rss").mock(return_value=httpx.Response(200, text=_RSS_OTHER_EMPTY))

    with WeWorkRemotelyScraper() as scraper:
        jobs = scraper.scrape(keywords=["ai"])
    assert len(jobs) == 1
    assert jobs[0].title == "Senior AI Engineer"


@respx.mock
def test_malformed_rss_does_not_raise():
    bad_body = "<not-xml>this is broken"
    for cat in _CATEGORIES:
        respx.get(f"{_BASE}/{cat}.rss").mock(return_value=httpx.Response(200, text=bad_body))

    with WeWorkRemotelyScraper() as scraper:
        jobs = scraper.scrape(keywords=["ai"])
    assert jobs == []


@respx.mock
def test_titles_without_colon_fall_back_to_unknown_company():
    body = """<?xml version="1.0"?><rss><channel>
      <item>
        <title>Just A Plain Title</title>
        <link>https://weworkremotely.com/remote-jobs/x</link>
        <description><![CDATA[<p>some description with ai in it</p>]]></description>
        <pubDate>Tue, 15 Apr 2026 12:00:00 +0000</pubDate>
      </item>
    </channel></rss>"""
    for cat in _CATEGORIES:
        if cat == "remote-programming-jobs":
            respx.get(f"{_BASE}/{cat}.rss").mock(return_value=httpx.Response(200, text=body))
        else:
            respx.get(f"{_BASE}/{cat}.rss").mock(return_value=httpx.Response(200, text=_RSS_OTHER_EMPTY))

    with WeWorkRemotelyScraper() as scraper:
        jobs = scraper.scrape(keywords=["ai"])
    assert len(jobs) == 1
    assert jobs[0].company_name == "Unknown"
    assert jobs[0].title == "Just A Plain Title"
