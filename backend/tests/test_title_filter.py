"""Coverage for app.utils.title_filter — allowlist of AI-relevant titles."""
import pytest

from app.utils.title_filter import is_ai_relevant, is_offtopic_title


@pytest.mark.parametrize("title", [
    # Plain non-AI roles (formerly the "blocklist" set)
    "Regional Sales Executive",
    "Territory Account Manager",
    "Account Executive III",
    "VP of Marketing",
    "Senior Recruiter",
    "Customer Success Manager",
    "HR Business Partner",
    "Senior Accountant",
    "BDR — Outbound Sales",
    "Database Administrator",
    # User-reported leaks (the actual reason this allowlist exists)
    "ML Engineer",
    "Senior Cloud Architect",
    "Senior CAD Backend Engineer Mechanical CAD Automation",
    "Digital Media Strategist",
    "Director Global Account Management",
    "Monetisation and LiveOps Lead (f/m/d)",
    "DevOps Engineer",
    "Senior DevOps Engineer",
    "Data Product Manager",
    "Data Engineer",
    "Data Scientist",
    "Software Engineer",  # generic, no AI signal in title
    "Backend Engineer — Python",
    "Site Reliability Engineer",
    "Platform Engineer",
    "Senior Product Manager",
])
def test_rejects_when_no_ai_signal(title):
    assert is_offtopic_title(title), f"should reject: {title!r}"
    assert not is_ai_relevant(title)


@pytest.mark.parametrize("title", [
    # AI Engineering / AI Agent / Automation
    "AI Engineer",
    "Senior AI Engineer",
    "AI/ML Engineer",
    "AI Infrastructure Engineer",
    "AI Platform Engineer",
    "AI Research Engineer",
    "AI Agent Developer",
    "Senior Agentic AI Engineer",
    "AI Automation Specialist",
    "AI Workflow Engineer",
    # LLM-focused
    "LLM Engineer",
    "Senior LLM Developer",
    "LLMOps Engineer",
    "Prompt Engineer",
    # Video / Image / Creative
    "AI Video Artist",
    "AI Creative Director",
    "Generative AI Engineer",
    "GenAI Engineer",
    "Computer Vision Engineer",
    "Diffusion Model Researcher",
    # Vibe coding
    "Vibe Coding Engineer",
    "Claude Code Specialist",
    "AI-First Engineer",
    "AI-Native Developer",
    "Founding AI Engineer",
])
def test_keeps_ai_relevant_titles(title):
    assert not is_offtopic_title(title), f"should KEEP: {title!r}"
    assert is_ai_relevant(title)


def test_none_and_empty():
    # Empty/None returns False from BOTH — caller decides what to do with
    # title-less rows (usually dropped at schema level).
    assert not is_offtopic_title(None)
    assert not is_offtopic_title("")
    assert not is_ai_relevant(None)
    assert not is_ai_relevant("")


def test_case_insensitive():
    assert is_ai_relevant("AI ENGINEER")
    assert is_ai_relevant("ai engineer")
    assert is_ai_relevant("Ai Engineer")
