"""mailbox_config singleton table — IMAP/SMTP creds, Fernet-encrypted password

Revision ID: 006_mailbox_config
Revises: 005_extend_sources
Create Date: 2026-04-29 22:00:00.000000

Holds custom-domain mailer credentials so they can be CRUD'd via UI
instead of ssh-edit-.env. Single-row table — `id=1` is the only row.

The `password_encrypted` column stores a Fernet-encrypted string
(same key as `apify_accounts.api_token`).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006_mailbox_config"
down_revision: Union[str, None] = "005_extend_sources"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mailbox_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("smtp_host", sa.String(255), nullable=False, server_default=""),
        sa.Column("smtp_port", sa.Integer, nullable=False, server_default="465"),
        sa.Column("imap_host", sa.String(255), nullable=False, server_default=""),
        sa.Column("imap_port", sa.Integer, nullable=False, server_default="993"),
        sa.Column("username", sa.String(255), nullable=False, server_default=""),
        sa.Column("password_encrypted", sa.Text, nullable=False, server_default=""),
        sa.Column("from_address", sa.String(255), nullable=False, server_default=""),
        sa.Column("from_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("drafts_folder", sa.String(100), nullable=False, server_default="Drafts"),
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
    # Enforce singleton — only one row allowed.
    op.create_check_constraint("ck_mailbox_singleton", "mailbox_config", "id = 1")


def downgrade() -> None:
    op.drop_constraint("ck_mailbox_singleton", "mailbox_config", type_="check")
    op.drop_table("mailbox_config")
