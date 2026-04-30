"""tighten ai_automation/vibe_coding/ai_video keywords

Revision ID: 009_refine_keywords
Revises: 008_cleanup_jobs
Create Date: 2026-04-30 00:00:00.000000

The seed keywords from migration 004 were too loose — "pipeline" matched
"CI/CD pipeline" in every DevOps JD, "workflow automation" caught generic
ops roles. This migration replaces the keyword arrays on existing rows
with AI-explicit tokens only. New configs will inherit these via 004 if
the DB ever resets, but in practice we update-in-place here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009_refine_keywords"
down_revision: Union[str, None] = "008_cleanup_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_REFINED = {
    "vibe_coding": [
        "vibe coding",
        "claude code",
        "cursor ide",
        "ai-first engineer",
        "ai dev tool",
        "founding engineer ai",
        "ai pair programming",
    ],
    "ai_automation": [
        "langchain",
        "llamaindex",
        "ai agent",
        "agentic",
        "mcp server",
        "ai workflow",
        "llm engineer",
        "ai infrastructure",
        "ai automation",
        "claude cli",
        "n8n",
    ],
    "ai_video": [
        "runway ml",
        "veo video",
        "sora video",
        "generative video",
        "diffusion video",
        "ai animation",
        "video gen ai",
        "ai video creator",
        "ai video",
    ],
}


def upgrade() -> None:
    conn = op.get_bind()
    for variant, kws in _REFINED.items():
        conn.execute(
            sa.text(
                "UPDATE scrape_configs SET keywords = :kws WHERE variant_target = :v"
            ),
            {"kws": kws, "v": variant},
        )

    # Purge previously-leaked off-topic jobs from `scraped_jobs`. These
    # entered before the title_filter was tightened (DevOps/Data PM/etc.
    # tagged as ai_automation). We reject any job whose title contains an
    # off-topic token AND lacks any explicit AI signal — same shape as
    # title_filter.is_offtopic_title, but inlined as SQL so we don't
    # depend on Python during migration.
    conn.execute(
        sa.text(
            """
            DELETE FROM scraped_jobs
            WHERE
                LOWER(title) ~* '\\m(devops|sre|site reliability|platform engineer'
                            '|infrastructure engineer|network engineer|security engineer'
                            '|cloud engineer|systems engineer|sysadmin|qa engineer'
                            '|test engineer|solution architect|data engineer'
                            '|data scientist|data analyst|data product manager'
                            '|product manager|product owner|project manager'
                            '|program manager|scrum master|ui designer|ux designer'
                            '|graphic designer)\\M'
                AND LOWER(title) !~* '\\m(ai engineer|ai/ml|ai automation|ai infrastructure'
                                  '|ai platform|ai research|ai video|ai creative'
                                  '|ml engineer|mlops|machine learning|computer vision'
                                  '|nlp|llm|generative ai|gen ai|genai|prompt engineer'
                                  '|vibe coding|claude code|agentic|founding ai)\\M'
            """
        )
    )


def downgrade() -> None:
    # Restore the loose keywords from migration 004.
    legacy = {
        "vibe_coding": [
            "vibe coding", "claude code", "rapid build", "full-stack",
            "AI engineer", "founding engineer",
        ],
        "ai_automation": [
            "AI automation", "claude CLI", "pipeline", "MCP",
            "n8n", "langchain", "workflow automation",
        ],
        "ai_video": [
            "AI video", "runway", "veo", "video pipeline",
            "generative video", "AI creative",
        ],
    }
    conn = op.get_bind()
    for variant, kws in legacy.items():
        conn.execute(
            sa.text(
                "UPDATE scrape_configs SET keywords = :kws WHERE variant_target = :v"
            ),
            {"kws": kws, "v": variant},
        )
