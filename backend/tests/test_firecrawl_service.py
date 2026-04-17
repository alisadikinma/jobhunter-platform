"""FirecrawlService unit tests — respx-mocked."""
import httpx
import respx

from app.config import settings
from app.services.firecrawl_service import FirecrawlService

_FIRECRAWL_URL = f"{settings.FIRECRAWL_API_URL.rstrip('/')}/v1/scrape"


@respx.mock
def test_scrape_returns_markdown_and_metadata():
    respx.post(_FIRECRAWL_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "# Example\n\nBody text here.",
                    "html": "<h1>Example</h1>",
                    "metadata": {
                        "title": "Example Page",
                        "description": "An example",
                        "statusCode": 200,
                    },
                },
            },
        )
    )
    result = FirecrawlService().scrape("https://example.com")
    assert result["markdown"].startswith("# Example")
    assert result["title"] == "Example Page"
    assert result["error"] is None


@respx.mock
def test_scrape_handles_http_error_gracefully():
    respx.post(_FIRECRAWL_URL).mock(return_value=httpx.Response(503))
    result = FirecrawlService().scrape("https://example.com")
    assert result["markdown"] == ""
    assert result["error"] is not None


@respx.mock
def test_scrape_handles_malformed_json():
    respx.post(_FIRECRAWL_URL).mock(return_value=httpx.Response(200, text="not json"))
    result = FirecrawlService().scrape("https://example.com")
    assert result["markdown"] == ""
    assert result["error"] == "malformed response"


@respx.mock
def test_scrape_reports_upstream_failure_flag():
    respx.post(_FIRECRAWL_URL).mock(
        return_value=httpx.Response(200, json={"success": False, "error": "blocked by target"})
    )
    result = FirecrawlService().scrape("https://example.com")
    assert result["markdown"] == ""
    assert "blocked" in (result["error"] or "")


@respx.mock
def test_scrape_passes_auth_header_when_key_set(monkeypatch):
    monkeypatch.setattr(settings, "FIRECRAWL_API_KEY", "fc_test_key")
    route = respx.post(_FIRECRAWL_URL).mock(
        return_value=httpx.Response(200, json={"success": True, "data": {"markdown": "x"}})
    )
    FirecrawlService().scrape("https://example.com")
    assert route.called
    sent_auth = route.calls.last.request.headers.get("Authorization")
    assert sent_auth == "Bearer fc_test_key"


@respx.mock
def test_scrape_with_extraction_uses_extract_format():
    captured: dict = {}

    def _capture(request: httpx.Request) -> httpx.Response:
        import json as _json
        captured["body"] = _json.loads(request.content)
        return httpx.Response(
            200,
            json={"success": True, "data": {"extract": {"industry": "AI"}}},
        )

    respx.post(_FIRECRAWL_URL).mock(side_effect=_capture)
    result = FirecrawlService().scrape_with_extraction(
        "https://example.com", schema={"industry": "string"}
    )
    assert captured["body"]["formats"] == ["extract"]
    assert result["extract"] == {"industry": "AI"}
