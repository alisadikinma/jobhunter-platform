"""AIJobs (aijobs.net + aicareers.io) HTML scraper tests."""
import httpx
import respx

from app.scrapers.aijobs import AIJobsScraper


_AIJOBS_HTML = """
<html><body>
<ul>
  <li class="list-group-item">
    <a href="/job/123/senior-ai-engineer">
      <h4>Senior AI Engineer</h4>
      <small class="company">Acme AI</small>
      <span class="location">Remote · USA</span>
      <time datetime="2026-04-20T10:00:00Z">Apr 20</time>
      <span class="badge">Python</span>
      <span class="badge">LangChain</span>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/job/456/ml-platform">
      <h4>ML Platform Engineer</h4>
      <small class="company">Beta Labs</small>
      <span class="badge">Kubernetes</span>
    </a>
  </li>
  <li class="list-group-item">
    <a href="/job/789/recruiter">
      <h4>Talent Sourcer</h4>
      <small class="company">Gamma</small>
    </a>
  </li>
</ul>
</body></html>
"""

_AICAREERS_HTML = """
<html><body>
<article class="job">
  <a href="/jobs/aiops-lead">
    <h3>AI Ops Lead</h3>
    <span class="company">Delta Tech</span>
    <span class="location">Remote · EU</span>
  </a>
</article>
</body></html>
"""

_EMPTY_HTML = "<html><body><p>nothing here</p></body></html>"


@respx.mock
def test_scrape_extracts_jobs_from_both_boards():
    respx.get("https://aijobs.net/").mock(return_value=httpx.Response(200, text=_AIJOBS_HTML))
    respx.get("https://aicareers.io/").mock(return_value=httpx.Response(200, text=_AICAREERS_HTML))

    with AIJobsScraper() as scraper:
        jobs = scraper.scrape(keywords=[])  # no filter — return all

    titles = [j.title for j in jobs]
    sources = [j.source for j in jobs]
    assert "Senior AI Engineer" in titles
    assert "ML Platform Engineer" in titles
    assert "Talent Sourcer" in titles
    assert "AI Ops Lead" in titles
    # Source prefix tags both boards distinctly.
    assert "aijobs:aijobs.net" in sources
    assert "aijobs:aicareers.io" in sources


@respx.mock
def test_keyword_filter_matches_against_title_company_tech_stack():
    respx.get("https://aijobs.net/").mock(return_value=httpx.Response(200, text=_AIJOBS_HTML))
    respx.get("https://aicareers.io/").mock(return_value=httpx.Response(200, text=_EMPTY_HTML))

    with AIJobsScraper() as scraper:
        jobs = scraper.scrape(keywords=["langchain"])
    assert len(jobs) == 1
    assert jobs[0].title == "Senior AI Engineer"
    assert "LangChain" in jobs[0].tech_stack


@respx.mock
def test_company_falls_back_to_unknown_when_no_company_element():
    body = """<html><body>
      <a href="/job/x"><h4>Mystery Role</h4></a>
    </body></html>"""
    respx.get("https://aijobs.net/").mock(return_value=httpx.Response(200, text=body))
    respx.get("https://aicareers.io/").mock(return_value=httpx.Response(200, text=_EMPTY_HTML))

    with AIJobsScraper() as scraper:
        jobs = scraper.scrape(keywords=[])
    assert len(jobs) == 1
    assert jobs[0].company_name == "Unknown"


@respx.mock
def test_one_board_failing_does_not_break_the_other():
    respx.get("https://aijobs.net/").mock(return_value=httpx.Response(500))
    respx.get("https://aicareers.io/").mock(return_value=httpx.Response(200, text=_AICAREERS_HTML))

    with AIJobsScraper() as scraper:
        jobs = scraper.scrape(keywords=[])
    assert len(jobs) == 1
    assert jobs[0].title == "AI Ops Lead"


@respx.mock
def test_zero_cards_yields_empty_list_no_exception():
    respx.get("https://aijobs.net/").mock(return_value=httpx.Response(200, text=_EMPTY_HTML))
    respx.get("https://aicareers.io/").mock(return_value=httpx.Response(200, text=_EMPTY_HTML))

    with AIJobsScraper() as scraper:
        jobs = scraper.scrape(keywords=[])
    assert jobs == []


@respx.mock
def test_dedup_within_run_by_source_url():
    # Same job listed twice → only emitted once.
    body = """<html><body>
      <li class="list-group-item">
        <a href="/job/dup-1"><h4>Dup Role</h4><small class="company">X</small></a>
      </li>
      <li class="list-group-item">
        <a href="/job/dup-1"><h4>Dup Role</h4><small class="company">X</small></a>
      </li>
    </body></html>"""
    respx.get("https://aijobs.net/").mock(return_value=httpx.Response(200, text=body))
    respx.get("https://aicareers.io/").mock(return_value=httpx.Response(200, text=_EMPTY_HTML))

    with AIJobsScraper() as scraper:
        jobs = scraper.scrape(keywords=[])
    assert len(jobs) == 1
