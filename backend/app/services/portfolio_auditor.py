"""Hybrid portfolio audit — scans plugin caches + project dirs, creates
DRAFT PortfolioAsset rows for Ali to review/publish.

Idempotent: detects existing rows by source_path + content_hash. A later
re-scan with a changed CLAUDE.md updates the draft in place rather than
inserting a new one.
"""
import hashlib
import logging
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.portfolio_asset import PortfolioAsset
from app.schemas.portfolio import PortfolioAuditResult

log = logging.getLogger(__name__)


_VARIANT_SIGNALS: dict[str, tuple[str, ...]] = {
    "vibe_coding": (
        "claude code", "claude cli", "cursor", "rapid prototyping",
        "vibe coding", "ship fast", "mvp builder", "founding engineer",
    ),
    "ai_automation": (
        "automation", "workflow", "n8n", "zapier", "mcp server",
        "langchain", "langgraph", "agent", "pipeline",
    ),
    "ai_video": (
        "runway", "veo", "pika", "nano banana", "generative video",
        "ai video", "video pipeline", "stable diffusion video",
    ),
}

_STACK_HINT = re.compile(
    r"(?:tech\s*stack|stack|dependencies|frameworks?)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)
_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _classify_variants(text_lc: str) -> list[str]:
    found = [
        variant
        for variant, signals in _VARIANT_SIGNALS.items()
        if any(s in text_lc for s in signals)
    ]
    return found or ["vibe_coding"]  # default bucket


def _infer_stack(content: str) -> list[str]:
    """Pull a tech list from a 'Tech stack:' line or an inline bullet list."""
    candidates: list[str] = []
    for line in content.splitlines():
        m = _STACK_HINT.search(line)
        if not m:
            continue
        raw = m.group(1)
        candidates.extend(
            t.strip(" `*_[]").strip()
            for t in re.split(r"[,;/]| and ", raw)
            if t.strip()
        )
        if candidates:
            break
    # Dedupe preserving order; cap at 12.
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        low = c.lower()
        if low and low not in seen and len(c) <= 40:
            seen.add(low)
            out.append(c)
    return out[:12]


def _parse_claude_md(path: Path) -> dict:
    content = path.read_text(encoding="utf-8", errors="ignore")
    h1 = _H1.search(content)
    title = h1.group(1).strip() if h1 else path.parent.name

    # First paragraph after title, truncated.
    body = content[h1.end():] if h1 else content
    first_para = next(
        (chunk.strip() for chunk in re.split(r"\n\s*\n", body.strip()) if chunk.strip()),
        "",
    )
    description = first_para[:300]

    lc = content.lower()
    return {
        "title": title[:255],
        "description": description,
        "tech_stack": _infer_stack(content),
        "relevance_hint": _classify_variants(lc),
        "content_hash": _hash_content(content),
    }


def _iter_claude_md_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    # One-level and two-level scan is enough for our layout:
    #   ~/.claude/plugins/cache/<plugin>/CLAUDE.md
    #   D:/Projects/<proj>/CLAUDE.md
    found: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        claude_md = child / "CLAUDE.md"
        if claude_md.is_file():
            found.append(claude_md)
    return found


def scan(db: Session, scan_paths: list[str]) -> PortfolioAuditResult:
    new_drafts = 0
    updated = 0
    skipped = 0
    errors: list[str] = []

    for raw in scan_paths:
        root = Path(raw).expanduser()
        if not root.exists():
            log.info("skip non-existent scan path: %s", root)
            skipped += 1
            continue

        for claude_md in _iter_claude_md_under(root):
            try:
                parsed = _parse_claude_md(claude_md)
            except Exception as e:
                errors.append(f"parse error at {claude_md}: {e}")
                continue

            source_path = str(claude_md)
            existing = (
                db.query(PortfolioAsset)
                .filter(PortfolioAsset.source_path == source_path)
                .one_or_none()
            )
            content_hash = parsed.pop("content_hash")
            metrics = {"content_hash": content_hash}

            if existing is None:
                db.add(
                    PortfolioAsset(
                        asset_type="plugin" if "plugin" in source_path else "project",
                        title=parsed["title"],
                        description=parsed["description"],
                        tech_stack=parsed["tech_stack"],
                        relevance_hint=parsed["relevance_hint"],
                        metrics=metrics,
                        status="draft",
                        auto_generated=True,
                        source_path=source_path,
                        display_priority=50,
                    )
                )
                new_drafts += 1
                continue

            # Existing row: update only if the CLAUDE.md actually changed.
            prev_hash = (existing.metrics or {}).get("content_hash")
            if prev_hash == content_hash:
                skipped += 1
                continue

            existing.title = parsed["title"]
            existing.description = parsed["description"]
            existing.tech_stack = parsed["tech_stack"]
            # Don't overwrite a human's curated relevance_hint once reviewed.
            if existing.status == "draft":
                existing.relevance_hint = parsed["relevance_hint"]
            existing.metrics = metrics
            updated += 1

    db.commit()
    return PortfolioAuditResult(
        new_drafts=new_drafts,
        updated=updated,
        skipped=skipped,
        errors=errors,
    )
