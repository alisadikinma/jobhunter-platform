"""Parse uploaded CV file or URL-scraped markdown into JSON Resume schema.

Two-stage pipeline:
1. extract_text_from_upload(file_bytes, mime_type) -> raw text
2. parse_cv_to_json_resume(raw_text) -> dict matching MasterCVContent schema

Calls Anthropic API directly via httpx — distinct from the Claude CLI
subprocess (used by cv-tailor skill). The CLI is for long-running
generation; this is a single fast extraction (~5s).
"""
from __future__ import annotations

import io
import json
import logging
from typing import Any

import httpx
from docx import Document
from pypdf import PdfReader

from app.config import settings

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


_EXTRACTION_SYSTEM_PROMPT = """You convert raw CV text into a strict JSON Resume schema with our extensions.

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

Rules:
- All three summary_variants keys MUST exist (use the same generic summary if you can't tell which variant applies).
- relevance_hint MUST be a subset of ["vibe_coding", "ai_automation", "ai_video"] — pick based on highlight content (AI/agent/automation work -> ai_automation, claude code/cursor/dev tools -> vibe_coding, video gen/diffusion -> ai_video).
- Dates as YYYY-MM. "Present" -> null.
- DO NOT invent data. If a field is missing in the source, return empty string or empty array.
- Return ONLY the JSON object — no markdown, no commentary.
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
    """Send raw_text to Anthropic API, get back JSON Resume dict."""
    if not raw_text or not raw_text.strip():
        raise CVParseError("Empty source text — nothing to parse")

    if not settings.ANTHROPIC_API_KEY:
        raise CVParseError(
            "ANTHROPIC_API_KEY not configured — set in .env to enable CV upload parsing"
        )

    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.ANTHROPIC_MODEL_FAST,
        "max_tokens": 4096,
        "system": _EXTRACTION_SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": f"Extract JSON Resume from this CV:\n\n{raw_text[:50000]}",
            }
        ],
    }
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            body = resp.json()
    except httpx.HTTPError as e:
        raise CVParseError(f"Anthropic API call failed: {e}") from e

    blocks = body.get("content") or []
    text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    raw_json = "\n".join(text_parts).strip()

    # Strip ```json fences if model added them despite the instruction.
    if raw_json.startswith("```"):
        raw_json = raw_json.split("\n", 1)[1] if "\n" in raw_json else raw_json
        if raw_json.endswith("```"):
            raw_json = raw_json.rsplit("```", 1)[0]
        raw_json = raw_json.strip()

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        log.warning("LLM returned invalid JSON: %s", raw_json[:500])
        raise CVParseError(f"Failed to parse LLM JSON output: {e}") from e
