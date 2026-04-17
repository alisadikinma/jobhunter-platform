"""ATS scorer unit tests."""
from app.services.scorer_service import score_cv


def test_score_empty_jd_returns_zero():
    r = score_cv("some cv content here", "")
    assert r.score == 0
    assert "empty" in r.suggestions[0].lower()


def test_score_perfect_overlap_is_high():
    # Pad the CV so the short-CV 10pt penalty doesn't trigger; the focus is
    # on overlap quality, not length.
    cv = " ".join(["Python Kubernetes FastAPI TypeScript PostgreSQL Claude Code"] * 50)
    jd = "We need Python, Kubernetes, FastAPI, TypeScript, PostgreSQL, Claude Code."
    r = score_cv(cv, jd)
    assert r.score >= 80
    assert "python" in r.keyword_matches
    assert "kubernetes" in r.keyword_matches


def test_score_low_when_cv_misses_keywords():
    cv = "Marketing manager with 10 years in brand strategy and advertising."
    jd = "We need a Python + Kubernetes + FastAPI engineer."
    r = score_cv(cv, jd)
    assert r.score < 30
    assert "python" in r.missing_keywords


def test_score_short_cv_suggestion_triggers():
    cv = "Python FastAPI."  # very short
    jd = "We need Python FastAPI, Docker, PostgreSQL experience."
    r = score_cv(cv, jd)
    assert any("short" in s.lower() for s in r.suggestions)


def test_score_stopwords_ignored():
    cv_a = "We are building with Python and FastAPI."
    cv_b = "building Python FastAPI."
    # Stopwords like 'we', 'are', 'with', 'and', 'a' should not inflate score.
    r_a = score_cv(cv_a, "Python FastAPI")
    r_b = score_cv(cv_b, "Python FastAPI")
    assert r_a.score == r_b.score  # same core content → same score
