"""Refresh the active master CV with current public branding + employee-friendly framing.

Run once after changing email / handles / tagline in real life — it
clones the active master_cv row, applies the patches below, and saves
as a new active version (so old generated CVs still resolve their
historical master via master_cv_id).

Patches:
  - basics.email      → aiagent@alisadikinma.com
  - basics.url        → https://www.alisadikinma.com (header website)
  - basics.label      → punchier "#1 Champion of 26 startups from 16
                        countries" Outskill framing (no "Founder",
                        no "Solopreneur" — flagged as risk signals
                        by US remote recruiters)
  - basics.profiles   → drop twitter; add Instagram + TikTok handles
                        (@alisadikinma)
  - basics.summary_*  → scrub founder/solopreneur framing → reframe
                        same achievements as engineer-style work so
                        US remote-job ATS / recruiters don't flag the
                        candidate as a flight risk
  - work[].position   → any "Founder" / "Co-founder" / "Founding *"
                        rewritten to "Lead AI Engineer" so the same
                        company / dates / achievements stay, just
                        without owner-mode framing
  - thought_leadership → cleared (the renderer no longer emits the
                        section, but we wipe the data too so future
                        templates don't accidentally resurrect it)

Usage:
  cd backend
  python -m scripts.update_master_cv_branding

Idempotent: re-running just bumps the version again with the same
content — no harm, but no point either. Check `version` in the output
to know whether anything changed.
"""
from __future__ import annotations

import copy
import re
import sys
from pathlib import Path

# Allow `python scripts/update_master_cv_branding.py` from backend/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.cv import MasterCV  # noqa: E402

NEW_EMAIL = "aiagent@alisadikinma.com"
NEW_WEBSITE = "https://www.alisadikinma.com"
NEW_LABEL = (
    "#1 Champion at Outskill Demo Day (beating 26 startups from 16 countries) "
    "· Vibe Coding · AI Agents · Automation · Video Gen · Batam, working globally"
)
NEW_PROFILES_KEEP_NETWORKS = {"github", "linkedin"}
NEW_SOCIAL_PROFILES = [
    {
        "network": "Instagram",
        "username": "alisadikinma",
        "url": "https://www.instagram.com/alisadikinma",
    },
    {
        "network": "TikTok",
        "username": "alisadikinma",
        "url": "https://www.tiktok.com/@alisadikinma",
    },
]

# Replacement substitution table for founder-style framing → engineer-style framing.
# Order matters: longer/more-specific patterns FIRST so they win against shorter ones.
# All patterns are case-insensitive but preserve case where possible via callable.
_FOUNDER_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Whole-phrase substitutions
    (re.compile(r"\bAI Solopreneur Studio\b\s*[·\-—]?\s*", re.IGNORECASE), ""),
    (re.compile(r"\bFounder of INDUSIA\.?ai\b", re.IGNORECASE), "AI Engineer on INDUSIA.ai"),
    (re.compile(r"\bFounder & CEO of\b", re.IGNORECASE), "Lead AI Engineer at"),
    (re.compile(r"\bFounder and CEO of\b", re.IGNORECASE), "Lead AI Engineer at"),
    (re.compile(r"\bCo-Founder of\b", re.IGNORECASE), "Lead AI Engineer at"),
    (re.compile(r"\bCofounder of\b", re.IGNORECASE), "Lead AI Engineer at"),
    (re.compile(r"\bFounder of\b", re.IGNORECASE), "AI Engineer at"),
    (re.compile(r"\bFounding (Engineer|CTO|CEO|Partner|Member)\b", re.IGNORECASE), r"Lead \1"),
    # Solo-mode phrasing → builder phrasing
    (re.compile(r"\bI run INDUSIA\.?ai solo\b[ —–-]*\s*", re.IGNORECASE), "I built INDUSIA.ai — "),
    (re.compile(r"\bI run INDUSIA\.?ai\b", re.IGNORECASE), "I built INDUSIA.ai"),
    (re.compile(r"\brun(s|ning)? .*? solo\b", re.IGNORECASE), r"built it"),
    (re.compile(r"\bone[- ]builder can ship\b", re.IGNORECASE), "one engineer can ship"),
    (re.compile(r"\bour AI Visual Inspection\b", re.IGNORECASE), "the AI Visual Inspection platform"),
    # Standalone token cleanup
    (re.compile(r"\bSolopreneur(s|ship)?\b", re.IGNORECASE), "Engineer"),
    (re.compile(r"\bSolo Founder\b", re.IGNORECASE), "Lead Engineer"),
    (re.compile(r"\bIndie Founder\b", re.IGNORECASE), "Independent Engineer"),
]


def _scrub_founder_framing(text: str | None) -> str | None:
    """Apply the founder→engineer rewrites to free-text fields.

    Returns the rewritten string. None / non-string passes through unchanged.
    Repeated runs are no-ops because every pattern's RHS no longer matches its LHS.
    """
    if not isinstance(text, str) or not text:
        return text
    out = text
    for pat, repl in _FOUNDER_PATTERNS:
        out = pat.sub(repl, out)
    # Collapse any double-space / orphaned punctuation introduced by deletions.
    out = re.sub(r" {2,}", " ", out)
    out = re.sub(r"\s*([·,;])\s*([·,;])\s*", r"\1 ", out)
    out = re.sub(r"^[ ·,;\-—]+", "", out)
    out = re.sub(r"[ ·,;\-—]+$", "", out)
    return out.strip()


