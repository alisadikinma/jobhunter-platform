# ruff: noqa: RUF001, RUF002
"""Render master CV content into ATS-friendly Pandoc markdown.

Pure templated renderer — no LLM. Used by the master CV preview/download
endpoints to produce a generic ATS CV without needing an Application
context (the tailored-per-job path goes through cv_generator + cv-tailor
skill instead).

Output conventions (ATS resume parser-friendly):
  - H1 for candidate name only
  - H2 for top-level sections (Summary, Experience, Education, ...)
  - H3 for individual role / school entries
  - Plain text bullet lists (no nested tables, no images)
  - Date ranges as "MMM YYYY – MMM YYYY" or "YYYY-MM"
  - Skills surfaced as "**Category:** comma list" lines (parsers love
    this shape; both Greenhouse and Workable's resume parsers
    keyword-match against it)
  - HTML in source fields is stripped paragraph-aware (preserves
    "\\n\\n" boundaries for downstream readability)
  - Selected projects capped at 10 (featured first, then recency) — 56
    raw projects bloats the CV and overflows ATS character limits
"""
from __future__ import annotations

import re
from html import unescape
from typing import Any

_BLOCK_TAG_RE = re.compile(r"</(p|div|li|h[1-6])>", re.IGNORECASE)
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


# Per-template section ordering. Keys MUST stay in lockstep with
# SUPPORTED_TEMPLATES — the module-level assertion below enforces this so
# a new template can't be added without explicitly choosing a section
# order (otherwise the renderer would silently fall back to plain and
# the recruiter-pleasing intent would be lost).
SUPPORTED_TEMPLATES: tuple[str, ...] = ("plain", "classic", "modern")

SECTION_ORDER: dict[str, tuple[str, ...]] = {
    # Engineer-first (default): Jake's Resume convention
    "plain":   ("summary", "experience", "skills", "projects", "education", "awards", "certifications"),
    # Academic-first: Harvard OCS convention — education leads, projects last
    "classic": ("summary", "education", "experience", "skills", "awards", "certifications", "projects"),
    # Skills-first: Rezi convention — pitches the toolkit before the resume body
    "modern":  ("summary", "skills", "experience", "projects", "awards", "education", "certifications"),
}

assert set(SECTION_ORDER.keys()) == set(SUPPORTED_TEMPLATES), (
    "SECTION_ORDER must define ordering for every template in SUPPORTED_TEMPLATES"
)


def _section_header(name: str, template: str) -> str:
    """Return the H2 line for a section, cased per template.

    `plain` uses ALL CAPS for stronger ATS keyword anchoring; `classic`
    and `modern` use Title Case for human readability.
    """
    return f"## {name.upper()}" if template == "plain" else f"## {name}"


def _strip_html(value: Any) -> str:
    """Strip HTML to plain text but preserve paragraph breaks (\\n\\n)
    and line breaks (\\n) so the resulting markdown keeps narrative
    structure. Returns empty string for null / non-string input."""
    if not isinstance(value, str) or not value.strip():
        return ""
    text = _BLOCK_TAG_RE.sub("\n\n", value)
    text = _BR_RE.sub("\n", text)
    text = _TAG_RE.sub("", text)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _format_date(value: Any) -> str:
    """Render YYYY-MM, YYYY-MM-DD, or YYYY → 'MMM YYYY' or 'YYYY'.
    Returns empty string for null/missing. ATS parsers handle both
    formats — month names slightly improve readability for humans."""
    if not value:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        year, month = m.group(1), int(m.group(2))
        if 1 <= month <= 12:
            return f"{_MONTHS[month - 1]} {year}"
    if re.match(r"^\d{4}$", s):
        return s
    return s


def _date_range(start: Any, end: Any, *, current_label: str = "Present") -> str:
    """'Jan 2024 – Present' / 'Jan 2024 – Dec 2025' / 'Jan 2024' /
    'Present'. Returns empty string when both ends are missing."""
    s = _format_date(start)
    e = _format_date(end) if end else ""
    if s and not e:
        return f"{s} – {current_label}"
    if not s and e:
        return e
    if s and e:
        return f"{s} – {e}"
    return ""


