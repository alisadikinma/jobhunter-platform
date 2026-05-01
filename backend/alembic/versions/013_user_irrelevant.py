"""add scraped_jobs.user_irrelevant column for not-relevant feedback

Revision ID: 013_user_irrelevant
Revises: 012_firecrawl_credits
Create Date: 2026-05-01 00:00:00.000000

Lets the user mark jobs as 'not relevant' from /jobs/[id]. Flagged jobs
are excluded from the default list view but accessible via
?include_irrelevant=true. Future Phase 6 will use this signal to train
the title_filter allowlist or scoring weights.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013_user_irrelevant"
down_revision: Union[str, None] = "012_firecrawl_credits"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scraped_jobs",
        sa.Column(
            "user_irrelevant",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "idx_jobs_user_irrelevant",
        "scraped_jobs",
        ["user_irrelevant"],
    )


def downgrade() -> None:
    op.drop_index("idx_jobs_user_irrelevant", table_name="scraped_jobs")
    op.drop_column("scraped_jobs", "user_irrelevant")
