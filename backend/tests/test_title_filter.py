"""Coverage for app.utils.title_filter — what we reject vs. what we keep."""
import pytest

from app.utils.title_filter import is_offtopic_title


@pytest.mark.parametrize("title", [
    "Regional Sales Executive",
    "Territory Account Manager",
    "Account Executive III",
    "VP of Marketing",
    "Vice President of Marketing",
    "Managing Director New England",
    "Senior Recruiter",
    "Talent Acquisition Specialist",
    "Customer Success Manager",
    "Executive Assistant",
    "HR Business Partner",
    "Senior Accountant",
    "BDR — Outbound Sales",
    "Sales Development Representative (SDR)",
    "Database Administrator",
])
def test_rejects_offtopic_titles(title):
    assert is_offtopic_title(title), f"should reject: {title!r}"


@pytest.mark.parametrize("title", [
    "AI Engineer",
    "ML Engineer",
    "Senior Machine Learning Engineer",
    "Data Engineer (Remote)",
    "Data Scientist II",
    "Software Engineer",
    "Backend Engineer — Python",
    "Full-Stack Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Platform Engineer",
    "AI Automation Specialist",
    "AI Video Artist",
    "Founding Engineer",
    "Developer Advocate",
    "Computer Vision Engineer",
    "NLP Researcher",
    "LLM Infrastructure Engineer",
])
def test_keeps_engineering_titles(title):
    assert not is_offtopic_title(title), f"should KEEP: {title!r}"


def test_none_and_empty():
    assert not is_offtopic_title(None)
    assert not is_offtopic_title("")
    assert not is_offtopic_title("   ")


def test_case_insensitive():
    assert is_offtopic_title("REGIONAL SALES EXECUTIVE")
    assert is_offtopic_title("regional sales executive")
    assert is_offtopic_title("Regional Sales Executive")


def test_word_boundary_no_false_positive():
    # "automation" should not trigger "ad" or "executive" should not trigger
    # via partial match
    assert not is_offtopic_title("AI Automation Engineer")
    assert not is_offtopic_title("Operations Engineer")  # no offtopic tokens


def test_engineering_signal_overrides_offtopic_token():
    # When an off-topic token co-occurs with an explicit engineering signal,
    # we KEEP — the role likely is AI-engineering with an off-topic adjective.
    assert not is_offtopic_title("AI Engineer — Sales Engineering track")
    assert not is_offtopic_title("Senior Machine Learning Engineer (Marketing Analytics)")
