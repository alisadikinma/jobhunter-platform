"""Apify scraper tests — mock the ApifyClient instead of hitting real Apify."""
from unittest.mock import MagicMock

import pytest
from cryptography.fernet import Fernet

from app.config import settings
from app.scrapers.base import ScraperDisabled
from app.scrapers.linkedin_apify import LinkedInApifyScraper
from app.scrapers.wellfound_apify import WellfoundApifyScraper
from app.services.encryption import encrypt_token


@pytest.fixture
def _fernet_key(monkeypatch):
    monkeypatch.setattr(settings, "APIFY_FERNET_KEY", Fernet.generate_key().decode())


def _fake_apify_client(items: list[dict]) -> MagicMock:
    """Build a MagicMock that mimics ApifyClient().actor().call() + dataset().list_items()."""
    mock_dataset = MagicMock()
    mock_dataset.list_items.return_value = MagicMock(items=items)

    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds-1"}
    mock_client.dataset.return_value = mock_dataset

    factory = MagicMock(return_value=mock_client)
    return factory


def test_wellfound_normalizes_actor_output(_fernet_key):
    items = [
        {
            "id": "wf-1",
            "jobTitle": "Founding AI Engineer",
            "companyName": "Gamma AI",
            "location": "Remote (US)",
            "description": "Build the thing",
            "salaryMin": 150000,
            "salaryMax": 200000,
            "url": "https://wellfound.com/jobs/wf-1",
            "skills": ["python", "llm"],
            "remote": True,
        }
    ]
    factory = _fake_apify_client(items)
    encrypted = encrypt_token("apify-token")

    scraper = WellfoundApifyScraper(encrypted, client_factory=factory)
    jobs = scraper.scrape(keywords=["AI Engineer"])

    assert len(jobs) == 1
    job = jobs[0]
    assert job.source == "wellfound"
    assert job.external_id == "wf-1"
    assert job.title == "Founding AI Engineer"
    assert job.company_name == "Gamma AI"
    assert job.salary_min == 150000
    assert "python" in job.tech_stack
    assert job.remote_type == "remote"


def test_wellfound_returns_empty_when_run_has_no_dataset(_fernet_key):
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = {}  # no defaultDatasetId
    factory = MagicMock(return_value=mock_client)

    scraper = WellfoundApifyScraper(encrypt_token("t"), client_factory=factory)
    assert scraper.scrape(keywords=["x"]) == []


def test_linkedin_apify_disabled_by_default(_fernet_key, monkeypatch):
    monkeypatch.setattr(settings, "APIFY_LINKEDIN_ENABLED", False)
    with pytest.raises(ScraperDisabled, match="APIFY_LINKEDIN_ENABLED"):
        LinkedInApifyScraper(encrypt_token("t"))


def test_linkedin_apify_runs_when_flag_enabled(_fernet_key, monkeypatch):
    monkeypatch.setattr(settings, "APIFY_LINKEDIN_ENABLED", True)
    items = [
        {
            "jobId": "li-1",
            "title": "Senior Engineer",
            "companyName": "LinkedInCo",
            "location": "Remote, US",
            "description": "desc",
            "jobUrl": "https://linkedin.com/jobs/li-1",
        }
    ]
    factory = _fake_apify_client(items)

    scraper = LinkedInApifyScraper(encrypt_token("t"), client_factory=factory)
    jobs = scraper.scrape(keywords=["engineer"])
    assert len(jobs) == 1
    assert jobs[0].source == "linkedin_apify"
    assert jobs[0].external_id == "li-1"
    assert jobs[0].remote_type == "remote"
