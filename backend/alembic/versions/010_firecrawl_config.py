"""firecrawl_config singleton table — Firecrawl API credentials, Fernet-encrypted

Revision ID: 010_firecrawl_config
Revises: 009_refine_keywords
Create Date: 2026-04-30 12:00:00.000000

Holds Firecrawl API URL + key so they can be CRUD'd via UI instead of
ssh-edit-.env. Single-row table — `id=1` is the only row. Uses the same
Fernet key as `mailbox_config.password_encrypted` and
`apify_accounts.api_token_encrypted`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010_firecrawl_config"
down_revision: Union[str, None] = "009_refine_keywords"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "firecrawl_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "api_url",
            sa.String(500),
            nullable=False,
            server_default="https://api.firecrawl.dev",
        ),
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


def downgrade() -> None:
    op.drop_constraint("ck_firecrawl_singleton", "firecrawl_config", type_="check")
    op.drop_table("firecrawl_config")