def _profiles_inline(profiles: list[dict]) -> str:
    """Compress the profiles[] array into a single comma-joined line
    suitable for the contact line. Skips anything missing a URL."""
    if not isinstance(profiles, list):
        return ""
    parts: list[str] = []
    for p in profiles:
        if not isinstance(p, dict):
            continue
        url = (p.get("url") or "").strip()
        if not url:
            continue
        # Strip the scheme so the inline line stays compact for ATS
        # parsers that auto-link plain text.
        display = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
        net = (p.get("network") or "").strip()
        if net and net.lower() not in display.lower():
            parts.append(f"{net.title()}: {display}")
        else:
            parts.append(display)
    return " · ".join(parts)


def _join_skills(skills: dict) -> str:
    """Render each skills category as a bold-prefixed line. Categories
    keep their order in the dict (Python 3.7+ insertion-ordered)."""
    if not isinstance(skills, dict):
        return ""
    lines: list[str] = []
    for category, items in skills.items():
        if not isinstance(items, list) or not items:
            continue
        label = category.replace("_", " ").title()
        # Pandoc renders trailing two-space line breaks; preserves the
        # one-line-per-category density ATS parsers prefer.
        lines.append(f"**{label}:** {', '.join(items)}  ")
    return "\n".join(lines)


def _render_work(work: list[dict]) -> str:
    if not isinstance(work, list) or not work:
        return ""
    blocks: list[str] = []
    for w in work:
        if not isinstance(w, dict):
            continue
        company = (w.get("company") or "").strip()
        position = (w.get("position") or w.get("title") or "").strip()
        if not company and not position:
            continue
        header = f"### {position} · {company}" if position and company else f"### {position or company}"
        date_line = _date_range(w.get("start_date"), w.get("end_date"))
        location = (w.get("location") or "").strip()
        meta_parts = [p for p in (date_line, location) if p]
        meta_line = " · ".join(meta_parts)
        summary = _strip_html(w.get("summary"))

        block_lines = [header]
        if meta_line:
            block_lines.append(f"_{meta_line}_")
        if summary:
            block_lines.append("")
            block_lines.append(summary)

        # Highlights are optional; render as bullet list when present.
        highlights = w.get("highlights")
        if isinstance(highlights, list) and highlights:
            block_lines.append("")
            for h in highlights:
                text = ""
                if isinstance(h, dict):
                    text = _strip_html(h.get("text"))
                elif isinstance(h, str):
                    text = _strip_html(h)
                if text:
                    block_lines.append(f"- {text}")

        tech_stack = w.get("tech_stack")
        if isinstance(tech_stack, list) and tech_stack:
            block_lines.append("")
            block_lines.append(f"**Tech:** {', '.join(str(t) for t in tech_stack if t)}")

        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_education(education: list[dict]) -> str:
    if not isinstance(education, list) or not education:
        return ""
    lines: list[str] = []
    for e in education:
        if not isinstance(e, dict):
            continue
        institution = (e.get("institution") or "").strip()
        if not institution:
            continue
        area = (e.get("area") or "").strip()
        study_type = (e.get("study_type") or "").strip()
        date_line = _date_range(e.get("start_date"), e.get("end_date"), current_label="")
        # Format: **Bachelor of Computer Science** · BINUS University (2019)
        degree_part = " ".join(p for p in (study_type, ("of " + area) if area else "") if p).strip()
        head = f"**{degree_part or 'Education'}**"
        tail_parts = [institution]
        if date_line:
            tail_parts.append(f"({date_line.replace(' – ', '–')})")
        lines.append(f"{head} · {' '.join(tail_parts)}")
    return "  \n".join(lines)


