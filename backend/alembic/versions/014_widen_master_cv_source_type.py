"""widen master_cv.source_type to fit portfolio-api-json:<host>

Revision ID: 014_widen_master_cv_source_type
Revises: 013_user_irrelevant
Create Date: 2026-05-06 00:00:00.000000

source_type was String(20) which truncates anything beyond 'manual',
'upload', or 'url:short.tld'. The Portfolio CV API import path emits
'portfolio-api-json:alisadikinma.com' (35 chars) and
'portfolio-api-md:alisadikinma.com' (33 chars) — both blow the limit.

Bumping to 64 covers the foreseeable namespace
('<provider-id>-<variant>:<fqdn>') without hitting the 255-char
varchar ceiling that brings index-size concerns. No data migration —
existing rows remain unchanged, only the type ceiling moves.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_widen_master_cv_source_type"
down_revision: Union[str, None] = "013_user_irrelevant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "master_cv",
        "source_type",
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_server_default="manual",
        existing_nullable=True,
    )


def downgrade() -> None:
    # Truncate any existing rows that exceed 20 chars before shrinking,
    # otherwise PostgreSQL refuses the type change. Replace overflow with
    # 'manual' (the safe default) — losing source attribution is better
    # than failing the rollback.
    op.execute(
        "UPDATE master_cv SET source_type = 'manual' "
        "WHERE source_type IS NOT NULL AND char_length(source_type) > 20"
    )
    op.alter_column(
        "master_cv",
        "source_type",
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_server_default="manual",
        existing_nullable=True,
    )
