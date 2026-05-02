"""Parse uploaded CV file or URL-scraped markdown into JSON Resume schema.

Two-stage pipeline:
1. extract_text_from_upload(file_bytes, mime_type) -> raw text
2. parse_cv_to_json_resume(raw_text) -> dict matching MasterCVContent schema

Stage 2 invokes the Claude CLI synchronously via `llm_extractor.
extract_json_via_cli` — same OAuth login as the cv-tailor skill, no
separate API key needed.
"""
from __future__ import annotations

import io
import logging
from typing import Any

from docx import Document
from pypdf import PdfReader

from app.services.llm_extractor import LLMExtractError, extract_json_via_cli

log = logging.getLogger(__name__)


_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
}

_ALLOWED_EXTENSIONS = (".pdf", ".docx", ".doc", ".md", ".markdown", ".txt")


class CVParseError(RuntimeError):
    pass


_EXTRACTION_SYSTEM_PROMPT = """You convert raw CV text into a strict JSON Resume schema with ATS-friendly extensions.

The input may be concatenated content from MULTIPLE web pages (separated by `=== Page: <url> ===` markers) or a single uploaded CV. Treat the entire input as one source describing one person — merge/dedupe entries that appear across pages.

Required schema (return ONLY the JSON, no prose, no code fences):
{
  "basics": {
    "name": str,
    "email": str,
    "label": str | null,
    "location": {"city": str, "region": str, "remote": bool} | null,
    "profiles": [{"network": str, "url": str}],
    "summary_variants": {
      "vibe_coding": str,
      "ai_automation": str,
      "ai_video": str
    }
  },
  "work": [
    {
      "company": str,
      "position": str,
      "startDate": str (YYYY-MM),
      "endDate": str (YYYY-MM) | null,
      "highlights": [
        {
          "text": str,
          "tags": [str],
          "metrics": dict | null,
          "relevance_hint": ["vibe_coding" | "ai_automation" | "ai_video"]
        }
      ]
    }
  ],
  "projects": [{"name": str, "description": str, "url": str | null, "tech": [str]}],
  "education": [{"institution": str, "area": str, "studyType": str, "endDate": str | null}],
  "skills": {"<category>": [str, ...]}
}

ATS-friendliness rules — these MATTER for downstream resume scoring:

1. COMPLETE EXTRACTION
   Capture EVERY distinct work entry, project, award, certification, and education record across all provided pages. Do not stop at the first 3-4 entries. If a page mentions 8 work positions, return all 8.

2. WORK ENTRIES
   Each entry MUST have: employer name, position title, startDate (YYYY-MM), endDate (YYYY-MM or null for "Present"). If the source only shows year, use YYYY-01.
   highlights[].text MUST start with a strong action verb (Built, Led, Shipped, Reduced, Architected, Migrated, Automated, Scaled, etc.). Include quantified outcome (numbers, percentages, scale, before/after) WHEN the source explicitly mentions one. Do NOT invent metrics.

3. SKILLS — STRICT FILTER
   skills MUST contain ONLY concrete technical skills (programming languages, frameworks, libraries, platforms, tools, protocols, paradigms). Group under sensible category keys (e.g. "languages", "frameworks", "cloud", "tools").
   EXCLUDE: model/product names ("VEO 3.1", "Seedance 2.0", "Kling AI", "OpenAI Sora", "Claude Opus"), vendor brand names treated as skills ("OpenClaw"), abstract meta-concepts ("Multi-agent Architecture", "Hierarchical Delegation", "Parallel Processing", "Tool Integration", "Webhook Integration"), generic soft skills ("Project Delivery", "Product Development").
   GOOD examples: Python, TypeScript, FastAPI, Next.js, PostgreSQL, AWS Lambda, Docker, n8n, Zapier, LangChain, Claude API, OpenAI API, Webhooks, REST APIs, gRPC.
   REJECT examples: VEO 3.1, Seedance 2.0, Multi-agent Architecture, Hierarchical Delegation, Conditional Routing, Project Delivery, Full-Stack Development.

4. PROJECTS
   Include name, 1-2 sentence description, url (if mentioned), tech stack (apply same skills filter — concrete tech only).

5. NO INVENTION
   If a field is missing in the source, return empty string or empty array. Never fabricate dates, metrics, employers, or job titles.

6. summary_variants
   All three keys MUST exist. If you can't tell which variant applies, use the same generic summary across all three (one tight paragraph, max 3 sentences).

7. relevance_hint
   MUST be a subset of ["vibe_coding", "ai_automation", "ai_video"]. AI/agent/automation work -> ai_automation; Claude Code / Cursor / dev tooling -> vibe_coding; video generation / diffusion / runway -> ai_video. Empty array if none fit.

8. DATES
   YYYY-MM format. "Present" / "Current" -> null endDate. Never infer dates that aren't in the source.

9. Return ONLY the JSON object — no markdown fences, no commentary.
"""


def is_supported_upload(mime_type: str | None, filename: str | None) -> bool:
    """Quick gate before reading bytes — used by the API layer for 422 responses."""
    name = (filename or "").lower()
    if any(name.endswith(ext) for ext in _ALLOWED_EXTENSIONS):
        return True
    if mime_type and mime_type in _ALLOWED_MIME_TYPES:
        return True
    if mime_type and mime_type.startswith("text/"):
        return True
    return False


def extract_text_from_upload(
    file_bytes: bytes, mime_type: str, filename: str = ""
) -> str:
    """Extract plain text from PDF / DOCX / MD / TXT."""
    name = (filename or "").lower()
    if mime_type == "application/pdf" or name.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            raise CVParseError(f"Failed to read PDF: {e}") from e
    if mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or name.endswith((".docx", ".doc")):
        try:
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception as e:
            raise CVParseError(f"Failed to read DOCX: {e}") from e
    # text/plain or text/markdown
    if (
        mime_type in {"text/plain", "text/markdown", "text/x-markdown"}
        or (mime_type and mime_type.startswith("text/"))
        or name.endswith((".md", ".markdown", ".txt"))
    ):
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            raise CVParseError(f"Failed to decode text: {e}") from e
    raise CVParseError(f"Unsupported file type: {mime_type or 'unknown'}")


def parse_cv_to_json_resume(raw_text: str) -> dict[str, Any]:
    """Send raw_text to Claude CLI, get back JSON Resume dict.

    Auth: the host's `claude` CLI OAuth login. No API key required.
    """
    if not raw_text or not raw_text.strip():
        raise CVParseError("Empty source text — nothing to parse")

    try:
        return extract_json_via_cli(
            system_prompt=_EXTRACTION_SYSTEM_PROMPT,
            # Sonnet 4.6 — significantly better structured extraction than
            # Haiku for ATS-friendly multi-page CV input. Cost trade-off
            # is acceptable for a per-CV one-shot operation.
            model="claude-sonnet-4-6",
            # 120k char ceiling — 4 portfolio pages of markdown easily
            # exceeds the previous 50k limit.
            user_message=f"Extract JSON Resume from this CV:\n\n{raw_text[:120000]}",
        )
    except LLMExtractError as e:
        raise CVParseError(str(e)) from e
