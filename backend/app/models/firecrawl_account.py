from sqlalchemy import Column, DateTime, Index, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database import Base


class FirecrawlAccount(Base):
    """Free-tier Firecrawl account in a rotating pool.

    Mirrors apify_accounts: when one account hits its credit limit or
    rate-limit, the pool acquires the next available active account.
    Each row holds an api_url (so we can mix self-hosted + SaaS) plus
    a Fernet-encrypted api_token.

    monthly_credit_usd=0 means "unlimited" (self-hosted Firecrawl).
    """

    __tablename__ = "firecrawl_accounts"

    id = Column(Integer, primary_key=True)
    label = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, server_default="")
    api_url = Column(String(500), nullable=False, server_default="https://api.firecrawl.dev")
    api_token = Column(Text, nullable=False, server_default="")  # Fernet-encrypted

    priority = Column(Integer, server_default="100")
    status = Column(String(20), server_default="active")

    monthly_credit_usd = Column(Numeric(10, 2), server_default="0.50")
    credit_used_usd = Column(Numeric(10, 2), server_default="0.00")
    quota_reset_at = Column(DateTime(timezone=True))
    exhausted_at = Column(DateTime(timezone=True))

    last_used_at = Column(DateTime(timezone=True))
    cooldown_until = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, server_default="0")
    last_error = Column(Text)
    last_success_at = Column(DateTime(timezone=True))

    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_firecrawl_status", "status", "priority"),
        Index("idx_firecrawl_cooldown", "cooldown_until"),
    )
