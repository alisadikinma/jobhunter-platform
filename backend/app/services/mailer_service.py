"""Custom-domain mailbox mailer — IMAP draft append + SMTP send.

Reads credentials from the `mailbox_config` singleton row (id=1) when
present. Falls back to `settings.MAIL_*` env vars when the DB row is
empty / inactive — useful for bootstrap before the UI form is filled in.

Two operations:

- `append_draft(...)` — adds a fully-formed message to the IMAP Drafts
  folder (`\\Draft` flag set). User reviews in their IMAP client
  (Thunderbird / Mail.app / webmail) and sends manually. Used for the
  initial cold-email touch — always human-reviewed.
- `send(...)` — SMTPS-relays a message immediately. Reserved for
  scheduled follow-ups (5d / 10d after `email_sent_at`) where the
  body has already been reviewed at draft time.

If no credentials are available the service raises `MailerDisabled` and
the caller is expected to skip mail-side persistence (drafts still land
in the `email_drafts` table for manual paste).
"""
from __future__ import annotations

import email.utils
import imaplib
import logging
import smtplib
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import settings
from app.models.mailbox import MailboxConfig
from app.services.encryption import decrypt_token

log = logging.getLogger(__name__)


class MailerError(RuntimeError):
    """Generic mailer failure — caller should treat this as soft-fail."""


class MailerDisabled(MailerError):
    """Raised when the mailer config is empty / inactive."""


@dataclass
class MailMessage:
    to_email: str
    subject: str
    body_text: str
    to_name: str | None = None
    body_html: str | None = None
    in_reply_to: str | None = None
    references: list[str] | None = None


@dataclass
class _ResolvedConfig:
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    username: str
    password: str
    from_address: str
    from_name: str
    drafts_folder: str

    @property
    def message_id_domain(self) -> str:
        addr = self.from_address or self.username
        return addr.split("@", 1)[1] if "@" in addr else "localhost"


def _resolve(db: Session | None, *, require_active: bool = True) -> _ResolvedConfig:
    """DB-first, fall back to env. Raises MailerDisabled if neither has creds.

    `require_active=False` lets `test_connection` validate freshly-saved creds
    before the `is_active` flag has been flipped (chicken-and-egg: the flag
    only flips after a successful test).
    """
    if db is not None:
        row = db.get(MailboxConfig, 1)
        if (
            row is not None
            and row.username
            and row.password_encrypted
            and (row.is_active or not require_active)
        ):
            try:
                password = decrypt_token(row.password_encrypted)
            except Exception as e:
                raise MailerError(f"Failed to decrypt mailbox password: {e}") from e
            return _ResolvedConfig(
                smtp_host=row.smtp_host,
                smtp_port=row.smtp_port,
                imap_host=row.imap_host,
                imap_port=row.imap_port,
                username=row.username,
                password=password,
                from_address=row.from_address or row.username,
                from_name=row.from_name or "",
                drafts_folder=row.drafts_folder or "Drafts",
            )

    # Fallback to .env — useful for first-boot before the user opens the form.
    if not (settings.MAIL_USERNAME and settings.MAIL_PASSWORD):
        raise MailerDisabled(
            "No mailbox config — set up via /settings/credentials UI or "
            "MAIL_* env vars"
        )
    return _ResolvedConfig(
        smtp_host=settings.MAIL_SMTP_HOST,
        smtp_port=settings.MAIL_SMTP_PORT,
        imap_host=settings.MAIL_IMAP_HOST,
        imap_port=settings.MAIL_IMAP_PORT,
        username=settings.MAIL_USERNAME,
        password=settings.MAIL_PASSWORD,
        from_address=settings.MAIL_FROM_ADDRESS or settings.MAIL_USERNAME,
        from_name=settings.MAIL_FROM_NAME or "",
        drafts_folder=settings.MAIL_DRAFTS_FOLDER or "Drafts",
    )


