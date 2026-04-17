from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from app.database import Base


class ScrapeConfig(Base):
    __tablename__ = "scrape_configs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, server_default="true")
    variant_target = Column(String(50))

    keywords = Column(ARRAY(String), nullable=False)
    excluded_keywords = Column(ARRAY(String))
    locations = Column(ARRAY(String))
    job_types = Column(ARRAY(String))
    remote_only = Column(Boolean, server_default="true")
    min_salary = Column(Integer)

    sources = Column(ARRAY(String), server_default="{remoteok,hn_algolia,hiring_cafe,adzuna,arbeitnow,jobspy}")
    max_results_per_source = Column(Integer, server_default="30")

    cron_expression = Column(String(50), server_default="0 */3 * * *")
    last_run_at = Column(DateTime(timezone=True))
    last_run_results = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
