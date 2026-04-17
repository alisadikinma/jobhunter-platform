from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from app.database import Base


class PortfolioAsset(Base):
    __tablename__ = "portfolio_assets"

    id = Column(Integer, primary_key=True)
    asset_type = Column(String(50))
    title = Column(String(255))
    url = Column(String(1000))
    thumbnail_url = Column(String(1000))
    description = Column(Text)
    tech_stack = Column(ARRAY(Text))
    tags = Column(ARRAY(Text))
    metrics = Column(JSONB)
    relevance_hint = Column(ARRAY(Text))
    display_priority = Column(Integer, server_default="50")
    is_featured = Column(Boolean, server_default="false")

    status = Column(String(20), server_default="draft")
    auto_generated = Column(Boolean, server_default="false")
    source_path = Column(Text)
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(Integer, ForeignKey("users.id"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