def _build_message(msg: MailMessage, cfg: _ResolvedConfig) -> EmailMessage:
    em = EmailMessage()
    em["From"] = email.utils.formataddr((cfg.from_name or "", cfg.from_address))
    em["To"] = email.utils.formataddr((msg.to_name or "", msg.to_email))
    em["Subject"] = msg.subject
    em["Date"] = email.utils.formatdate(localtime=False, usegmt=True)
    em["Message-ID"] = email.utils.make_msgid(domain=cfg.message_id_domain)
    if msg.in_reply_to:
        em["In-Reply-To"] = msg.in_reply_to
    if msg.references:
        em["References"] = " ".join(msg.references)

    em.set_content(msg.body_text)
    if msg.body_html:
        em.add_alternative(msg.body_html, subtype="html")
    return em


def append_draft(msg: MailMessage, *, db: Session | None = None) -> dict[str, str]:
    """Append `msg` to the IMAP Drafts folder. Returns `{folder, uid?, message_id}`."""
    cfg = _resolve(db)
    em = _build_message(msg, cfg)
    raw_bytes = em.as_bytes()
    message_id = em["Message-ID"]
    folder = cfg.drafts_folder

    context = ssl.create_default_context()
    try:
        with imaplib.IMAP4_SSL(host=cfg.imap_host, port=cfg.imap_port, ssl_context=context) as imap:
            imap.login(cfg.username, cfg.password)
            now = datetime.now(UTC)
            internal_date = imaplib.Time2Internaldate(now.timestamp())
            status, response = imap.append(folder, r"(\Draft)", internal_date, raw_bytes)
    except (imaplib.IMAP4.error, OSError) as e:
        log.warning("IMAP draft append failed: %s", e)
        raise MailerError(f"IMAP draft append failed: {e}") from e

    if status != "OK":
        raise MailerError(f"IMAP server rejected APPEND: {status} {response!r}")

    uid = _parse_appenduid(response)
    return {"folder": folder, "uid": uid or "", "message_id": message_id or ""}


def _parse_appenduid(response: list[bytes] | bytes | None) -> str | None:
    if not response:
        return None
    raw = response[0] if isinstance(response, list) else response
    if isinstance(raw, bytes):
        raw = raw.decode("ascii", errors="replace")
    if "APPENDUID" not in raw:
        return None
    try:
        # Format: "[APPENDUID <uidvalidity> <uid>] (Success)" — close bracket
        # may be glued to the digit ("1]") so split + strip per-token.
        chunk = raw.split("APPENDUID", 1)[1]
        tokens = [t.strip(" []") for t in chunk.split()]
        return tokens[1] if len(tokens) >= 2 else None
    except (IndexError, ValueError):
        return None


def send(msg: MailMessage, *, db: Session | None = None) -> dict[str, str]:
    """Submit `msg` via SMTPS. Reserved for scheduled follow-ups."""
    cfg = _resolve(db)
    em = _build_message(msg, cfg)
    message_id = em["Message-ID"]

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(host=cfg.smtp_host, port=cfg.smtp_port, context=context, timeout=30) as smtp:
            smtp.login(cfg.username, cfg.password)
            smtp.send_message(em)
    except (smtplib.SMTPException, OSError) as e:
        log.warning("SMTP send failed: %s", e)
        raise MailerError(f"SMTP send failed: {e}") from e

    return {"message_id": message_id or "", "to": msg.to_email}


def test_connection(db: Session) -> tuple[bool, bool, str]:
    """Run a real IMAP login + SMTP login against current DB config.

    Returns `(imap_ok, smtp_ok, message)`. Used by the test endpoint
    BEFORE marking `is_active=true`.
    """
    cfg = _resolve(db, require_active=False)
    imap_ok = False
    smtp_ok = False
    parts: list[str] = []

    try:
        ctx = ssl.create_default_context()
        with imaplib.IMAP4_SSL(host=cfg.imap_host, port=cfg.imap_port, ssl_context=ctx) as imap:
            imap.login(cfg.username, cfg.password)
            imap.list()
        imap_ok = True
        parts.append("IMAP login OK")
    except Exception as e:
        parts.append(f"IMAP failed: {e}")

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(host=cfg.smtp_host, port=cfg.smtp_port, context=ctx, timeout=15) as smtp:
            smtp.login(cfg.username, cfg.password)
            smtp.noop()
        smtp_ok = True
        parts.append("SMTP login OK")
    except Exception as e:
        parts.append(f"SMTP failed: {e}")

    return imap_ok, smtp_ok, " · ".join(parts)
