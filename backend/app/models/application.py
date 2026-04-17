from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("scraped_jobs.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))

    status = Column(String(30), server_default="targeting")

    targeted_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True))
    email_sent_at = Column(DateTime(timezone=True))
    replied_at = Column(DateTime(timezone=True))
    interview_at = Column(DateTime(timezone=True))
    offered_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))

    applied_via = Column(String(50))
    applied_url = Column(String(1000))
    contact_name = Column(String(255))
    contact_email = Column(String(255))
    contact_title = Column(String(255))
    salary_asked = Column(Integer)
    salary_offered = Column(Integer)

    notes = Column(Text)
    tags = Column(ARRAY(Text))

    cv_id = Column(Integer, ForeignKey("generated_cvs.id", ondelete="SET NULL"))
    email_draft_id = Column(Integer, ForeignKey("email_drafts.id", ondelete="SET NULL"))
    cover_letter_id = Column(Integer, ForeignKey("cover_letters.id", ondelete="SET NULL"))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_app_status", "status"),
        Index("idx_app_dates", applied_at.desc()),
    )


class ApplicationActivity(Base):
    __tablename__ = "application_activities"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(String(50), nullable=False)
    description = Column(Text)
    old_value = Column(String(100))
    new_value = Column(String(100))
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
