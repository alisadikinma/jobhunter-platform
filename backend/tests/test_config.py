import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_allows_default_secrets_in_dev():
    s = Settings(ENV="dev", JWT_SECRET="change-me", ADMIN_PASSWORD="change-me", _env_file=None)
    assert s.ENV == "dev"


def test_settings_rejects_default_jwt_secret_outside_dev():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(ENV="prod", JWT_SECRET="change-me", ADMIN_PASSWORD="real", _env_file=None)


def test_settings_rejects_default_admin_password_outside_dev():
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD"):
        Settings(ENV="prod", JWT_SECRET="a" * 32, ADMIN_PASSWORD="change-me", _env_file=None)


def test_settings_accepts_real_secrets_outside_dev():
    s = Settings(
        ENV="prod",
        JWT_SECRET="a" * 32,
        ADMIN_PASSWORD="real-password",
        _env_file=None,
    )
    assert s.ENV == "prod"
    assert len(s.JWT_SECRET) == 32


def test_settings_rejects_short_jwt_secret_outside_dev():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(ENV="prod", JWT_SECRET="short", ADMIN_PASSWORD="real", _env_file=None)


def test_settings_rejects_invalid_fernet_key():
    with pytest.raises(ValidationError, match="Fernet key"):
        Settings(ENV="dev", APIFY_FERNET_KEY="not-a-valid-fernet-key", _env_file=None)


def test_settings_accepts_valid_fernet_key():
    from cryptography.fernet import Fernet

    key = Fernet.generate_key().decode()
    s = Settings(ENV="dev", APIFY_FERNET_KEY=key, _env_file=None)
    assert key == s.APIFY_FERNET_KEY


def test_settings_rejects_short_callback_secret_outside_dev():
    with pytest.raises(ValidationError, match="CALLBACK_SECRET"):
        Settings(
            ENV="prod",
            JWT_SECRET="a" * 32,
            ADMIN_PASSWORD="real",
            CALLBACK_SECRET="short",
            _env_file=None,
        )


def test_settings_accepts_long_callback_secret_outside_dev():
    s = Settings(
        ENV="prod",
        JWT_SECRET="a" * 32,
        ADMIN_PASSWORD="real",
        CALLBACK_SECRET="b" * 32,
        _env_file=None,
    )
    assert len(s.CALLBACK_SECRET) == 32
