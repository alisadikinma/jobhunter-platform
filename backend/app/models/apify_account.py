from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database import Base


class ApifyAccount(Base):
    __tablename__ = "apify_accounts"

    id = Column(Integer, primary_key=True)
    label = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    api_token = Column(String(500), nullable=False)

    priority = Column(Integer, server_default="100")
    status = Column(String(20), server_default="active")

    monthly_credit_usd = Column(Numeric(10, 2), server_default="5.00")
    credit_used_usd = Column(Numeric(10, 2), server_default="0.00")
    quota_reset_at = Column(DateTime(timezone=True))
    exhausted_at = Column(DateTime(timezone=True))

    last_used_at = Column(DateTime(timezone=True))
    cooldown_until = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, server_default="0")
    last_error = Column(Text)
    last_success_at = Column(DateTime(timezone=True))

    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_apify_status", "status", "priority"),
        Index("idx_apify_cooldown", "cooldown_until"),
    )


class ApifyUsageLog(Base):
    __tablename__ = "apify_usage_log"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("apify_accounts.id"))
    scrape_run_id = Column(Integer)
    actor_id = Column(String(100))

    compute_units = Column(Numeric(10, 4))
    cost_usd = Column(Numeric(10, 4))
    jobs_scraped = Column(Integer)

    status = Column(String(20))
    error_message = Column(Text)
    duration_ms = Column(Integer)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_usage_account", "account_id", created_at.desc()),
    )