def _render_awards(awards: list[dict]) -> str:
    if not isinstance(awards, list) or not awards:
        return ""
    bullets: list[str] = []
    for a in awards:
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or "").strip()
        if not title:
            continue
        awarder = (a.get("awarder") or "").strip()
        date = _format_date(a.get("date"))
        suffix_parts = [p for p in (awarder, date) if p]
        suffix = f" · {' · '.join(suffix_parts)}" if suffix_parts else ""
        bullets.append(f"- **{title}**{suffix}")
    return "\n".join(bullets)


def _render_certifications(certs: list[dict]) -> str:
    if not isinstance(certs, list) or not certs:
        return ""
    bullets: list[str] = []
    for c in certs:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip()
        if not name:
            continue
        url = (c.get("url") or "").strip()
        if url:
            display = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
            bullets.append(f"- {name} — {display}")
        else:
            bullets.append(f"- {name}")
    return "\n".join(bullets)


def _render_projects(projects: list[dict], cap: int = 10) -> str:
    if not isinstance(projects, list) or not projects:
        return ""
    # Featured first, then anything with metrics filled, then natural order.
    def sort_key(p: dict) -> tuple[int, int]:
        if not isinstance(p, dict):
            return (3, 0)
        if p.get("is_featured"):
            return (0, 0)
        metrics = p.get("metrics")
        if isinstance(metrics, dict) and metrics:
            return (1, 0)
        if (p.get("highlights") and isinstance(p.get("highlights"), list)):
            return (2, 0)
        return (3, 0)

    ranked = sorted(
        [p for p in projects if isinstance(p, dict) and (p.get("name") or p.get("title"))],
        key=sort_key,
    )[:cap]

    blocks: list[str] = []
    for p in ranked:
        name = (p.get("name") or p.get("title") or "").strip()
        url = (p.get("url") or "").strip()
        head = f"### {name}"
        if url:
            head += f" — {re.sub(r'^https?://(www\\.)?', '', url).rstrip('/')}"
        description = _strip_html(p.get("description"))
        tech = p.get("tech_stack")
        tech_line = ""
        if isinstance(tech, list) and tech:
            tech_line = f"**Tech:** {', '.join(str(t) for t in tech if t)}"

        block_lines = [head]
        if description:
            block_lines.append("")
            block_lines.append(description)
        if tech_line:
            block_lines.append("")
            block_lines.append(tech_line)
        blocks.append("\n".join(block_lines))
    return "\n\n".join(blocks)


def _render_thought_leadership(posts: list[dict]) -> str:
    if not isinstance(posts, list) or not posts:
        return ""
    bullets: list[str] = []
    for t in posts:
        if not isinstance(t, dict):
            continue
        title = (t.get("title") or "").strip()
        if not title:
            continue
        url = (t.get("url") or "").strip()
        date = _format_date(t.get("published_at"))
        suffix = f" · {date}" if date else ""
        if url:
            display = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
            bullets.append(f"- \"{title}\" — {display}{suffix}")
        else:
            bullets.append(f"- \"{title}\"{suffix}")
    return "\n".join(bullets)


