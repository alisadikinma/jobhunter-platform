"""Fernet symmetric encryption for secrets stored in DB (Apify API tokens).

The key comes from APIFY_FERNET_KEY env; config.py validates it at startup.
Generate with:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from cryptography.fernet import Fernet

from app.config import settings


def _cipher() -> Fernet:
    if not settings.APIFY_FERNET_KEY:
        raise RuntimeError(
            "APIFY_FERNET_KEY is not configured — cannot encrypt/decrypt tokens"
        )
    return Fernet(settings.APIFY_FERNET_KEY.encode())


def encrypt_token(plain: str) -> str:
    return _cipher().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted: str) -> str:
    return _cipher().decrypt(encrypted.encode("utf-8")).decode("utf-8")


def mask_token(plain: str, visible: int = 4) -> str:
    """Return '****xxxx' — last `visible` chars kept for UI display."""
    if len(plain) <= visible:
        return "*" * len(plain)
    return "*" * (len(plain) - visible) + plain[-visible:]
