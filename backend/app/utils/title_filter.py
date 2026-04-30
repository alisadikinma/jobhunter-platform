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
    "sales",
    "salesperson",
    "account manager",
    "account executive",
    "territory",
    "business development",
    "bdr",
    "sdr",
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
    "administrator",  # database admin etc. typically not AI-engineering
    "hr ",
    "human resources",
    "finance",
    "accountant",
    "legal counsel",
    "paralegal",
}

# Title fragments that signal hands-on AI/engineering work. If ANY of these
# appears in the title, the off-topic filter does NOT reject — covers cases
# like "Marketing Engineer (AI)" or "AI Sales Engineer (technical pre-sales)".
_ENGINEERING_SIGNALS = {
    "ai engineer",
    "ml engineer",
    "machine learning",
    "data engineer",
    "data scientist",
    "research engineer",
    "research scientist",
    "software engineer",
    "backend engineer",
    "frontend engineer",
    "full-stack",
    "fullstack",
    "devops",
    "site reliability",
    "platform engineer",
    "infrastructure engineer",
    "automation engineer",
    "ai automation",
    "video engineer",
    "developer advocate",
    "founding engineer",
    "computer vision",
    "nlp",
    "llm",
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