def render_master_cv_to_markdown(content: dict, template: str = "plain") -> str:
    """Compose the full ATS-friendly markdown.

    The header (name + contact + profiles) always comes first; the body
    sections are ordered per `SECTION_ORDER[template]` to match the
    recruiter-pleasing convention for that template family. Thought
    leadership is appended after the ordered sections (it's a "nice to
    have" trailing block, not a primary section). Empty sections are
    omitted entirely — an empty `## Education` heading confuses ATS
    parsers more than its absence.
    """
    if not isinstance(content, dict):
        raise ValueError("content must be a dict")
    if template not in SUPPORTED_TEMPLATES:
        raise ValueError(
            f"unsupported template {template!r}; expected one of {SUPPORTED_TEMPLATES}"
        )

    basics = content.get("basics") or {}
    name = (basics.get("name") or "Unknown").strip()
    label = (basics.get("label") or "").strip()

    # --- Header ----------------------------------------------------
    contact_parts: list[str] = []
    for key in ("email", "phone"):
        v = basics.get(key)
        if v:
            contact_parts.append(str(v).strip())
    location = basics.get("location") or {}
    if isinstance(location, dict):
        loc_bits = [
            location.get("city"),
            location.get("region"),
            location.get("country"),
        ]
        loc_str = ", ".join([b for b in loc_bits if b])
        if location.get("remote"):
            loc_str = (loc_str + " (Remote)").strip()
        if loc_str:
            contact_parts.append(loc_str)
    elif isinstance(location, str):
        contact_parts.append(location)

    profiles_line = _profiles_inline(basics.get("profiles") or [])

    parts: list[str] = [f"# {name}"]
    if label:
        parts.append(f"**{label}**  ")
    if contact_parts:
        parts.append(" · ".join(contact_parts) + ("  " if profiles_line else ""))
    if profiles_line:
        parts.append(profiles_line)

    # --- Build per-section markdown chunks (header + body) --------
    # Each value is the full chunk to append OR an empty string when the
    # underlying data is absent. The "skip empty section" behavior is
    # preserved by checking truthiness during the ordered emit below.

    # Summary chunk also carries the Languages line — Languages is a
    # contact-adjacent fact, not a top-level section, so it stays glued
    # to summary regardless of template ordering.
    summary_text = _strip_html(basics.get("summary_text") or basics.get("summary"))
    languages = basics.get("languages")
    if summary_text or (isinstance(languages, list) and languages):
        summary_lines: list[str] = [f"\n{_section_header('Summary', template)}\n"]
        if summary_text:
            summary_lines.append(summary_text)
        if isinstance(languages, list) and languages:
            summary_lines.append("")
            summary_lines.append(
                f"**Languages:** {', '.join(str(lang) for lang in languages)}"
            )
        summary_chunk = "\n".join(summary_lines)
    else:
        summary_chunk = ""

    work_block = _render_work(content.get("work") or [])
    experience_chunk = (
        f"\n{_section_header('Experience', template)}\n\n{work_block}" if work_block else ""
    )

    education_block = _render_education(content.get("education") or [])
    education_chunk = (
        f"\n{_section_header('Education', template)}\n\n{education_block}"
        if education_block
        else ""
    )

    skills_block = _join_skills(content.get("skills") or {})
    skills_chunk = (
        f"\n{_section_header('Skills', template)}\n\n{skills_block}" if skills_block else ""
    )

    awards_block = _render_awards(content.get("awards") or [])
    awards_chunk = (
        f"\n{_section_header('Awards & Recognition', template)}\n\n{awards_block}"
        if awards_block
        else ""
    )

    certs_block = _render_certifications(content.get("certifications") or [])
    certifications_chunk = (
        f"\n{_section_header('Certifications', template)}\n\n{certs_block}"
        if certs_block
        else ""
    )

    projects_block = _render_projects(content.get("projects") or [])
    projects_chunk = (
        f"\n{_section_header('Selected Projects', template)}\n\n{projects_block}"
        if projects_block
        else ""
    )

    section_blocks: dict[str, str] = {
        "summary": summary_chunk,
        "experience": experience_chunk,
        "education": education_chunk,
        "skills": skills_chunk,
        "awards": awards_chunk,
        "certifications": certifications_chunk,
        "projects": projects_chunk,
    }

    # --- Emit in template-specific order ---------------------------
    for key in SECTION_ORDER[template]:
        chunk = section_blocks.get(key, "")
        if chunk:
            parts.append(chunk)

    # --- Thought Leadership (always trailing) ---------------------
    thought_block = _render_thought_leadership(content.get("thought_leadership") or [])
    if thought_block:
        parts.append(f"\n{_section_header('Thought Leadership', template)}\n")
        parts.append(thought_block)

    return "\n".join(parts).strip() + "\n"
