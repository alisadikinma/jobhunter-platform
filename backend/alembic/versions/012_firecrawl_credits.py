"""switch firecrawl_accounts to integer credits (525 free tier default)

Revision ID: 012_firecrawl_credits
Revises: 011_firecrawl_pool
Create Date: 2026-04-30 16:00:00.000000

Firecrawl uses CREDITS (1 credit = 1 page scrape on standard plan), not
USD. Free-tier signup gives 525 credits. The previous Decimal(10,2)
"monthly_credit_usd" defaulting to $0.50 was a misnomer.

Renames:
  monthly_credit_usd -> monthly_credits (Integer, default 525)
  credit_used_usd    -> credits_used    (Integer, default 0)

Existing rows: bump monthly_credits to 525 unless the column already
holds a larger int (preserves any user override).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012_firecrawl_credits"
down_revision: Union[str, None] = "011_firecrawl_pool"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new integer columns alongside the old Decimal ones.
    op.add_column(
        "firecrawl_accounts",
        sa.Column("monthly_credits", sa.Integer(), nullable=False, server_default="525"),
    )
    op.add_column(
        "firecrawl_accounts",
        sa.Column("credits_used", sa.Integer(), nullable=False, server_default="0"),
    )

    # Existing rows had monthly_credit_usd=$0.50 by mistake. Bump everyone
    # to free-tier 525 credits unless someone explicitly overrode it
    # (Decimal value > 1.0 means user typed a higher number).
    op.execute(
        """
        UPDATE firecrawl_accounts
        SET monthly_credits = CASE
            WHEN monthly_credit_usd >= 1 THEN ROUND(monthly_credit_usd)::INTEGER
            ELSE 525
        END,
        credits_used = ROUND(credit_used_usd * 1000)::INTEGER
        """
    )

    op.drop_column("firecrawl_accounts", "credit_used_usd")
    op.drop_column("firecrawl_accounts", "monthly_credit_usd")


def downgrade() -> None:
    op.add_column(
        "firecrawl_accounts",
        sa.Column(
            "monthly_credit_usd",
            sa.Numeric(10, 2),
            server_default="0.50",
            nullable=True,
        ),
    )
    op.add_column(
        "firecrawl_accounts",
        sa.Column(
            "credit_used_usd",
            sa.Numeric(10, 2),
            server_default="0.00",
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE firecrawl_accounts
        SET monthly_credit_usd = monthly_credits::NUMERIC / 1000,
            credit_used_usd = credits_used::NUMERIC / 1000
        """
    )
    op.drop_column("firecrawl_accounts", "credits_used")
    op.drop_column("firecrawl_accounts", "monthly_credits")
