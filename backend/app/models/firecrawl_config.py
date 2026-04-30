from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class FirecrawlConfig(Base):
    """Singleton row (id=1) holding Firecrawl API credentials.

    Fernet-encrypts `api_key` via `services.encryption` (same key as the
    mailbox password and Apify account tokens). `is_active=False` until
    the user runs the test endpoint successfully.
    """

    __tablename__ = "firecrawl_config"

    id = Column(Integer, primary_key=True)

    api_url = Column(String(500), nullable=False, server_default="https://api.firecrawl.dev")
    api_key_encrypted = Column(Text, nullable=False, server_default="")
    timeout_s = Column(Integer, nullable=False, server_default="60")

    is_active = Column(Boolean, nullable=False, server_default="FALSE")

    last_test_at = Column(DateTime(timezone=True))
    last_test_status = Column(String(20))
    last_test_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_firecrawl_singleton"),
    )
