"""email_drafts: add imap_uid / imap_folder / imap_message_id

Revision ID: 007_email_imap
Revises: 006_mailbox_config
Create Date: 2026-04-29 22:30:00.000000

Trace columns for IMAP-pushed drafts so the UI can offer "Open in Mail"
links (`imap://<host>/<folder>;UID=<uid>`) and the operator has a
verifiable audit trail of which drafts landed in the mailbox.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007_email_imap"
down_revision: Union[str, None] = "006_mailbox_config"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("email_drafts", sa.Column("imap_uid", sa.String(64)))
    op.add_column("email_drafts", sa.Column("imap_folder", sa.String(100)))
    op.add_column("email_drafts", sa.Column("imap_message_id", sa.String(255)))


def downgrade() -> None:
    op.drop_column("email_drafts", "imap_message_id")
    op.drop_column("email_drafts", "imap_folder")
    op.drop_column("email_drafts", "imap_uid")
