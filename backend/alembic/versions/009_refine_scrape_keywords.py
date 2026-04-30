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

    # Purge ALL jobs whose title lacks an AI-relevant signal. This is the
    # SQL mirror of app.utils.title_filter.is_ai_relevant — substring match
    # against the curated AI phrase list.
    conn.execute(
        sa.text(
            r"""
            DELETE FROM scraped_jobs
            WHERE LOWER(title) !~ '(ai engineer|ai/ml engineer|ai-ml engineer'
                              '|ai infrastructure|ai platform|ai research|ai applied|applied ai'
                              '|ai agent|agentic|agent engineer|ai automation|automation ai'
                              '|ai workflow|workflow ai|ai orchestration'
                              '|llm engineer|llm developer|llm ops|llmops|prompt engineer|prompt engineering'
                              '|ai video|ai image|ai creative|ai animation'
                              '|generative ai|gen ai|genai|generative video|generative image|diffusion model'
                              '|computer vision'
                              '|vibe coding|claude code|cursor ide|ai-first|ai first engineer'
                              '|founding ai|founding engineer, ai|founding engineer ai|ai-native|ai native)'
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
