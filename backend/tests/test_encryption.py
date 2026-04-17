import pytest
from cryptography.fernet import Fernet

from app.config import settings
from app.services.encryption import decrypt_token, encrypt_token, mask_token


@pytest.fixture
def _fernet_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "APIFY_FERNET_KEY", key)
    return key


def test_encrypt_decrypt_roundtrip(_fernet_key):
    plain = "apify_api_token_abcdef123"
    encrypted = encrypt_token(plain)
    assert encrypted != plain
    assert decrypt_token(encrypted) == plain


def test_encrypt_produces_different_ciphertext_each_call(_fernet_key):
    # Fernet embeds a timestamp/IV, so two encryptions of the same plaintext differ.
    plain = "same-token"
    assert encrypt_token(plain) != encrypt_token(plain)


def test_encrypt_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr(settings, "APIFY_FERNET_KEY", "")
    with pytest.raises(RuntimeError, match="APIFY_FERNET_KEY"):
        encrypt_token("anything")


def test_mask_token_keeps_last_four():
    assert mask_token("apify_api_abc1234") == "*************1234"


def test_mask_token_when_shorter_than_visible():
    assert mask_token("abc") == "***"
