from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class MailboxConfig(Base):
    """Singleton row (id=1) holding custom-domain mailer credentials.

    Password is Fernet-encrypted via `services.encryption`; `is_active=False`
    until the user runs the test endpoint successfully.
    """

    __tablename__ = "mailbox_config"

    id = Column(Integer, primary_key=True)

    smtp_host = Column(String(255), nullable=False, server_default="")
    smtp_port = Column(Integer, nullable=False, server_default="465")
    imap_host = Column(String(255), nullable=False, server_default="")
    imap_port = Column(Integer, nullable=False, server_default="993")
    username = Column(String(255), nullable=False, server_default="")
    password_encrypted = Column(Text, nullable=False, server_default="")
    from_address = Column(String(255), nullable=False, server_default="")
    from_name = Column(String(255), nullable=False, server_default="")
    drafts_folder = Column(String(100), nullable=False, server_default="Drafts")

    is_active = Column(Boolean, nullable=False, server_default="FALSE")

    last_test_at = Column(DateTime(timezone=True))
    last_test_status = Column(String(20))
    last_test_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_mailbox_singleton"),
    )
