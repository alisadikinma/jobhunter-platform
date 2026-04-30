"""replace firecrawl_config singleton with firecrawl_accounts pool

Revision ID: 011_firecrawl_pool
Revises: 010_firecrawl_config
Create Date: 2026-04-30 14:00:00.000000

The previous singleton model couldn't rotate when one Firecrawl free-tier
account hit its credit cap. This switches to a multi-account pool with
the same shape as `apify_accounts`: per-account credit tracking,
priority/status/cooldown, FOR UPDATE SKIP LOCKED acquisition.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "011_firecrawl_pool"
down_revision: Union[str, None] = "010_firecrawl_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the previous singleton table — never had production data since
    # 010 was deployed only for one revision before being replaced.
    op.drop_constraint("ck_firecrawl_singleton", "firecrawl_config", type_="check")
    op.drop_table("firecrawl_config")

    op.create_table(
        "firecrawl_accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, server_default=""),
        sa.Column(
            "api_url",
            sa.String(500),
            nullable=False,
            server_default="https://api.firecrawl.dev",
        ),
        sa.Column("api_token", sa.Text, nullable=False, server_default=""),
        sa.Column("priority", sa.Integer, server_default="100"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("monthly_credit_usd", sa.Numeric(10, 2), server_default="0.50"),
        sa.Column("credit_used_usd", sa.Numeric(10, 2), server_default="0.00"),
        sa.Column("quota_reset_at", sa.DateTime(timezone=True)),
        sa.Column("exhausted_at", sa.DateTime(timezone=True)),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("cooldown_until", sa.DateTime(timezone=True)),
        sa.Column("consecutive_failures", sa.Integer, server_default="0"),
        sa.Column("last_error", sa.Text),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("idx_firecrawl_status", "firecrawl_accounts", ["status", "priority"])
    op.create_index("idx_firecrawl_cooldown", "firecrawl_accounts", ["cooldown_until"])


def downgrade() -> None:
    op.drop_index("idx_firecrawl_cooldown", table_name="firecrawl_accounts")
    op.drop_index("idx_firecrawl_status", table_name="firecrawl_accounts")
    op.drop_table("firecrawl_accounts")

    op.create_table(
        "firecrawl_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("api_url", sa.String(500), nullable=False, server_default="https://api.firecrawl.dev"),
        sa.Column("api_key_encrypted", sa.Text, nullable=False, server_default=""),
        sa.Column("timeout_s", sa.Integer, nullable=False, server_default="60"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_test_at", sa.DateTime(timezone=True)),
        sa.Column("last_test_status", sa.String(20)),
        sa.Column("last_test_message", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_check_constraint("ck_firecrawl_singleton", "firecrawl_config", "id = 1")
