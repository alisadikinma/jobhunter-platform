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
        Settings(ENV="prod", JWT_SECRET="real-secret-value", ADMIN_PASSWORD="change-me", _env_file=None)


def test_settings_accepts_real_secrets_outside_dev():
    s = Settings(ENV="prod", JWT_SECRET="real-secret-value", ADMIN_PASSWORD="real-password", _env_file=None)
    assert s.ENV == "prod"
    assert s.JWT_SECRET == "real-secret-value"
