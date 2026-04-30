"""AI-relevance allowlist — keep only AI Agent / Automation / Image+Video / Vibe Coding.

Scope is intentionally narrow: the user is hunting for ONE of four tracks:
- AI Agent / Agentic / AI Automation
- AI Image generation
- AI Video generation
- Vibe Coding (Claude Code, Cursor, AI-first dev tools)

Anything else — DevOps, Cloud Architect, Data Engineer, ML Engineer (generic
model training), Product Manager, Account Management, Digital Media — must be
rejected even if the JD body happens to mention "ai" or "automation".

Strategy: ALLOWLIST on the title. The title must explicitly contain one of
the AI-relevant phrases below. Substring (not whole-word) so "AI/ML
Platform Engineer" matches via "ai/ml" even though it'd fail \\b.

Why not blocklist: the leak set is unbounded (every new role title we
haven't seen). Allowlist forces a positive AI signal in the title itself
and keeps false positives at zero.
"""
from __future__ import annotations


_AI_TITLE_PHRASES: tuple[str, ...] = (
    # AI Engineering — generic AI builder roles
    "ai engineer",
    "ai/ml engineer",
    "ai-ml engineer",
    "ai infrastructure",
    "ai platform",
    "ai research",
    "ai applied",
    "applied ai",
    # AI Agent / Automation
    "ai agent",
    "ai agents",
    "agentic",
    "agent engineer",
    "ai automation",
    "automation ai",
    "workflow ai",
    "ai workflow",
    "ai orchestration",
    # LLM-focused
    "llm engineer",
    "llm developer",
    "llm ops",
    "llmops",
    "prompt engineer",
    "prompt engineering",
    # AI Video / Image / Creative
    "ai video",
    "ai image",
    "ai creative",
    "ai animation",
    "generative ai",
    "gen ai",
    "genai",
    "generative video",
    "generative image",
    "diffusion model",
    "computer vision",  # user is open to vision/CV roles within video gen
    # Vibe coding / dev tools
    "vibe coding",
    "claude code",
    "cursor ide",
    "ai-first",
    "ai first engineer",
    "founding ai",
    "founding engineer, ai",
    "founding engineer ai",
    "ai-native",
    "ai native",
)


def is_ai_relevant(title: str | None) -> bool:
    """True if the title contains an explicit AI-relevant phrase.

    Substring match, case-insensitive. Empty / None returns False.
    """
    if not title:
        return False
    t = title.lower()
    return any(phrase in t for phrase in _AI_TITLE_PHRASES)


def is_offtopic_title(title: str | None) -> bool:
    """Inverse of is_ai_relevant. Kept as the name scrapers/tests already import.

    Rejects any title that does NOT contain an AI-relevant phrase.
    """
    if not title:
        # Empty title = unknown intent. We don't reject (the scraper layer
        # decides what to do with title-less rows; usually they're dropped
        # earlier on schema-level validation).
        return False
    return not is_ai_relevant(title)