def _scrub_position(position: str | None) -> str | None:
    """Rewrite a `work[].position` if it screams 'founder'.

    INDUSIA.ai etc. stays in `company`; we only neutralise the role title
    so the same achievements read as engineering work instead of ownership.
    """
    if not isinstance(position, str) or not position:
        return position
    p = position.strip()
    p_lower = p.lower()
    if any(
        marker in p_lower
        for marker in (
            "founder", "co-founder", "cofounder", "founding", "ceo",
        )
    ):
        # Map common variants to the safest neutral title for an AI-platform builder.
        if "engineer" in p_lower or "cto" in p_lower or "tech" in p_lower:
            return "Lead AI Engineer"
        if "ceo" in p_lower:
            return "Lead AI Engineer"
        return "Lead AI Engineer"
    if "solopreneur" in p_lower:
        return "AI Engineer"
    return position


def _patch_content(content: dict) -> tuple[dict, dict]:
    """Apply all branding + framing patches.

    Returns (new_content, change_log) — the change_log is a flat dict of
    counters useful for the operator-facing summary line.
    """
    new_content = copy.deepcopy(content) if isinstance(content, dict) else {}
    log: dict[str, int] = {
        "summary_scrubbed": 0,
        "positions_scrubbed": 0,
        "profiles_added": 0,
        "profiles_dropped": 0,
    }
    basics = dict(new_content.get("basics") or {})

    # --- Static branding fields ----------------------------------
    basics["email"] = NEW_EMAIL
    basics["url"] = NEW_WEBSITE
    basics["label"] = NEW_LABEL

    # --- Profiles: drop twitter, add IG + TikTok -----------------
    existing = basics.get("profiles") or []
    rebuilt: list[dict] = []
    seen_networks: set[str] = set()
    dropped = 0
    for p in existing:
        if not isinstance(p, dict):
            continue
        net = (p.get("network") or "").strip().lower()
        if net not in NEW_PROFILES_KEEP_NETWORKS:
            dropped += 1
            continue
        if net in seen_networks:
            continue
        rebuilt.append(p)
        seen_networks.add(net)
    added = 0
    for p in NEW_SOCIAL_PROFILES:
        if p["network"].lower() in seen_networks:
            continue
        rebuilt.append(p)
        seen_networks.add(p["network"].lower())
        added += 1
    basics["profiles"] = rebuilt
    log["profiles_added"] = added
    log["profiles_dropped"] = dropped

    # --- Free-text scrub: summary fields -------------------------
    for key in ("summary", "summary_text"):
        if key in basics:
            before = basics[key]
            scrubbed = _scrub_founder_framing(before)
            if scrubbed != before:
                log["summary_scrubbed"] += 1
            basics[key] = scrubbed

    # --- Work entries: founder-mode position titles --------------
    work = list(new_content.get("work") or [])
    rewritten_work: list[dict] = []
    for w in work:
        if not isinstance(w, dict):
            rewritten_work.append(w)
            continue
        w_copy = dict(w)
        before = w_copy.get("position")
        after = _scrub_position(before)
        if after != before:
            log["positions_scrubbed"] += 1
        if after is not None:
            w_copy["position"] = after
        # Also scrub free-text summary inside each work entry, same patterns.
        if "summary" in w_copy:
            w_copy["summary"] = _scrub_founder_framing(w_copy.get("summary"))
        rewritten_work.append(w_copy)
    new_content["work"] = rewritten_work

    new_content["basics"] = basics
    new_content["thought_leadership"] = []
    return new_content, log


def main() -> int:
    db = SessionLocal()
    try:
        active = db.execute(
            select(MasterCV)
            .where(MasterCV.is_active.is_(True))
            .order_by(MasterCV.version.desc())
            .limit(1)
        ).scalar_one_or_none()
        if active is None:
            print("No active master CV found — nothing to update.", file=sys.stderr)
            return 1

        patched, log = _patch_content(active.content or {})
        if patched == active.content:
            print(f"master_cv v{active.version} already matches new branding — no-op.")
            return 0

        active.is_active = False
        new_row = MasterCV(
            version=active.version + 1,
            content=patched,
            raw_markdown=active.raw_markdown,
            is_active=True,
            source_type="branding-refresh",
        )
        db.add(new_row)
        db.commit()
        db.refresh(new_row)
        print(
            f"OK · master_cv v{active.version} -> v{new_row.version} "
            f"(email={NEW_EMAIL}, website={NEW_WEBSITE}, "
            f"profiles=+{log['profiles_added']}/-{log['profiles_dropped']}, "
            f"summary_scrubbed={log['summary_scrubbed']}, "
            f"positions_scrubbed={log['positions_scrubbed']})"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
