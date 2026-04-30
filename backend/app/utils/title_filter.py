"""Off-topic title rejection — stop sales/recruiting roles entering the AI funnel.

RemoteOK's keyword match is loose: a sales role at an AI company ("TENEX.AI")
or any role whose description mentions "AI" gets through. We add a second-pass
title-level reject so the resulting list stays focused on actual builder roles.

The rejected list is intentionally narrow. False negatives (a real AI role
slips through) are far worse than false positives (a sales role gets in), so
we only reject when the title matches one of these tokens AND lacks any
explicit engineering / ML signal.
"""
import re

# Tokens that almost never coexist with hands-on AI engineering work. Match
# is whole-word, case-insensitive — so "AI Engineer" doesn't trip "engineer"
# but "Sales Engineer" does (no AI signal in the title).
_OFFTOPIC_TOKENS = {
    # Sales / GTM
    "sales",
    "salesperson",
    "account manager",
    "account executive",
    "territory",
    "business development",
    "bdr",
    "sdr",
    # Recruiting / HR / Ops
    "recruiter",
    "recruiting",
    "talent acquisition",
    "marketing",  # rejected unless paired with engineering signal — see _ENGINEERING_SIGNALS
    "vice president",
    "vp ",
    "managing director",
    "regional",
    "customer success",
    "support specialist",
    "support representative",
    "executive assistant",
    "office manager",
    "administrative",
    "administrator",
    "hr ",
    "human resources",
    "finance",
    "accountant",
    "legal counsel",
    "paralegal",
    # Non-AI engineering — these were leaking through. Generic infra/devops
    # roles aren't what we're hunting; AI roles say "AI engineer" or
    # "ML engineer" in the title, not "DevOps Engineer".
    "devops",
    "dev ops",
    "sre",
    "site reliability",
    "platform engineer",
    "infrastructure engineer",
    "network engineer",
    "security engineer",
    "cloud engineer",
    "systems engineer",
    "system administrator",
    "sysadmin",
    "qa engineer",
    "quality assurance",
    "test engineer",
    "solution architect",
    "solutions architect",
    "data engineer",
    "data scientist",
    "data analyst",
    "data product manager",
    "product manager",
    "product owner",
    "project manager",
    "program manager",
    "scrum master",
    "ui designer",
    "ux designer",
    "graphic designer",
}

# Title fragments that signal hands-on AI work. ONLY AI-explicit phrases —
# generic "software engineer" / "devops" do NOT belong here, because we want
# to reject them when they have no AI signal.
_ENGINEERING_SIGNALS = {
    "ai engineer",
    "ai/ml",
    "ai-ml",
    "ai automation",
    "ai infrastructure",
    "ai platform",
    "ai research",
    "ai video",
    "ai creative",
    "ml engineer",
    "mlops",
    "machine learning engineer",
    "machine learning scientist",
    "applied scientist",
    "research scientist, ai",
    "computer vision",
    "nlp engineer",
    "llm engineer",
    "llm",
    "generative ai",
    "gen ai",
    "genai",
    "prompt engineer",
    "automation engineer",  # narrow — only when explicitly automation-flavored
    "founding ai",
    "founding engineer, ai",
    "vibe coding",
    "claude code",
    "agent engineer",
    "agentic",
}


def is_offtopic_title(title: str | None) -> bool:
    """True if the title is an off-topic role we should drop at scrape time.

    Matches whole-word, case-insensitive. Returns False if the title also
    contains an engineering-signal phrase (the AI-positive override).
    """
    if not title:
        return False
    t = title.lower().strip()

    # Fast accept: any engineering signal short-circuits the rejection.
    if any(sig in t for sig in _ENGINEERING_SIGNALS):
        return False

    # Word-boundary match for each off-topic token.
    for token in _OFFTOPIC_TOKENS:
        # `\b` doesn't work cleanly for tokens containing spaces — use a
        # space-padded regex with start/end anchors as a fallback.
        pattern = r"\b" + re.escape(token.strip()) + r"\b"
        if re.search(pattern, t):
            return True
    return False
