"""Portfolio auditor tests — uses tmp_path as the scan root."""
import pytest

from app.models.portfolio_asset import PortfolioAsset
from app.services.portfolio_auditor import scan

pytestmark = pytest.mark.integration


_PLUGIN_CLAUDE = """# Carousel Generator

Cinematic AI image prompt generator for social media carousel content.
Uses Nano Banana Pro for fast iteration.

## Tech stack: Python, Claude CLI, MCP server

Extra notes below.
"""


_PROJECT_CLAUDE = """# Portfolio_v2

Laravel + Vue 3 public portfolio for alisadikinma.com.

Tech stack: Laravel, Vue, TypeScript, MySQL
"""


def _make_tree(tmp_path, entries: dict[str, str]):
    for rel_dir, claude_md in entries.items():
        d = tmp_path / rel_dir
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text(claude_md, encoding="utf-8")


def test_scan_creates_drafts_for_each_claude_md(pg_session, tmp_path):
    _make_tree(tmp_path, {
        "ai-image-carousel-prompt-gen": _PLUGIN_CLAUDE,
        "Portfolio_v2": _PROJECT_CLAUDE,
    })

    result = scan(pg_session, [str(tmp_path)])
    assert result.new_drafts == 2
    assert result.updated == 0

    rows = pg_session.query(PortfolioAsset).order_by(PortfolioAsset.id).all()
    titles = {r.title for r in rows}
    assert "Carousel Generator" in titles
    assert "Portfolio_v2" in titles
    assert all(r.status == "draft" and r.auto_generated for r in rows)


def test_scan_classifies_variants_from_keywords(pg_session, tmp_path):
    video_md = "# Video Promo Engine\n\nRunway + Veo pipeline for agency videos.\n"
    auto_md = "# Automation Kit\n\nn8n + langchain agents orchestrating ops.\n"
    _make_tree(tmp_path, {"video-engine": video_md, "auto-kit": auto_md})

    scan(pg_session, [str(tmp_path)])
    rows = {r.title: r for r in pg_session.query(PortfolioAsset).all()}
    assert "ai_video" in (rows["Video Promo Engine"].relevance_hint or [])
    assert "ai_automation" in (rows["Automation Kit"].relevance_hint or [])


def test_scan_infers_tech_stack_from_stack_line(pg_session, tmp_path):
    md = "# X\n\nDesc here.\n\nTech stack: FastAPI, PostgreSQL, Claude CLI\n"
    _make_tree(tmp_path, {"x": md})

    scan(pg_session, [str(tmp_path)])
    row = pg_session.query(PortfolioAsset).one()
    assert "FastAPI" in (row.tech_stack or [])
    assert "PostgreSQL" in (row.tech_stack or [])


def test_scan_is_idempotent_for_unchanged_content(pg_session, tmp_path):
    _make_tree(tmp_path, {"plugin-a": _PLUGIN_CLAUDE})
    first = scan(pg_session, [str(tmp_path)])
    second = scan(pg_session, [str(tmp_path)])
    assert first.new_drafts == 1
    assert second.new_drafts == 0
    assert second.skipped == 1  # the unchanged file was skipped


def test_scan_updates_draft_when_content_changes(pg_session, tmp_path):
    _make_tree(tmp_path, {"plugin-b": _PLUGIN_CLAUDE})
    scan(pg_session, [str(tmp_path)])

    updated_md = _PLUGIN_CLAUDE.replace("Carousel Generator", "Carousel Generator v2")
    (tmp_path / "plugin-b" / "CLAUDE.md").write_text(updated_md, encoding="utf-8")

    result = scan(pg_session, [str(tmp_path)])
    assert result.updated == 1

    row = pg_session.query(PortfolioAsset).one()
    assert row.title == "Carousel Generator v2"


def test_scan_does_not_overwrite_published_relevance_hint(pg_session, tmp_path):
    _make_tree(tmp_path, {"plug": _PLUGIN_CLAUDE})
    scan(pg_session, [str(tmp_path)])

    row = pg_session.query(PortfolioAsset).one()
    row.status = "published"
    row.relevance_hint = ["ai_video"]  # human-curated
    pg_session.commit()

    # Update the source and rescan:
    changed = _PLUGIN_CLAUDE + "\nn8n workflow pipeline."
    (tmp_path / "plug" / "CLAUDE.md").write_text(changed, encoding="utf-8")
    scan(pg_session, [str(tmp_path)])

    pg_session.refresh(row)
    # relevance_hint kept because status != 'draft'
    assert row.relevance_hint == ["ai_video"]


def test_scan_skips_missing_root(pg_session, tmp_path):
    missing = tmp_path / "does-not-exist"
    result = scan(pg_session, [str(missing)])
    assert result.skipped == 1
    assert result.new_drafts == 0
