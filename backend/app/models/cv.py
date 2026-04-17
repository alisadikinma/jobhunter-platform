from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.sql import func

from app.database import Base


class MasterCV(Base):
    """
    Master CV stored as JSON Resume format with extensions.

    content JSONB schema:
    {
        "basics": {
            "name": str,
            "label": str,
            "email": str,
            "location": {"city": str, "region": str, "remote": bool},
            "profiles": [{"network": str, "url": str}],
            "summary_variants": {
                "vibe_coding": str,
                "ai_automation": str,
                "ai_video": str
            }
        },
        "work": [{
            "company": str,
            "position": str,
            "highlights": [{
                "text": str,
                "tags": [str],
                "metrics": dict | null,
                "relevance_hint": ["vibe_coding" | "ai_automation" | "ai_video"]
            }]
        }],
        "projects": [...],
        "skills": {...},
        "education": [...]
    }
    """
    __tablename__ = "master_cv"

    id = Column(Integer, primary_key=True)
    version = Column(Integer, server_default="1")
    content = Column(JSONB, nullable=False)
    raw_markdown = Column(Text)
    skills = Column(ARRAY(Text))
    is_active = Column(Boolean, server_default="true")

    # Phase 2 prep columns (used when Portfolio_v2 integration added)
    source_type = Column(String(20), server_default="manual")
    source_hash = Column(String(64))
    synced_at = Column(DateTime(timezone=True))
    source_version = Column(String(50))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class GeneratedCV(Base):
    __tablename__ = "generated_cvs"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    job_id = Column(Integer, ForeignKey("scraped_jobs.id"))
    master_cv_id = Column(Integer, ForeignKey("master_cv.id"))

    tailored_markdown = Column(Text)
    tailored_json = Column(JSONB)
    docx_path = Column(String(500))
    pdf_path = Column(String(500))

    ats_score = Column(Integer)
    keyword_matches = Column(ARRAY(Text))
    missing_keywords = Column(ARRAY(Text))
    suggestions = Column(JSONB)

    variant_used = Column(String(50))
    confidence = Column(Integer)
    model_used = Column(String(50))
    generation_log = Column(JSONB)
    status = Column(String(20), server_default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    job_id = Column(Integer, ForeignKey("scraped_jobs.id"))
    content = Column(Text, nullable=False)
    tone = Column(String(30), server_default="professional")
    model_used = Column(String(50))
    status = Column(String(20), server_default="draft")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
