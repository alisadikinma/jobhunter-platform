from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from app.database import Base


class ScrapedJob(Base):
    __tablename__ = "scraped_jobs"

    id = Column(Integer, primary_key=True)
    external_id = Column(String(255))
    source = Column(String(50), nullable=False)
    source_url = Column(String(1000))
    company_id = Column(Integer)
    title = Column(String(500), nullable=False)
    company_name = Column(String(255), nullable=False)
    location = Column(String(255))
    job_type = Column(String(50))
    remote_type = Column(String(50))
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    salary_currency = Column(String(10), server_default="USD")
    description = Column(Text)
    description_source = Column(String(20), server_default="aggregator")
    requirements = Column(Text)
    tech_stack = Column(ARRAY(Text))
    experience_level = Column(String(50))

    relevance_score = Column(Integer)
    score_reasons = Column(JSONB)
    match_keywords = Column(ARRAY(Text))
    suggested_variant = Column(String(50))

    content_hash = Column(String(64), unique=True)

    status = Column(String(20), server_default="new")
    is_favorite = Column(Boolean, server_default="false")
    user_irrelevant = Column(Boolean, nullable=False, server_default="false")

    enriched_at = Column(DateTime(timezone=True))
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())
    posted_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_source", "source"),
        Index("idx_jobs_score", relevance_score.desc()),
        Index("idx_jobs_scraped_at", scraped_at.desc()),
        Index("idx_jobs_user_irrelevant", "user_irrelevant"),
    )
