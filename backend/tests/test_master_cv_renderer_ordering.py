"""Per-template section ordering for the master CV markdown renderer.

The 3 ATS-template families need DIFFERENT section orderings, per the
recruiter-pleasing convention from Harvard OCS / Jake's Resume / Rezi
research:

    plain   — engineer-first  (experience surfaces before education)
    classic — academic-first  (education surfaces before experience)
    modern  — skills-first    (skills surfaces before experience)
"""
from __future__ import annotations

import pytest

from app.services.master_cv_renderer import render_master_cv_to_markdown


@pytest.fixture
def sample_content() -> dict:
    """Master CV content that exercises every section the renderer knows."""
    return {
        "basics": {
            "name": "Ali Sadikin Ma",
            "label": "AI Engineer",
            "email": "ali@example.com",
            "summary_text": "Senior engineer shipping AI-augmented dev tooling.",
            "summary_variants": {
                "vibe_coding": "Vibe coding pitch.",
                "ai_automation": "Automation pitch.",
                "ai_video": "Video pitch.",
            },
        },
        "work": [
            {
                "company": "Acme",
                "position": "Staff AI Engineer",
                "start_date": "2023-01",
                "end_date": "2025-06",
                "summary": "Led the AI platform.",
                "highlights": [{"text": "Shipped CV tailoring pipeline."}],
            }
        ],
        "education": [
            {
                "institution": "BINUS University",
                "area": "Computer Science",
                "study_type": "Bachelor",
                "end_date": "2019",
            }
        ],
        "skills": {"languages": ["Python"]},
        "projects": [
            {
                "name": "JobHunter",
                "description": "ATS-friendly CV pipeline.",
                "tech_stack": ["FastAPI", "Next.js"],
            }
        ],
        "awards": [{"title": "Best Engineer", "awarder": "Acme", "date": "2024"}],
        "certifications": [{"name": "AWS Solutions Architect"}],
    }


def _idx(text: str, needle: str) -> int:
    """Case-insensitive substring index — `plain` template emits ALL CAPS
    H2s while `classic`/`modern` emit Title Case, so we normalize."""
    return text.lower().index(needle.lower())


@pytest.mark.parametrize("template", ["plain", "classic", "modern"])
def test_renders_all_section_headers_for_template(sample_content, template):
    md = render_master_cv_to_markdown(sample_content, template=template)
    # Every section in the fixture should appear under one of the
    # template's ordered slots.
    for header in (
        "summary",
        "experience",
        "education",
        "skills",
        "awards",
        "certifications",
        "projects",
    ):
        assert header in md.lower(), f"{template} missing section: {header}"


def test_plain_template_engineer_first_ordering(sample_content):
    md = render_master_cv_to_markdown(sample_content, template="plain")
    exp = _idx(md, "experience")
    edu = _idx(md, "education")
    skills = _idx(md, "skills")
    projects = _idx(md, "projects")
    assert exp < edu, f"plain ordering: experience at {exp} expected < education at {edu}"
    assert skills < projects, (
        f"plain ordering: skills at {skills} expected < projects at {projects}"
    )


def test_classic_template_academic_first_ordering(sample_content):
    md = render_master_cv_to_markdown(sample_content, template="classic")
    edu = _idx(md, "education")
    exp = _idx(md, "experience")
    projects = _idx(md, "projects")
    certs = _idx(md, "certifications")
    assert edu < exp, f"classic ordering: education at {edu} expected < experience at {exp}"
    assert projects > certs, (
        f"classic ordering: projects at {projects} expected > certifications at {certs}"
    )


def test_modern_template_skills_first_ordering(sample_content):
    md = render_master_cv_to_markdown(sample_content, template="modern")
    skills = _idx(md, "skills")
    exp = _idx(md, "experience")
    projects = _idx(md, "projects")
    edu = _idx(md, "education")
    assert skills < exp, f"modern ordering: skills at {skills} expected < experience at {exp}"
    assert projects < edu, (
        f"modern ordering: projects at {projects} expected < education at {edu}"
    )


@pytest.mark.parametrize("template", ["plain", "classic", "modern"])
def test_projects_emit_no_per_project_urls(sample_content, template):
    """Per-project URLs were retired (cosmetic-truncated `domain.com/...slug`
    forms were non-clickable garbage on PDF/print). The renderer must not
    emit any URL on a project's H3 line, even when the project carries a
    `url` field — recruiters use the catalog link instead."""
    sample_content = dict(sample_content)
    sample_content["projects"] = [
        {
            "name": "JobHunter",
            "description": "ATS pipeline.",
            "url": "https://www.alisadikinma.com/work/some-very-long-project-slug-name",
            "tech_stack": ["FastAPI"],
        }
    ]
    md = render_master_cv_to_markdown(sample_content, template=template)
    # H3 line must NOT carry a URL or its truncated cosmetic stub.
    assert "### JobHunter\n" in md or "### JobHunter\r\n" in md or md.rstrip().endswith("### JobHunter") or "### JobHunter " not in md, (
        f"{template} project H3 still carries trailing decoration: {md!r}"
    )
    # Truncation glyph from the old _shorten_url() helper must be gone.
    assert "/.../" not in md, f"{template} still emits the old `/.../` truncation stub"
    # The full project URL must not appear in the project block (it was the
    # source of the cosmetic stubs).
    assert "some-very-long-project-slug-name" not in md, (
        f"{template} leaked the per-project URL into the rendered markdown"
    )


def test_projects_section_emits_catalog_url_when_set(sample_content):
    """When `basics.projects_url` is set, the Selected Projects section
    leads with a single italicised catalog link (full URL, plain text so
    ATS parsers can extract it)."""
    sample_content = dict(sample_content)
    sample_content["basics"] = {
        **sample_content["basics"],
        "projects_url": "https://alisadikinma.com/en/work?tab=projects",
    }
    md = render_master_cv_to_markdown(sample_content, template="plain")
    assert "_Full project list: https://alisadikinma.com/en/work?tab=projects_" in md, (
        f"catalog link missing from rendered markdown: {md!r}"
    )
    # Catalog line must sit between the Selected Projects header and the
    # first project H3 inside that section. Scope the search past the
    # Selected Projects header so the Experience section's H3s don't
    # poison the assertion.
    section_start = md.lower().index("selected projects")
    catalog_idx = md.index("Full project list:", section_start)
    first_project_h3_idx = md.index("### ", section_start)
    assert section_start < catalog_idx < first_project_h3_idx, (
        "catalog link must sit between the Selected Projects header and the first project H3"
    )


def test_projects_section_omits_catalog_url_when_unset(sample_content):
    """No `projects_url` → no catalog line. Section header still appears."""
    md = render_master_cv_to_markdown(sample_content, template="plain")
    assert "Full project list" not in md, (
        "renderer should not invent a catalog line when basics.projects_url is unset"
    )
