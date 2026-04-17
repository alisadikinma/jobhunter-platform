from pydantic import BaseModel


class EnrichmentResponse(BaseModel):
    ok: bool
    source: str  # "aggregator" | "firecrawl_enriched"
    length_before: int
    length_after: int
    message: str | None = None


class CompanyResearchResponse(BaseModel):
    ok: bool
    domain: str | None
    title: str | None
    markdown_chars: int
    message: str | None = None
