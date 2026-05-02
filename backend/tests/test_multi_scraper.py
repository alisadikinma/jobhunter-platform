"""Tests for parallel multi-page Firecrawl scraper.

The helper takes a list of URLs, scrapes them in parallel via FirecrawlService,
and returns a single concatenated markdown string with section delimiters.
Failed/empty pages are skipped (warn-and-continue); only when ALL fail does
it raise MultiScrapeError.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest


def test_scrape_multiple_pages_concatenates_with_delimiters():
    """Happy path: 3 URLs all return markdown -> joined with === Page: <url> === separators."""
    from app.services import multi_scraper
    from app.services.multi_scraper import scrape_multiple_pages

    fake_results = {
        "https://example.com/a": {"markdown": "# A content", "error": None},
        "https://example.com/b": {"markdown": "# B content", "error": None},
        "https://example.com/c": {"markdown": "# C content", "error": None},
    }

    class _FakeFirecrawl:
        def __init__(self, db=None):
            self.db = db
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def scrape(self, url, opts=None):
            return fake_results[url]

    # Patch FirecrawlService used inside the module.
    multi_scraper.FirecrawlService = _FakeFirecrawl

    urls = list(fake_results.keys())
    out = scrape_multiple_pages(urls, db=MagicMock())

    # Each URL's markdown appears, in input order, with the delimiter line.
    for url in urls:
        assert f"=== Page: {url} ===" in out
        assert fake_results[url]["markdown"] in out
    # Order is preserved.
    pos_a = out.index("# A content")
    pos_b = out.index("# B content")
    pos_c = out.index("# C content")
    assert pos_a < pos_b < pos_c


def test_scrape_multiple_pages_skips_failures(caplog):
    """One URL fails -> the other two still produce output, helper logs warning."""
    import logging
    from app.services import multi_scraper
    from app.services.multi_scraper import scrape_multiple_pages

    results = {
        "https://example.com/ok1": {"markdown": "good 1", "error": None},
        "https://example.com/bad": {"markdown": "", "error": "scrape failed"},
        "https://example.com/ok2": {"markdown": "good 2", "error": None},
    }

    class _FakeFirecrawl:
        def __init__(self, db=None): pass
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def scrape(self, url, opts=None):
            return results[url]

    multi_scraper.FirecrawlService = _FakeFirecrawl

    with caplog.at_level(logging.WARNING, logger="app.services.multi_scraper"):
        out = scrape_multiple_pages(list(results.keys()), db=MagicMock())

    assert "good 1" in out
    assert "good 2" in out
    assert "https://example.com/bad" not in out  # delimiter for the failed URL skipped
    assert any("https://example.com/bad" in rec.message for rec in caplog.records)


def test_scrape_multiple_pages_all_fail_raises():
    """All URLs fail -> raise MultiScrapeError so the caller can surface 502."""
    from app.services import multi_scraper
    from app.services.multi_scraper import MultiScrapeError, scrape_multiple_pages

    class _FakeFirecrawl:
        def __init__(self, db=None): pass
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def scrape(self, url, opts=None):
            return {"markdown": "", "error": "everything broken"}

    multi_scraper.FirecrawlService = _FakeFirecrawl

    with pytest.raises(MultiScrapeError):
        scrape_multiple_pages(
            ["https://x.test/1", "https://x.test/2"], db=MagicMock()
        )


def test_derive_portfolio_urls_returns_4_urls_in_order():
    """alisadikinma.com/en -> [base, /about, /work?tab=awards, /work?tab=projects]."""
    from app.services.multi_scraper import derive_portfolio_urls

    out = derive_portfolio_urls("https://alisadikinma.com/en")
    assert out == [
        "https://alisadikinma.com/en",
        "https://alisadikinma.com/en/about",
        "https://alisadikinma.com/en/work?tab=awards",
        "https://alisadikinma.com/en/work?tab=projects",
    ]


def test_derive_portfolio_urls_strips_trailing_slash():
    from app.services.multi_scraper import derive_portfolio_urls

    out = derive_portfolio_urls("https://alisadikinma.com/en/")
    assert out[0] == "https://alisadikinma.com/en"
    assert out[1] == "https://alisadikinma.com/en/about"


def test_derive_portfolio_urls_bare_domain():
    """Domain with no path still produces 4 URLs."""
    from app.services.multi_scraper import derive_portfolio_urls

    out = derive_portfolio_urls("https://example.com")
    assert out == [
        "https://example.com",
        "https://example.com/about",
        "https://example.com/work?tab=awards",
        "https://example.com/work?tab=projects",
    ]


def test_scrape_multiple_pages_uses_per_worker_session(monkeypatch):
    """Each worker must open its own SessionLocal to avoid the cross-thread
    'Session is already flushing' race that broke production scrapes.
    Verified by counting `SessionLocal()` calls during the run.
    """
    from app.services import multi_scraper
    from app.services.multi_scraper import scrape_multiple_pages

    session_calls = {"count": 0}

    class _SessionStub:
        def __enter__(self): return self
        def __exit__(self, *a): return None

    def _fake_session_local():
        session_calls["count"] += 1
        return _SessionStub()

    monkeypatch.setattr(multi_scraper, "SessionLocal", _fake_session_local)

    class _FirecrawlStub:
        def __init__(self, db=None): pass
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def scrape(self, url, opts=None):
            return {"markdown": f"page {url}", "error": None}

    monkeypatch.setattr(multi_scraper, "FirecrawlService", _FirecrawlStub)

    urls = [f"https://example.com/{i}" for i in range(4)]
    scrape_multiple_pages(urls, db=MagicMock())

    # One SessionLocal() call per worker.
    assert session_calls["count"] == 4


def test_scrape_multiple_pages_runs_in_parallel():
    """Wall time must be <2x of one scrape's latency (proves ThreadPoolExecutor not sequential)."""
    from app.services import multi_scraper
    from app.services.multi_scraper import scrape_multiple_pages

    SCRAPE_LATENCY_S = 0.4
    URLS = [f"https://example.com/{i}" for i in range(4)]

    class _SlowFirecrawl:
        def __init__(self, db=None): pass
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def scrape(self, url, opts=None):
            time.sleep(SCRAPE_LATENCY_S)
            return {"markdown": f"page {url}", "error": None}

    multi_scraper.FirecrawlService = _SlowFirecrawl

    t0 = time.monotonic()
    out = scrape_multiple_pages(URLS, db=MagicMock())
    elapsed = time.monotonic() - t0

    # Sequential would be ~1.6s (4*0.4). Parallel should be ~0.4-0.6s.
    # Use < 2× single-scrape as a generous threshold robust to CI jitter.
    assert elapsed < SCRAPE_LATENCY_S * 2.0, f"parallel should be fast; got {elapsed:.2f}s"
    # All 4 pages still represented.
    for url in URLS:
        assert url in out
