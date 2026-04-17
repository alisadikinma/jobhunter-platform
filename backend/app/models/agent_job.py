from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class AgentJob(Base):
    __tablename__ = "agent_jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(String(50), nullable=False)
    reference_id = Column(Integer)
    reference_type = Column(String(50))

    status = Column(String(20), server_default="pending")
    progress_pct = Column(Integer, server_default="0")
    current_step = Column(String(100))
    progress_log = Column(JSONB, server_default=text("'[]'::jsonb"))

    model_used = Column(String(50))
    process_pid = Column(Integer)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)

    result = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
