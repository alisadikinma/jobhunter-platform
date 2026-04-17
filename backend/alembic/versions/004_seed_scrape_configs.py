"""seed 3 variant-targeted scrape configs

Revision ID: 004_seed_configs
Revises: 003_fk_tz_jsonb
Create Date: 2026-04-17 13:00:00.000000

Adds the three target roles from the brainstorm (vibe_coding, ai_automation,
ai_video) as default scrape_configs, each running every 3h on all 5 free API
sources plus JobSpy and Wellfound.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004_seed_configs"
down_revision: Union[str, None] = "003_fk_tz_jsonb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SOURCES = ["remoteok", "hn_algolia", "arbeitnow", "adzuna", "hiring_cafe", "jobspy"]


_SEED_CONFIGS = [
    {
        "name": "Vibe Coding Remote (US/EU/AU)",
        "variant_target": "vibe_coding",
        "keywords": [
            "vibe coding", "claude code", "rapid build", "full-stack",
            "AI engineer", "founding engineer",
        ],
        "locations": ["USA", "Europe", "Australia"],
    },
    {
        "name": "AI Automation Engineer Remote",
        "variant_target": "ai_automation",
        "keywords": [
            "AI automation", "claude CLI", "pipeline", "MCP",
            "n8n", "langchain", "workflow automation",
        ],
        "locations": ["USA", "Europe"],
    },
    {
        "name": "AI Video Generation Specialist",
        "variant_target": "ai_video",
        "keywords": [
            "AI video", "runway", "veo", "video pipeline",
            "generative video", "AI creative",
        ],
        "locations": ["USA", "Europe", "Remote"],
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    for cfg in _SEED_CONFIGS:
        # Skip if a config with the same variant_target already exists
        # (idempotent re-runs after a schema reset).
        existing = conn.execute(
            sa.text("SELECT id FROM scrape_configs WHERE variant_target = :v"),
            {"v": cfg["variant_target"]},
        ).scalar()
        if existing:
            continue

        conn.execute(
            sa.text("""
                INSERT INTO scrape_configs
                    (name, is_active, variant_target, keywords, locations,
                     sources, remote_only, max_results_per_source,
                     cron_expression)
                VALUES
                    (:name, TRUE, :variant_target, :keywords, :locations,
                     :sources, TRUE, 30, '0 */3 * * *')
            """),
            {
                "name": cfg["name"],
                "variant_target": cfg["variant_target"],
                "keywords": cfg["keywords"],
                "locations": cfg["locations"],
                "sources": _SOURCES,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM scrape_configs WHERE variant_target IN (:v1, :v2, :v3)"),
        {"v1": "vibe_coding", "v2": "ai_automation", "v3": "ai_video"},
    )
