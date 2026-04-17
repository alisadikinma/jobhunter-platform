from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.database import Base


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    job_id = Column(Integer, ForeignKey("scraped_jobs.id"))

    subject = Column(String(255))
    body = Column(Text, nullable=False)
    email_type = Column(String(30), server_default="initial")
    recipient_email = Column(String(255))
    recipient_name = Column(String(255))

    strategy = Column(String(50))
    personalization = Column(JSONB)

    status = Column(String(20), server_default="draft")
    sent_at = Column(DateTime(timezone=True))

    model_used = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
