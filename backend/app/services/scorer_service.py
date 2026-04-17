"""Lightweight ATS scorer — keyword overlap between CV and JD.

Deliberately NOT using `resume-matcher` (the plan's optional dep) — that
library is ~400MB of torch + spacy and overkill for a keyword-overlap
metric. This implementation tokenizes both sides, strips stopwords,
computes Jaccard-like ratios, and returns a 0-100 score.

If we ever need richer semantic scoring, swap this module for a
resume-matcher wrapper; callers use the same interface.
"""
import re
from dataclasses import dataclass

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9+\-.]{1,}")

_STOPWORDS = frozenset(["a", "an", "and", "any", "are", "as", "at", "be", "by", "for", "from", "has", "have", "if", "in", "is", "it", "its", "of", "on", "or", "so", "that", "the", "their", "there", "they", "this", "to", "was", "we", "were", "will", "with", "you", "your", "our", "can", "about", "also", "into", "like", "not", "but", "more", "most", "than", "then", "them", "these", "those", "who", "what", "which", "when", "where", "why", "how", "some", "such", "each", "every", "other", "same", "new", "very", "just", "use", "used", "using", "across", "within", "across", "over", "under", "between", "before", "after", "during", "team", "role", "work", "you'll", "you'll", "be", "role", "you", "will", "we're", "were", "experience", "experienced", "needs", "need", "required", "require", "requires", "looking", "ideal", "ideal", "candidate", "candidate", "candidates", "skill", "skills", "strong", "strong", "proven", "proficient", "proficiency", "year", "years", "yr", "yrs", "knowledge", "ability", "must", "should", "love", "passion", "passionate", "excited", "opportunity", "opportunities", "join", "joining", "growth", "growing", "fast-paced", "fast", "paced"])


@dataclass
class ScoreBreakdown:
    score: int  # 0-100
    keyword_matches: list[str]
    missing_keywords: list[str]
    suggestions: list[str]


def _tokenize(text: str) -> list[str]:
    return [
        w.lower().strip(".-+")
        for w in _WORD_RE.findall(text or "")
        if w.lower() not in _STOPWORDS and len(w) > 1
    ]


def _keyword_set(text: str) -> set[str]:
    return {t for t in _tokenize(text) if not t.isdigit()}


def score_cv(cv_markdown: str, job_description: str) -> ScoreBreakdown:
    """Compute ATS fit — 0-100 score + matched/missing keyword lists.

    Scoring: 100 * (len(jd ∩ cv) / len(jd)) capped and floored,
    plus a small penalty when the CV has fewer than 200 meaningful
    tokens (too short = ATS will likely screen out).
    """
    cv_tokens = _keyword_set(cv_markdown)
    jd_tokens = _keyword_set(job_description)
    if not jd_tokens:
        return ScoreBreakdown(
            score=0,
            keyword_matches=[],
            missing_keywords=[],
            suggestions=["Job description is empty — cannot score"],
        )

    matched = sorted(jd_tokens & cv_tokens)
    missing = sorted(jd_tokens - cv_tokens)

    raw_ratio = len(matched) / len(jd_tokens)
    score = int(min(100, max(0, raw_ratio * 100)))

    suggestions: list[str] = []
    cv_total = len(_tokenize(cv_markdown))
    if cv_total < 200:
        score = max(0, score - 10)
        suggestions.append(
            f"CV is short ({cv_total} tokens) — aim for 250-500 on a 1-page CV."
        )
    if len(missing) > len(matched):
        suggestions.append(
            f"Missing {len(missing)} JD keywords — consider weaving 5-10 of the "
            "top-priority ones into your summary or highlights."
        )
    if score >= 85:
        suggestions.append("Strong keyword coverage — ATS should let this through.")

    return ScoreBreakdown(
        score=score,
        keyword_matches=matched[:50],
        missing_keywords=missing[:50],
        suggestions=suggestions,
    )
