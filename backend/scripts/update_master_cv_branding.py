"""Refresh the active master CV with current public branding.

Run once after changing email / handles / tagline in real life — it
clones the active master_cv row, applies the patches below, and saves
as a new active version (so old generated CVs still resolve their
historical master via master_cv_id).

Patches:
  - basics.email     → aiagent@alisadikinma.com
  - basics.url       → https://www.alisadikinma.com (header website)
  - basics.label     → punchier "#1 Champion of 26 startups from 16
                       countries" Outskill framing
  - basics.profiles  → drop twitter; add Instagram + TikTok handles
                       (@alisadikinma)
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


def _patch_content(content: dict) -> dict:
    new_content = copy.deepcopy(content) if isinstance(content, dict) else {}
    basics = dict(new_content.get("basics") or {})

    basics["email"] = NEW_EMAIL
    basics["url"] = NEW_WEBSITE
    basics["label"] = NEW_LABEL

    existing = basics.get("profiles") or []
    rebuilt: list[dict] = []
    seen_networks: set[str] = set()
    for p in existing:
        if not isinstance(p, dict):
            continue
        net = (p.get("network") or "").strip().lower()
        if net not in NEW_PROFILES_KEEP_NETWORKS:
            continue
        if net in seen_networks:
            continue
        rebuilt.append(p)
        seen_networks.add(net)
    for p in NEW_SOCIAL_PROFILES:
        if p["network"].lower() in seen_networks:
            continue
        rebuilt.append(p)
        seen_networks.add(p["network"].lower())
    basics["profiles"] = rebuilt

    new_content["basics"] = basics
    new_content["thought_leadership"] = []
    return new_content


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

        patched = _patch_content(active.content or {})
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
            f"(email={NEW_EMAIL}, website={NEW_WEBSITE}, profiles={len(new_row.content['basics']['profiles'])})"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
